"""Private, bounded JSON RPC worker. Native DLLs never enter the desktop process."""
import base64
import json
import os
import sys
import time
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
    while True:
        line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
        if not line:
            return
        if len(line) > MAX_MESSAGE or not line.endswith(b'\n'):
            return
        try:
            request = json.loads(line)
            action = request['action']
            if action == 'configure':
                rack.restore(request['settings'])
                result = rack.settings()
            elif action == 'process':
                for index, values in enumerate(request.get('parameters', [])):
                    for name, value in values.items():
                        rack.set_parameter(index, name, value)
                for slot, bypass in zip(rack.slots, request.get('bypass', [])):
                    slot['bypass'] = bool(bypass)
                started = time.perf_counter()
                audio = rack.process(decode_audio(request['audio']), request['rate'])
                result = {**encode_audio(audio), 'error': rack.error,
                          'compute_ms': (time.perf_counter() - started) * 1000}
            elif action == 'editor':
                plugin = rack.slots[request['index']]['plugin']
                plugin.show_editor()
                for name, parameter in plugin.parameters.items():
                    rack.slots[request['index']]['parameters'][name] = float(parameter.raw_value)
                result = rack.settings()
            elif action == 'ping':
                result = {'pid': os.getpid()}
            elif action == 'reset':
                for slot in rack.slots:
                    slot['plugin'].reset()
                result = True
            elif action == 'inspect':
                for slot in rack.slots:
                    for name, parameter in slot['plugin'].parameters.items():
                        slot['parameters'][name] = float(parameter.raw_value)
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
