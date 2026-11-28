import copy
import numpy as np
import pytest
import soundfile as sf
from touchmusic.motion_score import MotionScore
from touchmusic.audio import AudioEngine, Recorder, RATE


def test_record_save_restore_edit_and_replay_with_tempo_changes():
    score = MotionScore()
    score.start('Recording', 100)
    score.capture('action', 'Chord I')
    score.advance(24100, 24000)
    score.capture('level', 'Plugin knob 1', .7)
    score.advance(36100, 12000)
    score.capture('level', 'Plugin knob 1', .9)
    assert [e['beat'] for e in score.events] == [0, 1, 2]
    saved = score.settings()
    score.load(saved)
    assert score.mode == 'Stopped'
    score.start('Playing', 500)
    assert score.advance(500, 24000)[0]['target'] == 'Chord I'
    assert not score.advance(12000, 24000)
    assert score.advance(24500, 24000)[0]['value'] == .7
    assert score.advance(36500, 12000)[0]['value'] == .9
    assert score.mode == 'Stopped'
    assert score.settings() == saved


@pytest.mark.parametrize('event', [
    {'beat': float('nan'), 'kind': 'action', 'target': 'Chord I'},
    {'beat': 0, 'kind': 'level', 'target': 'Reverb', 'value': float('inf')},
    {'beat': 0, 'kind': 'shell', 'target': 'command'},
    {'beat': -1, 'kind': 'action', 'target': 'Chord I'},
])
def test_invalid_score_does_not_replace_existing_performance(event):
    score = MotionScore()
    score.events = [{'beat': 0, 'kind': 'action', 'target': 'Chord I'}]
    old = copy.deepcopy(score.events)
    with pytest.raises(ValueError):
        score.load({'version': 1, 'events': [event]})
    assert score.events == old


def test_stereo_master_and_recording_preserve_channel_difference(tmp_path):
    engine = AudioEngine()
    class WideRack:
        slots = []
        def process(self, audio, rate, stereo=False):
            return np.stack((np.ones(len(audio))*.1, np.ones(len(audio))*.3))
    engine.rack = WideRack()
    path = tmp_path/'stereo.wav'
    engine.recorder = Recorder(path, stems=True, channels=2)
    output = engine.process(np.zeros(512, np.float32), stereo=True)
    engine.recorder.close()
    assert output.shape == (512, 2)
    assert np.all(output[:, 1] > output[:, 0])
    recorded, rate = sf.read(path, always_2d=True)
    np.testing.assert_allclose(recorded, output, atol=1e-6)
    assert sf.info(tmp_path/'stereo-stems/wet-vocal.wav').channels == 2
    assert sf.info(tmp_path/'stereo-stems/dry-mic.wav').channels == 2
    assert rate == RATE
