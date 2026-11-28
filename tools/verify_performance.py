"""Accelerated DSP endurance and owned-worker lifecycle checks, without audio devices."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touchmusic.audio import AudioEngine, BLOCK, RATE
from touchmusic.isolated_rack import IsolatedPluginRack
from touchmusic.plugin_state import StateStore
from benchmark_audio import memory_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=3600, help='Simulated audio duration, not wall-clock soak time')
    parser.add_argument('--plugin', help='Optional installed effect for paced worker restart/state checks')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 7200:
        parser.error('Use 1..7200 simulated seconds.')
    report = {'simulated_audio_seconds': args.seconds, 'hardware_audio_tested': False,
              'gpu_inference_tested': False, 'physical_audio_dropouts': None,
              'note': 'Accelerated software endurance, not a real-time hardware performance.'}
    if args.plugin:
        processes = []
        with tempfile.TemporaryDirectory() as folder:
            rack = IsolatedPluginRack(state_store=StateStore(Path(folder)))
            try:
                rack.add(str(Path(args.plugin).resolve()))
                for cycle in range(10):
                    if cycle:
                        rack.restart()
                    processes.append(rack.client.process)
                    for _ in range(16):
                        assert np.isfinite(rack.process(np.ones(512, np.float32)*.03, RATE)).all()
                        time.sleep(.011)
                    assert not rack.error, f'Cycle {cycle}: {rack.error}'
                    rack.capture_states()
                    assert not rack.error
            finally:
                rack.close()
        assert all(process.poll() is not None for process in processes)
        report['plugin_restart_state_cycles'] = len(processes)
        report['owned_workers_remaining'] = 0
    engine = AudioEngine()
    source = (.1*np.sin(np.arange(BLOCK)*2*np.pi*220/RATE)).astype(np.float32)
    blocks = (args.seconds*RATE+BLOCK-1)//BLOCK
    started, cpu = time.perf_counter(), time.process_time()
    maximum = 0.
    misses = 0
    for index in range(blocks):
        before = time.perf_counter()
        output = engine.process(source)
        cost = (time.perf_counter()-before)*1000
        maximum = max(maximum, cost)
        misses += cost > BLOCK/RATE*1000
        if output.shape != (BLOCK,) or not np.isfinite(output).all() or np.max(np.abs(output)) > 1:
            raise ValueError('Invalid DSP output during endurance run.')
        if index and index % 30000 == 0:
            print(f'{index}/{blocks} software blocks verified', flush=True)
    report.update(blocks=blocks, frames=engine.clock.frame, wall_seconds=time.perf_counter()-started,
                  process_cpu_seconds=time.process_time()-cpu, max_block_ms=maximum,
                  synthetic_deadline_misses=misses, peak_process_memory_bytes=memory_bytes(),
                  output='Finite and bounded for every block')
    Path(args.output).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
