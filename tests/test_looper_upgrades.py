import numpy as np

from touchmusic.audio import AudioEngine, LoopTrack, RATE


def test_overdub_preserves_original_and_supports_undo_redo():
    loop = LoopTrack(100)
    original = np.full(8, .2, np.float32)
    loop.load(original)
    loop.start_overdub(feedback=.5)
    np.testing.assert_allclose(loop.process(np.full(8, .3, np.float32)), .2)
    loop.toggle()
    np.testing.assert_allclose(original, .2)
    np.testing.assert_allclose(loop.clip, .4)
    loop.undo()
    np.testing.assert_allclose(loop.clip, .2)
    loop.redo()
    np.testing.assert_allclose(loop.clip, .4)


def test_count_in_and_fixed_bar_capture_finish_at_exact_frames():
    engine = AudioEngine()
    engine.params.update(dialogue=True, gain=1., bpm=120, count_in=1, capture_bars=1)
    engine.commands.put(('loop', 0))
    engine.process(np.zeros(RATE * 2 - 100, np.float32))
    assert not engine.loop.recording
    engine.process(np.full(200, .25, np.float32))
    assert engine.loop.recording and engine.loop.size == 100
    engine.process(np.full(RATE * 2 + 30, .25, np.float32))
    assert not engine.loop.recording
    assert len(engine.loop.clip) == RATE * 2
    np.testing.assert_allclose(engine.loop.clip, .25)


def test_cancel_count_in_and_clear_cancel_scheduled_finish():
    engine = AudioEngine()
    engine.params.update(dialogue=True, count_in=1, capture_bars=1)
    engine.commands.put(('loop', 0))
    engine.process(np.zeros(512, np.float32))
    engine.commands.put(('loop', 0))
    engine.process(np.zeros(RATE * 5, np.float32))
    assert not engine.loop.recording and engine.loop.clip is None
    assert not engine.clock.pending


def test_seam_fade_retains_clip_length_and_source():
    loop = LoopTrack(RATE)
    original = np.ones(4800, np.float32)
    loop.load(original)
    loop.seam_ms = 5
    output = loop.process(np.zeros(4800, np.float32))
    assert len(output) == len(original)
    assert output[0] == 0 and output[-1] == 0
    assert output[500] == 1
    np.testing.assert_array_equal(loop.clip, original)
def test_overdub_and_capture_commands_cancel_the_same_pending_count_in():
    import numpy as np
    from touchmusic.audio import AudioEngine
    engine = AudioEngine()
    engine.params['count_in'] = 1
    engine.commands.put(('loop', 0))
    engine.process(np.zeros(512, np.float32))
    assert ('loop', 0) in engine.clock.pending
    engine.commands.put(('overdub', 0))
    engine.process(np.zeros(512, np.float32))
    assert not engine.clock.pending
    assert not engine.loop.recording

