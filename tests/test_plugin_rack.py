import numpy as np
import pytest
from touchmusic.plugin_rack import PluginRack


class Parameter:
    raw_value = 1.


class Plugin:
    is_instrument = False
    num_input_channels = 2

    def __init__(self):
        self.parameters = {'gain': Parameter()}

    def process(self, audio, rate, reset=False):
        assert not reset
        return audio*self.parameters['gain'].raw_value


def test_plugin_rack_gesture_state_order_and_nonblocking_bypass(tmp_path):
    path = tmp_path/'test.vst3'
    path.touch()
    rack = PluginRack(lambda *args, **kwargs: Plugin())
    rack.add(path)
    rack.add(path)
    rack.bindings['1'] = {'slot': 0, 'parameter': 'gain'}
    assert rack.control(1, .5)
    np.testing.assert_allclose(rack.process(np.ones(512, np.float32), 48000), .5)
    saved = rack.settings()
    rack.move(0, 1)
    assert rack.bindings['1']['slot'] == 1
    rack.restore(saved)
    assert rack.bindings['1']['slot'] == 0
    rack.lock.acquire()
    try:
        np.testing.assert_array_equal(rack.process(np.ones(512), 48000), 1)
        assert rack.bypassed_blocks == 1
    finally:
        rack.lock.release()
    rack.remove(0)
    assert not rack.bindings
    with pytest.raises(ValueError):
        rack.add(tmp_path/'not-a-plugin.dll')


def test_failed_plugin_is_bypassed_and_restore_preserves_existing_rack(tmp_path):
    path = tmp_path/'test.vst3'
    path.touch()
    rack = PluginRack(lambda *args, **kwargs: Plugin())
    rack.add(path)
    rack.slots[0]['plugin'].process = lambda *args, **kwargs: np.full(512, np.nan)
    assert np.isfinite(rack.process(np.ones(512), 48000)).all()
    assert rack.slots[0]['bypass'] and rack.error
    with pytest.raises(ValueError):
        rack.restore({'effects': [{'path': str(tmp_path/'missing.vst3')}]})
    assert len(rack.slots) == 1
