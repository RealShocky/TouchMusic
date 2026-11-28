import numpy as np
import soundfile as sf
from touchmusic.audio import AudioEngine, Recorder, RATE


def test_effects_are_finite_bounded_and_mute_is_silent():
    engine = AudioEngine()
    engine.params.update(pitch=5, reverb=.5, delay=.4, harmony=.8, robot=.5,
                         chorus=.4, drive=.25, radio=.3, octave=.5, tremolo=.6)
    source = np.sin(np.arange(512) * .08).astype(np.float32) * 2
    blocks = [engine.process(source) for _ in range(20)]
    assert all(b.shape == (512,) and np.isfinite(b).all() and np.max(np.abs(b)) <= 1 for b in blocks)
    assert any(np.any(b) for b in blocks)
    engine.muted = True
    assert not engine.process(source).any()


def test_recording_flushes_all_samples(tmp_path):
    path = tmp_path / 'capture.wav'
    recorder = Recorder(path)
    for _ in range(10):
        recorder.write(np.ones(512, np.float32) * .2)
    recorder.close()
    audio, rate = sf.read(path)
    assert len(audio) == 5120 and rate == RATE
    assert np.allclose(audio, .2, atol=1e-6)
    assert not recorder.error
