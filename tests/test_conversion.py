import time
import numpy as np
from touchmusic.neural import StreamingConverter


class DeterministicBackend:
    """Fast test double for queue behavior, independent of GPU weights."""
    reference_path = None

    def set_reference(self, path):
        self.reference_path = path

    def convert(self, audio):
        time.sleep(.01)
        return np.full_like(audio, .2 if self.reference_path == 'one' else .8)


def wait_until(predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        time.sleep(.01)
    assert predicate()


def test_voice_switch_discards_old_output():
    converter = StreamingConverter(DeterministicBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        converter.process(np.ones(converter.hop, np.float32))
        wait_until(lambda: not converter.results.empty())
        converter.select('two')
        wait_until(lambda: converter.ready)
        output = converter.process(np.ones(converter.hop, np.float32))
        assert not output.any()
        wait_until(lambda: not converter.results.empty())
        output = converter.process(np.ones(converter.hop, np.float32))
        assert np.allclose(output[960:], .8)
    finally:
        converter.close()


def test_input_queue_is_bounded():
    converter = StreamingConverter(DeterministicBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        for _ in range(50):
            converter.process(np.ones(converter.hop, np.float32))
        assert converter.requests.qsize() <= 2
        assert converter.dropped > 0
    finally:
        converter.close()


def test_reselecting_same_reference_remains_ready():
    converter = StreamingConverter(DeterministicBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        converter.select('one')
        wait_until(lambda: converter.ready)
    finally:
        converter.close()


def test_dry_ai_blend_uses_the_same_captured_chunk():
    converter = StreamingConverter(DeterministicBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        converter.process(np.full(converter.hop, .6, np.float32))
        wait_until(lambda: not converter.results.empty())
        output = converter.process(np.zeros(converter.hop, np.float32), mix=.5)
        np.testing.assert_allclose(output[960:], .4, atol=1e-6)
    finally:
        converter.close()


def test_provenance_tracks_overlap_and_unavailable_audio():
    converter = StreamingConverter(DeterministicBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        start = 2 ** 35
        converter.process(np.ones(converter.hop, np.float32), start_frame=start)
        assert np.all(converter.source_frames == -1)
        wait_until(lambda: not converter.results.empty())
        converter.process(np.zeros(512, np.float32), start_frame=start + converter.hop)
        np.testing.assert_array_equal(converter.source_frames, np.arange(start - 960, start - 448))
        converter.select('two')
        converter.process(np.zeros(512, np.float32), start_frame=start + converter.hop + 512)
        assert np.all(converter.source_frames == -1)
    finally:
        converter.close()


def test_capture_gap_does_not_relabel_stale_context():
    windows = []

    class CapturingBackend(DeterministicBackend):
        def convert(self, audio):
            windows.append(audio.copy())
            return super().convert(audio)

    converter = StreamingConverter(CapturingBackend)
    try:
        converter.select('one')
        wait_until(lambda: converter.ready)
        converter.process(np.ones(converter.hop, np.float32), start_frame=0)
        wait_until(lambda: len(windows) == 1)
        converter.process(np.ones(converter.hop, np.float32), start_frame=converter.hop * 2)
        wait_until(lambda: len(windows) == 2)
        assert not windows[1][:converter.hop].any()
    finally:
        converter.close()
