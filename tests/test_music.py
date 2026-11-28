import numpy as np

from touchmusic.audio import AudioEngine, BLOCK, LoopTrack, RATE, Recorder
from touchmusic.music import PitchDetector, chord_notes, nearest_note
from touchmusic.project import load_project, save_project


def test_pitch_and_chord_notes():
    detector = PitchDetector(RATE)
    audio = (.2 * np.sin(2 * np.pi * 432 * np.arange(8192) / RATE)).astype(np.float32)
    for block in np.split(audio, 16):
        pitch = detector.process(block)
    assert abs(pitch - 432) < 2
    assert nearest_note(68.7, chord_notes(0, 'Major', 0)) == 67
    assert chord_notes(0, 'Minor', 0) == (0, 3, 7)
    assert chord_notes(0, 'Major', 4) == (7, 11, 14)
    for block in np.split(np.zeros_like(audio), 16):
        pitch = detector.process(block)
    assert pitch is None


def test_loop_undo_keeps_previous_take():
    loop = LoopTrack(16)
    loop.toggle()
    loop.process(np.full(4, .15, np.float32))
    loop.toggle()
    loop.toggle()
    loop.process(np.full(4, .28, np.float32))
    loop.toggle()
    loop.undo()
    assert np.allclose(loop.process(np.zeros(4)), .15)


def test_pitch_correction_shifts_a_sustained_tone():
    engine = AudioEngine()
    engine.params.update(tune=1., retune=.8)
    source = (.2 * np.sin(2 * np.pi * 425 * np.arange(RATE * 2) / RATE)).astype(np.float32)
    rendered = np.concatenate([engine.process(source[i:i+BLOCK]) for i in range(0, len(source), BLOCK)])[RATE:]
    spectrum = abs(np.fft.rfft(rendered * np.hanning(len(rendered))))
    assert spectrum.argmax() == 440


def test_project_round_trip(tmp_path):
    path = tmp_path / 'show.touchmusic'
    clip = np.arange(8, dtype=np.float32) / 16
    save_project(path, {'key': 3}, {'loop-1': clip, 'backing': clip[::-1]})
    settings, assets, voices = load_project(path)
    assert settings == {'key': 3}
    assert not voices
    np.testing.assert_array_equal(assets['loop-1'], clip)
    np.testing.assert_array_equal(assets['backing'], clip[::-1])


def test_monitor_mute_keeps_recording_stems(tmp_path):
    import soundfile as sf
    engine = AudioEngine()
    engine.params.update(dialogue=True, gain=1, monitor='Dry mic')
    engine.muted = True
    path = tmp_path / 'take.wav'
    engine.recorder = Recorder(path, stems=True)
    assert not np.any(engine.process(np.full(512, .25, np.float32)))
    recorder = engine.stop_recording()
    assert not recorder.error
    mix, _ = sf.read(path)
    vocal, _ = sf.read(recorder.stem_dir / 'wet-vocal.wav')
    assert np.allclose(mix, np.tanh(.25))
    assert np.allclose(vocal, .25)
