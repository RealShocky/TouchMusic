"""A small result-only background task. Qt widgets are touched by GUI polling only."""
import threading


class BackgroundTask:
    def __init__(self, operation):
        self.result = None
        self.error = None
        def execute():
            try:
                self.result = operation()
            except Exception as exc:
                self.error = str(exc)
        self.thread = threading.Thread(target=execute, daemon=True)
        self.thread.start()

    @property
    def done(self):
        return not self.thread.is_alive()
