import numpy as np
import pytest
from touchmusic.instrument import InstrumentBus
from touchmusic.instrument_backend import InstrumentBackend
from test_plugin_rack import Parameter


def test_normalized_adapter_avoids_range_inference_and_preserves_duplicate_names(monkeypatch):
    import pedalboard
    from touchmusic.instrument_backend import load_instrument
    class RawParameter:
        name = 'Volume'
        raw_value = .5
    class Native:
        def __init__(self, path, plugin_name=None):
            self._parameters = [RawParameter(), RawParameter()]
        @property
        def parameters(self):
            raise AssertionError('Range inference must not run.')
    monkeypatch.setattr(pedalboard, 'VST3Plugin', Native)
    plugin = load_instrument('test.vst3')
    assert list(plugin.parameters) == ['0000_Volume', '0001_Volume']
    plugin.parameters['0001_Volume'].raw_value = .7
    assert plugin.parameters['0001_Volume'].raw_value == .7


def bus():
    value = InstrumentBus()
    value.slots = [{'path': 'synth.vst3', 'parameters': {'gain': .5}, 'bypass': False}]
    return value


def test_timed_instrument_note_release_and_panic_discards_old_commands():
    value = bus()
    assert value.play([60, 64, 67], duration=.5)
    attack = value._midi(0, 512, 48000)
    assert [e[0][1] for e in attack if e[0][0] == 0x90] == [60, 64, 67]
    assert not value._midi(512, 512, 48000)
    release = value._midi(24000, 512, 48000)
    assert len(release) == 3 and all(e[0][0] == 0x80 for e in release)
    value.play([72])
    value.panic()
    assert all(e[0][0] == 0xB0 for e in value._midi(24512, 512, 48000))
    assert not value.active and not value.events


def test_retriggered_pitch_does_not_receive_an_old_note_off():
    value = bus()
    value.play([60], duration=.1)
    value._midi(0, 512, 48000)
    value.position = 2400
    value.play([60], duration=.5)
    value._midi(2400, 512, 48000)
    assert not value._midi(4800, 512, 48000)
    assert value.active[60]


def test_instrument_limits_and_silent_crash_fallback():
    value = bus()
    for notes in ([128], [], [True]):
        with pytest.raises(ValueError):
            value.play(notes)
    value.error = 'native fault'
    assert not value.play([60])
    assert not value.read(8192).any()
    assert len(value.entries) <= 5
    with pytest.raises(ValueError):
        value.validate({'effects': [{'path': 'a.vst3'}, {'path': 'b.vst3'}]})
    value.validate({'effects': [{'path': 'large.vst3', 'parameters': {str(i): .5 for i in range(2855)}}]})


def test_worker_instrument_backend_renders_stereo_midi_and_rejects_effects(tmp_path):
    path = tmp_path/'synth.vst3'
    path.touch()
    class Synth:
        is_instrument = True
        parameters = {'gain': Parameter()}
        def process(self, midi, sample_rate, duration, num_channels, reset):
            assert midi == [([0x90, 60, 96], 0.)] and not reset
            return np.ones((num_channels, round(duration*sample_rate)), np.float32)*.2
    backend = InstrumentBackend(lambda *a, **k: Synth())
    backend.restore({'effects': [{'path': str(path)}]})
    assert backend.process(512, 48000, [([0x90, 60, 96], 0.)]).shape == (2, 512)
    with pytest.raises(ValueError):
        backend.process(512, 48000, [([0x90, 140, 96], 0.)])
