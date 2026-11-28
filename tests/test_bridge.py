import json
import socket
import time
import numpy as np
import pytest
from touchmusic.bridge import LocalBridge, decode_packet, PROTOCOL
from touchmusic.audio import AudioEngine


def packet(sequence=1, identity='plugin1'):
    return {'protocol': PROTOCOL, 'instance': identity, 'sequence': sequence,
            'tempo': 120., 'ppq': 4., 'playing': True, 'timing_valid': True,
            'sample_rate': 48000., 'sample_position': 96000., 'parameters': [0.]*10}


def test_bridge_validation_and_loopback_delivery():
    with pytest.raises(ValueError):
        decode_packet(json.dumps({**packet(), 'parameters': [float('nan')]*10}).encode())
    bridge = LocalBridge(0)
    bridge.start()
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for sequence in (1, 2):
            sender.sendto(json.dumps(packet(sequence)).encode(), ('127.0.0.1', bridge.port))
        deadline = time.monotonic()+2
        while bridge.packets < 2 and time.monotonic() < deadline:
            time.sleep(.01)
        received = bridge.consume()
        assert received['sequence'] == 2
        assert bridge.consume() is None
        sender.sendto(json.dumps(packet(3, 'other')).encode(), ('127.0.0.1', bridge.port))
        deadline = time.monotonic()+2
        while bridge.rejected < 1 and time.monotonic() < deadline:
            time.sleep(.01)
        assert bridge.rejected == 1
    finally:
        sender.close()
        bridge.close()


def test_host_sync_reanchors_clock_and_stops_capture_on_seek_or_stop():
    engine = AudioEngine()
    engine.commands.put(('host_sync', (120, 8., time.monotonic(), True)))
    engine.process(np.zeros(512, np.float32))
    assert engine.host_locked
    assert 8 <= (engine.clock.frame-engine.clock.origin)/engine.clock.period < 8.2
    engine.commands.put(('loop', 0))
    engine.process(np.ones(512, np.float32)*.1)
    assert engine.loop.recording
    engine.commands.put(('host_sync', (120, 0., time.monotonic(), True)))
    engine.process(np.zeros(512, np.float32))
    assert not engine.loop.recording and engine.loop.clip is not None
    engine.commands.put(('host_sync', (120, 0., time.monotonic(), False)))
    engine.process(np.zeros(512, np.float32))
    assert not engine.host_locked and not engine.clock.pending
