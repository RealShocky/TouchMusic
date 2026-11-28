import time
import subprocess
import sys
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


def test_focus_request_survives_sender_exit_before_owner_processes_events(tmp_path, qt_application):
    first = SingleInstance(tmp_path)
    try:
        assert first.acquire()
        code = ('import sys; from PySide6.QtCore import QCoreApplication; '
                'from touchmusic.instance import SingleInstance; '
                'app=QCoreApplication([]); other=SingleInstance(sys.argv[1]); '
                'assert not other.acquire(); other.close()')
        subprocess.run([sys.executable, '-c', code, str(tmp_path)], check=True, timeout=10)
        deadline = time.monotonic()+2
        while first.focus_requests == 0 and time.monotonic() < deadline:
            qt_application.processEvents()
            time.sleep(.005)
        assert first.focus_requests == 1 and first.pending_focus
    finally:
        first.close()
