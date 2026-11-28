"""Private-fixture GPU comparison and optional real-model native return probe.

Reports contain metrics only. Reference audio, names and model weights stay local.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import numpy as np

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touchmusic.library import VoiceLibrary, read_audio
from benchmark_audio import memory_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', default='touchmusic/neural.py')
    parser.add_argument('--label', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--audio-bridge', help='Optional compiled Audio Bridge binary/bundle for paced real-model return')
    args = parser.parse_args()
    library = VoiceLibrary()
    if len(library.voices) < 2:
        raise RuntimeError('Two local references are required for this private-fixture check.')
    path = Path(args.backend).resolve()
    spec = importlib.util.spec_from_file_location('touchmusic._bench_backend', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = time.perf_counter()
    backend = module.SeedSingingBackend()
    load_seconds = time.perf_counter()-before
    torch = backend.torch
    cuda = str(backend.device).startswith('cuda')
    backend.set_reference(library.path(library.voices[0]))
    source = read_audio(library.path(library.voices[-1]))[:96000]
    if len(source) < 48000:
        raise RuntimeError('Source fixture is too short.')
    if cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    timings = []
    cpu = time.process_time()
    for _ in range(2):
        before = time.perf_counter()
        output = backend.convert(source)
        if cuda:
            torch.cuda.synchronize()
        timings.append(time.perf_counter()-before)
        if len(output) != len(source) or not np.isfinite(output).all() or np.max(np.abs(output)) < .001:
            raise ValueError('Real conversion returned invalid or silent output.')
    report = {'label': args.label, 'backend_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'device': str(backend.device), 'gpu': torch.cuda.get_device_name() if cuda else None,
              'torch': torch.__version__, 'model_load_seconds': load_seconds, 'source_seconds': len(source)/48000,
              'conversion_seconds': timings, 'conversion_cpu_seconds': time.process_time()-cpu,
              'peak_process_memory_bytes': memory_bytes(), 'real_model_tested': True,
              'gpu_peak_allocated_bytes': torch.cuda.max_memory_allocated() if cuda else None,
              'gpu_peak_reserved_bytes': torch.cuda.max_memory_reserved() if cuda else None,
              'physical_audio_devices_tested': False, 'listening_quality_tested': False,
              'fixture_note': 'The same two local references are used for both runs; no audio or reference identity is exported.'}
    if args.audio_bridge:
        from pedalboard import load_plugin
        from touchmusic.audio import AudioEngine
        from touchmusic.audio_bridge import AudioBridge
        from touchmusic.neural import StreamingConverter
        engine = AudioEngine()
        converter = StreamingConverter(lambda: backend)
        captured = {}
        original_process = engine.process
        def capture(audio, stereo=False):
            frame = engine.clock.frame
            result = original_process(audio, stereo=stereo)
            captured[frame] = (result.copy(), int(np.count_nonzero(converter.source_frames >= 0)))
            return result
        engine.process = capture
        plugin = None
        server = AudioBridge(engine)
        try:
            converter.select(library.path(library.voices[0]))
            deadline = time.monotonic()+20
            while not converter.ready and not converter.error and time.monotonic() < deadline:
                time.sleep(.02)
            if not converter.ready:
                raise RuntimeError(converter.error or 'Converter readiness timeout.')
            engine.converter, engine.neural = converter, True
            engine.params.update(dialogue=True, aimix=1.)
            server.start()
            binary = Path(args.audio_bridge)
            inner = binary/'Contents/x86_64-win'/binary.name
            plugin = load_plugin(str(inner if inner.is_file() else binary))
            waveform = np.resize(source, 48000*8)
            outputs = []
            for offset in range(0, len(waveform)-511, 512):
                block = waveform[offset:offset+512]
                outputs.append(plugin.process(np.stack((block, block)), 48000, reset=False))
                time.sleep(512/48000)
            audio = np.concatenate(outputs, axis=1)
            if not np.isfinite(audio).all() or np.max(np.abs(audio)) < .001 or converter.error or server.error:
                raise ValueError(converter.error or server.error or 'Invalid native real-model return.')
            matches = 0
            for index in range(8, len(outputs)):
                frame = (index-8)*512
                if frame in captured and captured[frame][1] > 0:
                    if np.allclose(outputs[index].T, captured[frame][0], atol=1e-6):
                        matches += 1
            if matches < 10 or converter.inference_ms <= 0:
                raise ValueError('Insufficient matched converted blocks in the native return.')
            report['real_model_native_return'] = {'packets': server.packets, 'input_packet_gaps': server.gaps,
                'converter_dropped_chunks': converter.dropped, 'converter_underruns': converter.underruns,
                'last_inference_ms': converter.inference_ms, 'finite_nonzero_stereo': True,
                'matched_real_converted_blocks': matches,
                'daw_tested': False, 'note': 'Actual native hosting with GPU conversion; no physical microphone or DAW.'}
        finally:
            plugin = None
            gc.collect()
            server.close()
            converter.close()
            converter.thread.join(timeout=10)
            engine.rack.close()
            engine.instrument.close()
    Path(args.output).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
