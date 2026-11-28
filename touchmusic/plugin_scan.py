"""Metadata discovery and explicit, isolated effect compatibility probes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import numpy as np
from .plugin_process import PluginProcess
from .plugin_worker import encode_audio, decode_audio


def standard_folders():
    paths = [Path(os.environ.get('COMMONPROGRAMFILES', 'C:/Program Files/Common Files')) / 'VST3',
             Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs/Common/VST3']
    if platform.system() == 'Darwin':
        paths = [Path('/Library/Audio/Plug-Ins/VST3'), Path.home()/'Library/Audio/Plug-Ins/VST3']
    elif platform.system() != 'Windows':
        paths = [Path('/usr/lib/vst3'), Path('/usr/local/lib/vst3'), Path.home()/'.vst3']
    return paths


def discover(folders=None, limit=1000):
    found, visited = {}, 0
    for folder in folders if folders is not None else standard_folders():
        root = Path(folder).expanduser()
        if root.suffix.lower() == '.vst3' and root.exists():
            found[str(root.resolve()).casefold()] = str(root.resolve())
            continue
        for current, directories, files in os.walk(root, followlinks=False):
            visited += 1
            if visited > 10000:
                raise ValueError('Discovery limit reached. Choose narrower folders.')
            retained = []
            for name in directories:
                path = Path(current)/name
                if path.suffix.lower() == '.vst3':
                    found[str(path.resolve()).casefold()] = str(path.resolve())
                elif not path.is_symlink():
                    retained.append(name)
            directories[:] = retained
            for name in files:
                if name.lower().endswith('.vst3'):
                    path = str((Path(current)/name).resolve())
                    found[path.casefold()] = path
            if len(found) >= limit:
                return sorted(found.values())[:limit]
    return sorted(found.values())


def binary_path(path):
    path = Path(path).resolve()
    binary = path/'Contents'/'x86_64-win'/path.name
    return binary if binary.is_file() else path


def fingerprint(path):
    binary = binary_path(path)
    if not binary.is_file():
        raise ValueError('No supported Windows x64 binary found in this bundle.')
    digest = hashlib.sha256()
    with binary.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def scan_plugin(path, version='Unknown', factory=PluginProcess, blocks=100):
    """A bounded smoke test, not certification or measured hardware round-trip latency."""
    record = {'path': str(Path(path).resolve()), 'version': version, 'status': 'Failed',
              'tested_at': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'rate': 48000, 'block_frames': 512, 'blocks': blocks,
              'hardware_tested': False, 'editor_tested': False, 'daw_tested': False}
    client = None
    try:
        record['binary_sha256'] = fingerprint(path)
        client = factory()
        values = client.request('configure', settings={'effects': [{'path': str(path)}]})
        parameters = values['effects'][0]['parameters']
        record['parameters'] = len(parameters)
        timings, response = [], []
        for index in range(blocks):
            audio = np.zeros(512, np.float32)
            if index == 0:
                audio[0] = .1
            started = time.perf_counter()
            result = client.request('process', audio=encode_audio(audio), rate=48000)
            timings.append((time.perf_counter()-started)*1000)
            if result.get('error'):
                raise RuntimeError(result['error'])
            wet = decode_audio(result)
            if wet.shape != (2, 512):
                raise ValueError('Plugin did not produce a full stereo block.')
            response.append(wet)
        impulse = np.concatenate(response, axis=1)
        active = np.flatnonzero(np.max(np.abs(impulse), axis=0) > 1e-6)
        record['impulse_onset_samples'] = int(active[0]) if len(active) else None
        record['impulse_note'] = 'Onset at default settings; not declared latency or hardware round trip.'
        record['rpc_ms_p50'] = float(np.percentile(timings, 50))
        record['rpc_ms_p95'] = float(np.percentile(timings, 95))
        record['automation'] = 'No exposed parameters'
        if parameters:
            name = next(iter(parameters))
            original = parameters[name]
            changed = .25 if original > .5 else .75
            client.request('process', audio=encode_audio(np.zeros(512, np.float32)), rate=48000,
                           parameters=[{name: changed}])
            actual = client.request('inspect')['effects'][0]['parameters'][name]
            if abs(actual-changed) > .001:
                raise ValueError('Normalized parameter readback failed.')
            record['automation'] = 'Passed normalized readback: '+name
        record['status'] = 'Passed smoke test'
    except Exception as exc:
        record['error'] = str(exc)
        record['quarantined'] = True
    finally:
        if client:
            client.close()
    return record


def save_scan(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)
