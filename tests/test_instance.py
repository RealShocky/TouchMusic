import time
from touchmusic.instance import SingleInstance


def test_single_writer_focus_handoff_and_clean_reacquire(tmp_path, qt_application):
    first = SingleInstance(tmp_path)
    second = SingleInstance(tmp_path)
    try:
        assert first.acquire()
        assert not second.acquire()
        deadline = time.monotonic()+1
        while first.focus_requests == 0 and time.monotonic() < deadline:
            qt_application.processEvents()
            time.sleep(.005)
        assert first.focus_requests == 1
        assert first.pending_focus
        first.close()
        assert second.acquire()
    finally:
        first.close()
        second.close()
