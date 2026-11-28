import socket
import time
import numpy as np
import pytest
from touchmusic.audio_bridge import AudioBridge, encode_packet, decode_packet, HEADER
from touchmusic.audio import AudioEngine


def test_audio_packet_bounds_rate_finite_samples_and_instance():
    audio = np.ones((512, 2), np.float32)*.1
    raw = encode_packet(123, 512, audio)
    identity, frame, result = decode_packet(raw)
    assert identity == 123 and frame == 512
    np.testing.assert_array_equal(result, audio)
    for bad in (raw[:-1], raw+b'x', encode_packet(0, 0, audio), encode_packet(1, 1, audio)):
        with pytest.raises(ValueError):
            decode_packet(bad)
    header = list(HEADER.unpack_from(raw))
    header[4] = 44100
    with pytest.raises(ValueError):
        decode_packet(HEADER.pack(*header)+raw[HEADER.size:])
    with pytest.raises(ValueError):
        encode_packet(1, 0, audio*np.nan)


def test_actual_engine_roundtrip_over_localhost_and_duplicate_rejection():
    engine = AudioEngine()
    engine.params.update(dialogue=True, gain=.7)
    bridge = AudioBridge(engine, port=0)
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(2)
    try:
        bridge.start()
        assert engine.external and not engine.stream
        audio = np.ones((512, 2), np.float32)*.1
        raw = encode_packet(9, 0, audio)
        client.sendto(raw, ('127.0.0.1', bridge.port))
        packet, _ = client.recvfrom(8192)
        identity, frame, wet = decode_packet(packet, kind=2)
        assert identity == 9 and frame == 0
        np.testing.assert_allclose(wet, np.tanh(.07), atol=1e-6)
        client.sendto(raw, ('127.0.0.1', bridge.port))
        deadline = time.monotonic()+1
        while not bridge.rejected and time.monotonic() < deadline:
            time.sleep(.005)
        assert bridge.rejected == 1 and bridge.packets == 1
        with pytest.raises(ValueError):
            engine.start(None, None)
    finally:
        client.close()
        assert bridge.close()
    assert not engine.external


def test_daw_return_uses_enabled_converter_without_opening_devices():
    engine = AudioEngine()
    class Converter:
        def process(self, audio, mix, start_frame):
            self.source_frames = np.arange(start_frame, start_frame+len(audio))
            return audio*.5
    engine.converter = Converter()
    engine.neural = True
    engine.params.update(dialogue=True, gain=1.)
    wet = engine.process(np.ones(512, np.float32)*.2, stereo=True)
    np.testing.assert_allclose(wet, np.tanh(.1), atol=1e-6)
