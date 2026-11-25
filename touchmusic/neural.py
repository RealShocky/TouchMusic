"""Pitch-preserving reference conversion using the upstream Seed-VC model.

Inference runs on one worker thread. Audio queues are bounded and tagged by
generation, so a voice switch cannot play output from the previous voice.
"""
import importlib.util
from collections import OrderedDict
import os
import queue
import sys
import threading
import time
from types import SimpleNamespace
import numpy as np
from .library import ROOT, DATA, read_audio


class SeedSingingBackend:
    def __init__(self, progress=print):
        progress('Initializing PyTorch')
        import torch
        from huggingface_hub import hf_hub_download
        vendor = ROOT / 'vendor' / 'seed-vc'
        if not (vendor / 'inference.py').exists():
            raise RuntimeError('Seed-VC source is missing. Run Setup.cmd.')
        sys.path.insert(0, str(vendor))
        spec = importlib.util.spec_from_file_location('touchmusic_seed', vendor / 'inference.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cache = DATA / 'models'
        cache.mkdir(parents=True, exist_ok=True)
        os.environ['HF_HUB_CACHE'] = str(cache)

        def download(repo_id, model_filename='pytorch_model.bin', config_filename=None):
            progress(f'Checking or downloading {repo_id} model files')
            model = hf_hub_download(repo_id, model_filename, cache_dir=str(cache))
            if config_filename:
                return model, hf_hub_download(repo_id, config_filename, cache_dir=str(cache))
            return model

        module.load_custom_model_from_hf = download
        self.torch = torch
        self.device = module.device
        progress(f'Loading singing model on {self.device}')
        torch.set_num_threads(4)
        args = SimpleNamespace(f0_condition=True, checkpoint=None, config=None, fp16=torch.cuda.is_available())
        self.model, self.semantic, self.f0, self.vocoder, self.speaker, self.mel, options = module.load_models(args)
        self.rate = options['sampling_rate']
        self.reference_path = None
        self.reference = None
        self.reference_cache = OrderedDict()

    def set_reference(self, path):
        path = str(path)
        if path in self.reference_cache:
            self.reference = self.reference_cache[path]
            self.reference_path = path
            self.reference_cache.move_to_end(path)
            return
        import torchaudio
        torch = self.torch
        with torch.inference_mode():
            wav = read_audio(path, self.rate)[:self.rate * 8]
            waveform = torch.from_numpy(wav).to(self.device)[None]
            low = torchaudio.functional.resample(waveform, self.rate, 16000)
            semantic = self.semantic(low)
            mel = self.mel(waveform)
            f0 = torch.from_numpy(self.f0(low[0], thred=.03)).to(self.device)[None]
            length = torch.LongTensor([mel.size(2)]).to(self.device)
            condition = self.model.length_regulator(semantic, ylens=length, n_quantizers=3, f0=f0)[0]
            features = torchaudio.compliance.kaldi.fbank(low, num_mel_bins=80, dither=0, sample_frequency=16000)
            features -= features.mean(dim=0, keepdim=True)
            style = self.speaker(features[None])
            self.reference = condition, mel, style
            self.reference_path = path
            self.reference_cache[path] = self.reference
            if len(self.reference_cache) > 8:
                self.reference_cache.popitem(last=False)

    def convert(self, audio, rate=48000, steps=4):
        import torchaudio
        torch = self.torch
        if self.reference is None:
            raise RuntimeError('Select a reference voice first.')
        with torch.inference_mode():
            source = torch.from_numpy(np.asarray(audio, np.float32)).to(self.device)[None]
            source = torchaudio.functional.resample(source, rate, self.rate)
            low = torchaudio.functional.resample(source, self.rate, 16000)
            semantic = self.semantic(low)
            mel = self.mel(source)
            # Preserve the singer's F0 directly, including unvoiced frames.
            f0 = torch.from_numpy(self.f0(low[0], thred=.03)).to(self.device)[None]
            length = torch.LongTensor([mel.size(2)]).to(self.device)
            condition = self.model.length_regulator(semantic, ylens=length, n_quantizers=3, f0=f0)[0]
            prompt, reference_mel, style = self.reference
            combined = torch.cat([prompt, condition], dim=1)
            lengths = torch.LongTensor([combined.size(1)]).to(self.device)
            with torch.autocast(device_type=self.device.type, enabled=self.device.type == 'cuda', dtype=torch.float16):
                converted = self.model.cfm.inference(combined, lengths, reference_mel, style, None,
                                                     steps, inference_cfg_rate=.7)
            converted = converted[:, :, reference_mel.size(-1):]
            waveform = self.vocoder(converted.float()).reshape(-1)
            waveform = torchaudio.functional.resample(waveform, self.rate, rate)
            result = waveform.float().cpu().numpy()
        # Match the audio clock despite mel-frame rounding.
        return np.interp(np.linspace(0, len(result) - 1, len(audio)), np.arange(len(result)), result).astype(np.float32)


class StreamingConverter:
    LIVE_HOP = 38400
    STUDIO_HOP = 57600

    def __init__(self, factory=None):
        self.factory = factory or (lambda: SeedSingingBackend(progress=self.report_progress))
        self.lock = threading.RLock()
        self.requests = queue.Queue(maxsize=2)
        self.results = queue.Queue(maxsize=4)
        self.reference = None
        self.generation = 0
        self.ready = False
        self.status = 'Loading singing model'
        self.error = ''
        self.inference_ms = 0.
        self.dropped = 0
        self.underruns = 0
        self.closed = False
        self.hop = self.LIVE_HOP
        self.quality = 'Live'
        self.overlap = 960
        self.pending = np.zeros(0, np.float32)
        self.history = np.zeros(self.hop, np.float32)
        self.output = np.empty((0, 2), np.float32)
        self.output_frames = np.empty(0, np.int64)
        self.source_frames = np.empty(0, np.int64)
        self.next_input_frame = 0
        self.pending_start_frame = 0
        self.input_end_frame = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def report_progress(self, status):
        self.status = status
        print(status, flush=True)

    def reset(self):
        with self.lock:
            self.generation += 1
            self.pending = np.zeros(0, np.float32)
            self.history = np.zeros(self.hop, np.float32)
            self.output = np.empty((0, 2), np.float32)
            self.output_frames = np.empty(0, np.int64)
            self.input_end_frame = None

    def set_quality(self, quality):
        with self.lock:
            if quality != self.quality:
                self.quality = quality
                self.hop = self.STUDIO_HOP if quality == 'Studio' else self.LIVE_HOP
                self.reset()

    def select(self, path):
        with self.lock:
            if self.reference == str(path):
                return
            self.reference = str(path)
            self.ready = False
            self.reset()

    def _run(self):
        try:
            backend = self.factory()
            self.status = 'Select a reference voice'
            previous = None
            previous_end_frame = None
            tail = np.zeros(self.overlap, np.float32)
            while not self.closed:
                reference = self.reference
                if reference:
                    if backend.reference_path != reference:
                        self.status = 'Preparing reference voice'
                        backend.set_reference(reference)
                    with self.lock:
                        if self.reference == reference and not self.ready:
                            self.status = 'Singing model ready'
                            self.ready = True
                try:
                    generation, reference, window, quality, hop, source_start = self.requests.get(timeout=.1)
                except queue.Empty:
                    continue
                if generation != self.generation or not reference:
                    continue
                if backend.reference_path != reference:
                    backend.set_reference(reference)
                started = time.perf_counter()
                if np.max(np.abs(window[-hop-self.overlap:])) < .0003:
                    converted = np.zeros(hop + self.overlap, np.float32)
                else:
                    converted = (backend.convert(window, steps=8) if quality == 'Studio' else
                                 backend.convert(window))[-hop-self.overlap:]
                self.inference_ms = (time.perf_counter() - started) * 1000
                if generation != self.generation:
                    continue
                if previous != generation or previous_end_frame != source_start:
                    tail.fill(0)
                fade = np.linspace(0, 1, self.overlap, dtype=np.float32)
                converted[:self.overlap] = tail * (1 - fade) + converted[:self.overlap] * fade
                tail = converted[-self.overlap:].copy()
                previous = generation
                previous_end_frame = source_start + hop
                dry = window[-hop-self.overlap:-self.overlap]
                result = np.column_stack((dry, converted[:hop]))
                try:
                    self.results.put_nowait((generation, result, source_start))
                except queue.Full:
                    self.dropped += 1
                self.status = 'Singing model ready' if self.inference_ms < hop / 48 else 'Conversion slower than live audio'
        except Exception as exc:
            import traceback
            self.error = str(exc)
            self.status = 'Singing engine error: ' + str(exc)
            self.ready = False
            traceback.print_exc()

    def process(self, audio, mix=1., start_frame=None):
        """Return playback audio and expose its capture provenance in source_frames.

        start_frame is the absolute input-stream sample index. Omit it to use
        an internal clock. Each source_frames value identifies the input sample
        represented by the corresponding returned sample; -1 marks unavailable
        audio. This describes conversion transport timing, not downstream DSP.
        """
        start_frame = self.next_input_frame if start_frame is None else int(start_frame)
        self.next_input_frame = start_frame + len(audio)
        self.source_frames = np.full(len(audio), -1, np.int64)
        if not self.lock.acquire(blocking=False):
            return np.zeros_like(audio)
        try:
            return self._process_locked(audio, mix, start_frame)
        finally:
            self.lock.release()

    def _process_locked(self, audio, mix, start_frame):
        if not self.ready:
            return np.zeros_like(audio)
        if self.input_end_frame is not None and self.input_end_frame != start_frame:
            self.pending = np.zeros(0, np.float32)
            self.history = np.zeros(self.hop, np.float32)
        self.input_end_frame = start_frame + len(audio)
        if not len(self.pending):
            self.pending_start_frame = start_frame
        self.pending = np.concatenate([self.pending, audio])
        while len(self.pending) >= self.hop:
            current, self.pending = self.pending[:self.hop], self.pending[self.hop:]
            window = np.concatenate([self.history, current])
            self.history = current.copy()
            source_start = self.pending_start_frame - self.overlap
            self.pending_start_frame += self.hop
            try:
                self.requests.put_nowait((self.generation, self.reference, window, self.quality, self.hop, source_start))
            except queue.Full:
                self.dropped += 1
        while not self.results.empty():
            generation, result, source_start = self.results.get_nowait()
            if generation == self.generation:
                self.output = np.concatenate([self.output, result])[-self.hop * 3:]
                frames = np.arange(source_start, source_start + len(result), dtype=np.int64)
                self.output_frames = np.concatenate([self.output_frames, frames])[-self.hop * 3:]
        output = np.zeros_like(audio)
        count = min(len(output), len(self.output))
        dry, wet = self.output[:count].T
        output[:count] = dry * (1. - mix) + wet * mix
        self.source_frames[:count] = np.maximum(self.output_frames[:count], -1)
        self.output = self.output[count:]
        self.output_frames = self.output_frames[count:]
        if count < len(output):
            self.underruns += 1
        return output

    def close(self):
        self.closed = True
