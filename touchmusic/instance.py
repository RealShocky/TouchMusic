"""One settings/recovery writer per data directory, with local focus handoff."""
import hashlib
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, QLockFile, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        data = Path(data).resolve()
        data.mkdir(parents=True, exist_ok=True)
        self.name = 'TouchMusic-'+hashlib.sha256(str(data).casefold().encode()).hexdigest()[:24]
        self.lock = QLockFile(str(data/'touchmusic-instance.lock'))
        self.focus_file = data/'instance-focus.request'
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.check_focus_file)
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.accept)
        self.window = None
        self.pending_focus = False
        self.focus_requests = 0
        self.owned = False

    def acquire(self):
        if not self.lock.tryLock(0):
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if socket.waitForConnected(500):
                socket.write(b'focus\n')
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
            else:
                descriptor, name = tempfile.mkstemp(dir=self.focus_file.parent, suffix='.focus')
                try:
                    with os.fdopen(descriptor, 'wb') as output:
                        output.write(b'focus\n')
                    os.replace(name, self.focus_file)
                finally:
                    Path(name).unlink(missing_ok=True)
            return False
        self.owned = True
        QLocalServer.removeServer(self.name)
        self.server.listen(self.name)
        # Restricted Windows environments can deny named pipes. The lock still
        # enforces ownership; a bounded file signal provides the focus handoff.
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

    def accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            def read(connection=socket):
                message = bytes(connection.read(33))
                if message.strip() == b'focus':
                    self.focus_requests += 1
                    self.focus()
                connection.disconnectFromServer()
                connection.deleteLater()
            socket.readyRead.connect(read)
            if socket.bytesAvailable():
                read()

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
            self.server.close()
            self.lock.unlock()
            self.owned = False
