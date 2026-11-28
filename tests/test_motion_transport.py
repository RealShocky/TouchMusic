import numpy as np
from touchmusic.audio import AudioEngine


def render(chunks):
    engine = AudioEngine()
    engine.params.update(dialogue=True, gain=1.)
    events = [{'beat': 0., 'kind': 'level', 'target': 'Master level', 'value': .2},
              {'beat': .01, 'kind': 'level', 'target': 'Master level', 'value': .8},
              {'beat': .03, 'kind': 'level', 'target': 'Master level', 'value': .4}]
    engine.motion.start({'version': 1, 'events': events}, {
        'Master level': {'key': 'master', 'minimum': 0, 'maximum': 100, 'divisor': 100}})
    outputs = [engine.process(np.ones(size, np.float32)*.1) for size in chunks]
    return np.concatenate(outputs), engine


def test_score_is_sample_clocked_and_independent_of_audio_block_boundaries():
    whole, first = render([1024])
    split, second = render([1, 110, 401, 17, 495])
    np.testing.assert_allclose(whole, split, atol=1e-7)
    np.testing.assert_allclose(whole[:240], np.tanh(.02), atol=1e-7)
    np.testing.assert_allclose(whole[240:720], np.tanh(.08), atol=1e-7)
    np.testing.assert_allclose(whole[720:], np.tanh(.04), atol=1e-7)
    assert [frame for _, _, frame in first.motion.drain()] == [0, 240, 720]
    assert not first.motion.running and not second.motion.running


def test_tempo_change_recomputes_future_score_frames_on_the_audio_clock():
    engine = AudioEngine()
    engine.params['dialogue'] = True
    engine.motion.start({'version': 1, 'events': [
        {'beat': 0, 'kind': 'level', 'target': 'Tempo', 'value': 1.},
        {'beat': 1, 'kind': 'level', 'target': 'Master level', 'value': .5}]}, {
        'Tempo': {'key': 'bpm', 'minimum': 40, 'maximum': 240, 'divisor': 1},
        'Master level': {'key': 'master', 'minimum': 0, 'maximum': 100, 'divisor': 100}})
    engine.process(np.zeros(12500, np.float32))
    assert [frame for _, _, frame in engine.motion.drain()] == [0, 12000]
    assert engine.clock.bpm == 240


def test_stop_discards_stale_gui_actions_and_dense_scores_stop_without_audio_failure():
    engine = AudioEngine()
    events = [{'beat': 0, 'kind': 'action', 'target': 'Next voice'} for _ in range(129)]
    engine.motion.start({'version': 1, 'events': events}, {})
    output = engine.process(np.zeros(512, np.float32))
    assert np.isfinite(output).all()
    assert 'Too many' in engine.motion.error and not engine.motion.running
    engine.motion.stop()
    assert not engine.motion.drain()
