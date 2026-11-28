"""One settings/recovery writer per data directory, with local focus handoff."""
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, QLockFile, QTimer


class SingleInstance(QObject):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        data = Path(data).resolve()
        data.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(data/'touchmusic-instance.lock'))
        self.focus_file = data/'instance-focus.request'
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.check_focus_file)
        self.lock.setStaleLockTime(0)
        self.window = None
        self.pending_focus = False
        self.focus_requests = 0
        self.owned = False

    def acquire(self):
        if not self.lock.tryLock(0):
            # A short-lived Windows local socket can disconnect before the UI
            # event loop accepts/reads it. Persist a bounded coalesced request so
            # delivery survives sender exit and named-pipe restrictions alike.
            descriptor, name = tempfile.mkstemp(dir=self.focus_file.parent, suffix='.focus')
            try:
                with os.fdopen(descriptor, 'wb') as output:
                    output.write(b'focus\n')
                os.replace(name, self.focus_file)
            finally:
                Path(name).unlink(missing_ok=True)
            return False
        self.owned = True
        self.timer.start()
        return True

    def check_focus_file(self):
        try:
            if self.focus_file.is_file():
                with self.focus_file.open('rb') as source:
                    message = source.read(33)
                self.focus_file.unlink()
                if message == b'focus\n':
                    self.focus_requests += 1
                    self.focus()
        except OSError:
            pass

    def set_window(self, window):
        self.window = window
        if self.pending_focus:
            self.focus()

    def focus(self):
        if self.window is None:
            self.pending_focus = True
            return
        self.pending_focus = False
        if self.window.isMinimized():
            self.window.showNormal()
        else:
            self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def close(self):
        if self.owned:
            self.timer.stop()
            self.lock.unlock()
            self.owned = False
