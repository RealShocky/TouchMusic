import numpy as np
import soundfile as sf

from touchmusic.audio import AudioEngine, RATE, Recorder


def test_capture_and_chord_change_land_inside_the_audio_block():
    engine = AudioEngine()
    engine.params.update(quantize='Next beat', bpm=120, dialogue=True, gain=1)
    engine.process(np.zeros(23900, np.float32))
    engine.commands.put(('loop', 0))
    engine.commands.put(('chord', 4))
    engine.process(np.ones(200, np.float32) * .25)
    assert engine.params['chord'] == 4
    assert engine.loops[0].recording
    assert engine.loops[0].size == 100
    engine.process(np.full(3900, .25, np.float32))
    engine.commands.put(('loop', 0))
    engine.process(np.full(20100, .25, np.float32))
    assert len(engine.loops[0].clip) == RATE // 2
    assert np.allclose(engine.loops[0].clip, .25)


def test_bar_quantization_and_click_monitor():
    engine = AudioEngine()
    engine.params.update(quantize='Next bar', bpm=120, metronome=True, dialogue=True)
    assert engine.process(np.zeros(512, np.float32)).any()
    engine.commands.put(('chord', 4))
    engine.process(np.zeros(512, np.float32))
    assert engine.params['chord'] == 0
    assert engine.queued_chord == 4


def test_recording_exports_aligned_vocal_and_leaves_the_original(tmp_path):
    class DelayedConverter:
        def process(self, audio, mix, start_frame):
            self.source_frames = np.arange(start_frame, start_frame + len(audio)) - len(audio)
            return np.full_like(audio, .4 if start_frame else 0.)

    engine = AudioEngine()
    engine.params.update(dialogue=True, gain=1, metronome=True)
    engine.neural = True
    engine.converter = DelayedConverter()
    original = tmp_path / 'show.wav'
    engine.recorder = Recorder(original, align=True)
    for _ in range(2):
        engine.process(np.zeros(512, np.float32))
    exported = engine.stop_recording()
    exported.alignment_thread.join(timeout=5)
    assert exported.aligned_mix.is_file() and original.is_file()
    raw, _ = sf.read(exported.stem_dir / 'wet-vocal.wav')
    aligned, _ = sf.read(exported.stem_dir / 'wet-vocal-aligned.wav')
    assert np.allclose(raw[512:], .4)
    assert np.allclose(aligned[:512], .4)
    assert not np.any(aligned[512:])
