import os
import threading
import time
import numpy as np
import pytest
from touchmusic.plugin_process import PluginProcess
from touchmusic.plugin_worker import encode_audio, decode_audio
from touchmusic.isolated_rack import IsolatedPluginRack
from touchmusic.plugin_rack import PluginRack
from test_plugin_rack import Plugin


def test_real_worker_owns_a_different_process_and_parent_survives_exit():
    client = PluginProcess()
    try:
        child = client.request('ping')['pid']
        assert child != os.getpid()
        client.request('configure', settings={'effects': []})
        signal = np.linspace(-.1, .1, 512, dtype=np.float32)
        result = client.request('process', audio=encode_audio(signal), rate=48000)
        np.testing.assert_array_equal(decode_audio(result), signal)
        client.process.kill()
        client.process.wait(timeout=3)
        with pytest.raises(RuntimeError):
            client.request('ping')
        assert os.getpid() != child
    finally:
        client.close()


def test_rpc_watchdog_kills_a_stuck_owned_worker():
    client = PluginProcess()
    try:
        client.request('ping')
        # Replace the writer with a pipe adapter that sends an unfinished frame.
        actual = client.process.stdin
        class PartialWriter:
            def write(self, payload):
                actual.write(b'{')
            def flush(self):
                actual.flush()
            def close(self):
                actual.close()
        client.process.stdin = PartialWriter()
        started = time.monotonic()
        with pytest.raises(RuntimeError):
            client.request('ping', timeout=.15)
        assert time.monotonic()-started < 3
        assert client.process.poll() is not None
    finally:
        client.close()


def test_dry_fallback_is_exactly_delayed_for_variable_blocks_and_bounded():
    rack = IsolatedPluginRack()
    rack.slots = [{'parameters': {}, 'bypass': False}]
    rack.error = 'simulated worker failure'
    signal = np.arange(20000, dtype=np.float32)
    chunks, start = [], 0
    for size in [1, 111, 400, 17, 511, 2048, 16912]:
        chunks.append(rack.process(signal[start:start+size], 48000, stereo=True))
        start += size
    result = np.concatenate(chunks, axis=1)
    expected = np.concatenate((np.zeros(2048), signal[:-2048]))
    np.testing.assert_array_equal(result[0], expected)
    np.testing.assert_array_equal(result[1], expected)
    assert len(rack.entries) <= 5
    assert rack.jobs.qsize() <= 6


def test_cached_final_parameter_value_does_not_drop_when_worker_busy():
    rack = IsolatedPluginRack()
    rack.slots = [{'path': 'test.vst3', 'plugin_name': '', 'parameters': {'gain': 0.}, 'bypass': False}]
    rack.bindings['1'] = {'slot': 0, 'parameter': 'gain'}
    for value in np.linspace(0, 1, 1000):
        assert rack.control(1, float(value))
    assert rack.slots[0]['parameters']['gain'] == 1
    assert not rack.control(1, float('nan'))
    assert rack.apply_values(rack.settings())


def test_native_backend_preserves_asymmetric_stereo(tmp_path):
    path = tmp_path/'wide.vst3'
    path.touch()
    class Wide(Plugin):
        def process(self, audio, rate, reset=False):
            return np.stack((audio[0], -audio[1]))
    rack = PluginRack(lambda *a, **k: Wide(), preserve_stereo=True)
    rack.add(path)
    output = rack.process(np.ones(512, np.float32), 48000)
    assert output.shape == (2, 512)
    np.testing.assert_array_equal(output[0], 1)
    np.testing.assert_array_equal(output[1], -1)


def test_nonfinite_or_unbounded_rpc_audio_is_rejected():
    with pytest.raises(ValueError):
        decode_audio(encode_audio(np.zeros(8193, np.float32)))
    with pytest.raises(ValueError):
        decode_audio(encode_audio(np.full(512, np.nan)))
    with pytest.raises(ValueError):
        decode_audio({'shape': [2, 512], 'pcm': ''})


def test_failed_restore_retains_previous_process_and_configuration():
    class Failed:
        closed = False
        def request(self, *a, **k):
            raise RuntimeError('native load failure')
        def close(self):
            self.closed = True
    failed = Failed()
    rack = IsolatedPluginRack(lambda: failed)
    original = {'path': 'old.vst3', 'parameters': {}, 'bypass': False}
    rack.slots = [original]
    with pytest.raises(RuntimeError):
        rack.restore({'effects': [{'path': 'new.vst3'}]})
    assert rack.slots == [original] and failed.closed
