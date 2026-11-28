import numpy as np

from touchmusic.audio import AudioEngine, BLOCK


def test_four_loop_tracks_layer_and_export_independently():
    engine = AudioEngine()
    assert len(engine.loops) == 4
    low = np.full(BLOCK, .1, dtype=np.float32)
    high = np.full(BLOCK, .2, dtype=np.float32)
    engine.params['dialogue'] = True
    engine.params['gain'] = 1
    for index, sound in enumerate((low, high)):
        engine.commands.put(('loop', index))
        engine.process(sound)
        engine.commands.put(('loop', index))
        engine.process(np.zeros_like(sound))
    first = engine.loops[0].clip
    np.testing.assert_allclose(first, low)
    np.testing.assert_allclose(engine.loops[1].clip, high)
    np.testing.assert_allclose(engine.process(np.zeros_like(low)), np.tanh(low*.7 + high*.7))
    engine.commands.put(('mute', 0))
    np.testing.assert_allclose(engine.process(np.zeros_like(low)), np.tanh(high*.7))
    engine.commands.put(('loop', 0))
    engine.process(high)
    engine.commands.put(('loop', 0))
    engine.process(low)
    np.testing.assert_allclose(first, low)


def test_dialogue_bypasses_coloring_effects():
    engine = AudioEngine()
    engine.params.update(gain=1, dialogue=True, robot=1, pitch=-12, harmony=1, radio=1, drive=1)
    voice = np.linspace(-.5, .5, BLOCK, dtype=np.float32)
    np.testing.assert_allclose(engine.process(voice), np.tanh(voice))
