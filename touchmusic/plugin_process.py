"""Owned native-plugin child process with bounded framing and a kill watchdog."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from .plugin_worker import MAX_MESSAGE


class PluginProcess:
    def __init__(self):
        executable = Path(sys.executable)
        if executable.name.lower() == 'pythonw.exe':
            executable = executable.with_name('python.exe')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent) + os.pathsep + env.get('PYTHONPATH', '')
        self.process = subprocess.Popen([str(executable), '-m', 'touchmusic.plugin_worker'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.lock = threading.Lock()

    def request(self, action, timeout=10, **values):
        payload = json.dumps({'action': action, **values}, allow_nan=False,
                             separators=(',', ':')).encode('utf-8') + b'\n'
        if len(payload) > MAX_MESSAGE:
            raise ValueError('Plugin request exceeds limit.')
        with self.lock:
            if self.process.poll() is not None:
                raise RuntimeError('Plugin worker exited. Stop audio and restart the rack.')
            watchdog = threading.Timer(timeout, self.kill) if timeout is not None else None
            if watchdog:
                watchdog.daemon = True
                watchdog.start()
            try:
                self.process.stdin.write(payload)
                self.process.stdin.flush()
                line = self.process.stdout.readline(MAX_MESSAGE + 1)
                if not line or len(line) > MAX_MESSAGE or not line.endswith(b'\n'):
                    self.kill()
                    raise RuntimeError('Plugin worker crashed, timed out, or returned invalid data.')
                response = json.loads(line)
                if not response.get('ok'):
                    raise RuntimeError(response.get('error', 'Plugin worker failed.'))
                return response['result']
            except (OSError, ValueError) as exc:
                self.kill()
                raise RuntimeError('Plugin communication failed: ' + str(exc)) from exc
            finally:
                if watchdog:
                    watchdog.cancel()

    def kill(self):
        if self.process.poll() is None:
            try:
                self.process.kill()
            except OSError:
                pass

    def close(self):
        self.kill()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        for stream in (self.process.stdin, self.process.stdout):
            stream.close()
