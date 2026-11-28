import time
import numpy as np
from touchmusic.audition import AuditionJob
from touchmusic.neural import StreamingConverter


class Backend:
    reference_path = None

    def set_reference(self, reference):
        self.reference_path = reference

    def convert(self, audio, rate=48000, steps=4):
        return audio * (.5 if self.reference_path == 'one' else .8)


def test_comparison_uses_same_source_preserves_duration_and_cancels():
    audio = np.linspace(-.5, .5, 100000, dtype=np.float32)
    job = AuditionJob(audio, [('one', 'Live'), ('two', 'Studio')])
    job.run(Backend())
    assert job.done.is_set() and not job.error
    np.testing.assert_allclose(job.results[0]['audio'], audio*.5, atol=1e-6)
    np.testing.assert_allclose(job.results[1]['audio'], audio*.8, atol=1e-6)
    assert len(job.results[1]['audio']) == len(audio)
    cancelled = AuditionJob(audio, [('one', 'Live')])
    cancelled.cancel.set()
    cancelled.run(Backend())
    assert not cancelled.results and cancelled.status == 'Cancelled'


def test_comparison_serializes_on_existing_worker_and_restores_reference():
    converter = StreamingConverter(Backend)
    try:
        converter.select('one')
        deadline = time.monotonic()+3
        while not converter.ready and time.monotonic() < deadline:
            time.sleep(.01)
        job = converter.submit_audition(np.full(48000, .2, np.float32), [('two', 'Studio')])
        assert job.done.wait(3)
        deadline = time.monotonic()+3
        while not converter.ready and time.monotonic() < deadline:
            time.sleep(.01)
        assert converter.ready and not converter.audition_busy and not converter.error
        assert converter.reference == 'one'
        np.testing.assert_allclose(job.results[0]['audio'], .16, atol=1e-6)
    finally:
        converter.close()
