"""Reproducible synthetic release comparison. This never opens audio hardware."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import numpy as np


def memory_bytes():
    if os.name != 'nt':
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024))
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD),
                   *[(name, ctypes.c_size_t) for name in ('peak', 'working', 'peak_pool', 'pool',
                     'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]]
    values = Counters()
    values.cb = ctypes.sizeof(values)
    ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    query.restype = wintypes.BOOL
    if not query(handle, ctypes.byref(values), values.cb):
        return None
    return values.peak


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--label', required=True)
    parser.add_argument('--blocks', type=int, default=2000)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not 100 <= args.blocks <= 100000:
        parser.error('Use 100..100000 blocks.')
    sys.path.insert(0, str(Path(args.source).resolve()))
    from touchmusic.audio import AudioEngine, RATE, BLOCK
    engine = AudioEngine()
    source = (.15*np.sin(np.arange(BLOCK)*2*np.pi*220/RATE)).astype(np.float32)
    for _ in range(64):
        engine.process(source)
    times = []
    started, cpu = time.perf_counter(), time.process_time()
    for _ in range(args.blocks):
        before = time.perf_counter()
        output = engine.process(source)
        if not np.isfinite(output).all():
            raise ValueError('Non-finite benchmark output.')
        times.append((time.perf_counter()-before)*1000)
    wall, used = time.perf_counter()-started, time.process_time()-cpu
    report = {'label': args.label, 'platform': platform.platform(), 'python': platform.python_version(),
              'numpy': np.__version__, 'scenario': 'Synthetic mono vocal input, default FX, no AI or external plugins',
              'rate': RATE, 'block_frames': BLOCK, 'blocks': args.blocks,
              'wall_seconds': wall, 'process_cpu_seconds': used, 'cpu_percent_of_one_core': 100*used/wall,
              'peak_process_memory_bytes': memory_bytes(),
              'block_ms_p50': float(np.percentile(times, 50)),
              'block_ms_p95': float(np.percentile(times, 95)), 'block_ms_max': max(times),
              'synthetic_deadline_misses': sum(t > 1000*BLOCK/RATE for t in times),
              'hardware_audio_dropouts': None, 'hardware_roundtrip_ms': None,
              'gpu_inference_ms': None, 'gpu_peak_allocated_bytes': None,
              'gpu_note': 'AI disabled. Optional nvidia-smi telemetry is system-wide, not process attribution.'}
    try:
        telemetry = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,utilization.gpu',
                                   '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        report['gpu_system_snapshot'] = telemetry.stdout.strip() if telemetry.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        report['gpu_system_snapshot'] = None
    Path(args.output).write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
