"""Private, bounded JSON RPC worker. Native DLLs never enter the desktop process."""
import base64
import json
import os
import sys
import time
import hashlib
import threading
import queue
import numpy as np

MAX_MESSAGE = 2 * 1024 * 1024


def encode_audio(audio):
    audio = np.ascontiguousarray(audio, dtype='<f4')
    return {'shape': list(audio.shape), 'pcm': base64.b64encode(audio.tobytes()).decode('ascii')}


def decode_audio(value):
    shape = value['shape']
    if (not isinstance(shape, list) or len(shape) not in (1, 2)
            or any(type(n) is not int or n < 1 for n in shape)
            or shape[-1] > 8192 or (len(shape) == 2 and shape[0] not in (1, 2))):
        raise ValueError('Invalid audio dimensions.')
    raw = base64.b64decode(value['pcm'], validate=True)
    if len(raw) != int(np.prod(shape)) * 4:
        raise ValueError('Invalid audio payload.')
    audio = np.frombuffer(raw, dtype='<f4').reshape(shape).copy()
    if not np.isfinite(audio).all():
        raise ValueError('Non-finite audio.')
    return audio


def serve():
    # Keep the RPC pipe separate from C/C++ stdout logging before importing plugins.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), 'w', encoding='utf-8', buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    from .plugin_rack import PluginRack
    rack = PluginRack(preserve_stereo=True)
    captured = {}
    upload = None
    requests = queue.Queue(maxsize=8)
    editor_close = threading.Event()
    def refresh_parameters():
        # Presets may change the native parameter list. Replace the snapshot so
        # removed names cannot linger and be sent to a different program later.
        for slot in rack.slots:
            slot['parameters'] = {name: float(parameter.raw_value)
                                  for name, parameter in slot['plugin'].parameters.items()}
    def read_requests():
        while True:
            line = sys.stdin.buffer.readline(MAX_MESSAGE+1)
            if not line:
                # A lost parent must not leave a native editor or hung DLL orphan.
                os._exit(0)
            if len(line) > MAX_MESSAGE or not line.endswith(b'\n'):
                os._exit(2)
            try:
                item = json.loads(line)
                if item.get('action') == 'close_editor':
                    editor_close.set()
                    continue
                if item.get('action') == 'editor':
                    editor_close.clear()
                requests.put(item)
            except Exception as exc:
                requests.put(exc)
    threading.Thread(target=read_requests, daemon=True).start()
    while True:
        try:
            request = requests.get()
            if isinstance(request, Exception):
                raise request
            action = request['action']
            if action in ('editor', 'state_info', 'state_begin'):
                index = request.get('index')
                if type(index) is not int or not 0 <= index < len(rack.slots):
                    raise ValueError('Invalid native slot index.')
            if action == 'configure':
                if request.get('instrument'):
                    from .instrument_backend import InstrumentBackend
                    rack = InstrumentBackend()
                rack.restore(request['settings'])
                if hasattr(rack, 'prepare_state'):
                    rack.prepare_state()
                refresh_parameters()
                result = rack.settings()
            elif action == 'process':
                for index, values in enumerate(request.get('parameters', [])):
                    for name, value in values.items():
                        rack.set_parameter(index, name, value)
                for slot, bypass in zip(rack.slots, request.get('bypass', [])):
                    slot['bypass'] = bool(bypass)
                started = time.perf_counter()
                source = decode_audio(request['audio'])
                audio = (rack.process(source.shape[-1], request['rate'], request.get('midi', []))
                         if request.get('midi') is not None else rack.process(source, request['rate']))
                result = {**encode_audio(audio), 'error': rack.error,
                          'compute_ms': (time.perf_counter() - started) * 1000}
            elif action == 'editor':
                plugin = rack.slots[request['index']]['plugin']
                plugin.show_editor(close_event=editor_close)
                if hasattr(rack, 'prepare_state'):
                    rack.prepare_state()
                refresh_parameters()
                result = rack.settings()
            elif action == 'ping':
                result = {'pid': os.getpid()}
            elif action == 'set_values':
                for index, values in enumerate(request['parameters']):
                    for name, value in values.items():
                        if rack.slots[index]['parameters'].get(name) != value:
                            rack.set_parameter(index, name, value)
                result = True
            elif action == 'state_info':
                from .plugin_state import MAX_STATE
                index = request['index']
                raw = bytes(rack.slots[index]['plugin'].raw_state)
                if len(raw) > MAX_STATE:
                    raise ValueError('Native state exceeds 8 MiB.')
                captured.clear()
                captured[index] = raw
                result = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            elif action == 'state_read':
                from .plugin_state import CHUNK
                raw = captured[request['index']]
                offset = request['offset']
                if type(offset) is not int or not 0 <= offset <= len(raw):
                    raise ValueError('Invalid state offset.')
                result = base64.b64encode(raw[offset:offset+CHUNK]).decode('ascii')
                if offset+CHUNK >= len(raw):
                    captured.clear()
            elif action == 'state_begin':
                from .plugin_state import MAX_STATE, valid_id
                size = request['size']
                if type(size) is not int or not 0 <= size <= MAX_STATE or not valid_id(request['sha256']):
                    raise ValueError('Invalid native state upload.')
                upload = {'index': request['index'], 'size': size, 'sha256': request['sha256'], 'raw': bytearray()}
                result = True
            elif action == 'state_write':
                from .plugin_state import CHUNK
                raw = base64.b64decode(request['data'], validate=True)
                if (upload is None or len(raw) > CHUNK or request['offset'] != len(upload['raw'])
                        or len(upload['raw'])+len(raw) > upload['size']):
                    raise ValueError('Invalid native state chunk.')
                upload['raw'].extend(raw)
                result = True
            elif action == 'state_commit':
                if (upload is None or len(upload['raw']) != upload['size']
                        or hashlib.sha256(upload['raw']).hexdigest() != upload['sha256']):
                    raise ValueError('Native state upload checksum mismatch.')
                # Bypass Pedalboard's Python parameter-name inference. For large
                # synths it scans thousands of unrelated parameters before ever
                # reaching the native raw_state descriptor and hits the watchdog.
                object.__setattr__(rack.slots[upload['index']]['plugin'],
                                   'raw_state', bytes(upload['raw']))
                if hasattr(rack, 'prepare_state'):
                    # Synths may defer patch application to their next blocks.
                    # Effect state restoration must retain its negotiated buses.
                    rack.slots[upload['index']]['plugin'].reset()
                    rack.prepare_state()
                refresh_parameters()
                upload = None
                result = True
            elif action == 'reset':
                for slot in rack.slots:
                    slot['plugin'].reset()
                if hasattr(rack, 'prepare_state'):
                    rack.prepare_state()
                result = True
            elif action == 'inspect':
                refresh_parameters()
                result = rack.settings()
            elif action == 'quit':
                return
            else:
                raise ValueError('Unknown worker action.')
            response = {'ok': True, 'result': result}
        except Exception as exc:
            response = {'ok': False, 'error': str(exc)[:4000]}
        encoded = json.dumps(response, allow_nan=False, separators=(',', ':'))
        if len(encoded.encode('utf-8')) >= MAX_MESSAGE:
            encoded = json.dumps({'ok': False, 'error': 'Worker response exceeds limit.'})
        protocol.write(encoded + '\n')
        protocol.flush()


if __name__ == '__main__':
    serve()
