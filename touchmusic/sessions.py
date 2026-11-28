"""Crash recovery snapshots and ordered references to portable skit files."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import numpy as np
from .project import save_project, load_project


def _atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class SessionRecovery:
    """One writer with at most one active and one newest pending snapshot.

    Call submit from the UI, never the audio callback. Arrays are copied by
    default. copy_assets=False pins caller-owned arrays, which must remain
    immutable until written; use it for completed clips replaced as a whole.
    Archive publication occurs only after load_project validates the new file.
    recovery_available describes the prior shutdown, captured at construction.
    """
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.archive_path = self.directory / 'latest.touchmusic'
        self.state_path = self.directory / 'session.json'
        try:
            previous = json.loads(self.state_path.read_text('utf-8'))
            clean = isinstance(previous, dict) and previous.get('clean_shutdown') is True
        except (OSError, ValueError):
            clean = False
        self.recovery_available = self.archive_path.is_file() and not clean
        self.error = ''
        self.saved_revision = 0
        self._submitted = 0
        self._finished = 0
        self._pending = None
        self._closing = False
        self._condition = threading.Condition()
        _atomic_json(self.state_path, {'version': 1, 'clean_shutdown': False})
        self.thread = threading.Thread(target=self._run, name='TouchMusic recovery', daemon=True)
        self.thread.start()

    def submit(self, settings, assets, voices=(), *, copy_assets=True):
        """Queue a detached latest snapshot, returning its monotonic revision."""
        prepared = {name: np.array(audio, dtype=np.float32, copy=copy_assets)
                    for name, audio in assets.items()}
        snapshot = deepcopy(settings), prepared, tuple((deepcopy(voice), Path(path)) for voice, path in voices)
        with self._condition:
            if self._closing:
                raise RuntimeError('The recovery writer is closed.')
            self._submitted += 1
            self._pending = (self._submitted, snapshot)
            self._condition.notify_all()
            return self._submitted

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._pending is not None or self._closing)
                if self._pending is None:
                    return
                revision, snapshot = self._pending
                self._pending = None
            temporary = None
            failure = ''
            try:
                descriptor, name = tempfile.mkstemp(dir=self.directory, suffix='.touchmusic.tmp')
                os.close(descriptor)
                temporary = Path(name)
                save_project(temporary, *snapshot)
                load_project(temporary)
                os.replace(temporary, self.archive_path)
            except Exception as exc:
                failure = str(exc) or type(exc).__name__
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            with self._condition:
                self.error = failure
                self._finished = revision
                if not failure:
                    self.saved_revision = revision
                self._condition.notify_all()

    def load_recovery(self):
        """Return validated (settings, assets, voices), without extracting files."""
        return load_project(self.archive_path)

    def flush(self, timeout=5.):
        """Wait for the latest submitted revision; False means timeout or failure."""
        with self._condition:
            target = self._submitted
            self._condition.wait_for(lambda: self._finished >= target, timeout=max(0., timeout))
            return self.saved_revision >= target

    def close(self, clean=True, timeout=5.):
        """Finish pending saves and mark clean only if all latest state persisted.

        False leaves the crash marker dirty. An in-progress writer is allowed
        to finish after a timeout, but cannot mark the session clean itself.
        """
        deadline = time.monotonic() + max(0., timeout)
        with self._condition:
            self._closing = True
            self._condition.notify_all()
        saved = self.flush(max(0., deadline - time.monotonic()))
        self.thread.join(timeout=max(0., deadline - time.monotonic()))
        complete = saved and not self.thread.is_alive()
        if clean and complete:
            try:
                _atomic_json(self.state_path, {'version': 1, 'clean_shutdown': True})
            except Exception as exc:
                self.error = str(exc)
                return False
        return complete


class Setlist:
    """Ordered local skit paths. Loading the list never opens/extracts a skit."""
    MAX_ENTRIES = 1000

    def __init__(self, paths=(), index=0):
        self._paths = [self._path(path) for path in paths]
        if len(self._paths) > self.MAX_ENTRIES:
            raise ValueError('A setlist supports up to 1000 skits.')
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError('Invalid setlist selection.')
        if self._paths and not 0 <= index < len(self._paths):
            raise ValueError('Invalid setlist selection.')
        self.index = index if self._paths else -1

    @staticmethod
    def _path(value, base=None):
        if not isinstance(value, (str, os.PathLike)):
            raise ValueError('Each setlist entry must be a local skit path.')
        text = os.fspath(value)
        if not isinstance(text, str) or not text.strip() or '\x00' in text or '://' in text:
            raise ValueError('Each setlist entry must be a local skit path.')
        path = Path(text).expanduser()
        if path.suffix.lower() != '.touchmusic':
            raise ValueError('Setlist entries must be .touchmusic skit files.')
        if base is not None and not path.is_absolute():
            path = base / path
        return path.resolve()

    @property
    def paths(self):
        return tuple(self._paths)

    @property
    def current(self):
        return self._paths[self.index] if self._paths else None

    def select(self, index):
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(self._paths):
            raise IndexError('Select an existing skit.')
        self.index = index
        return self.current

    def add(self, path):
        if len(self._paths) >= self.MAX_ENTRIES:
            raise ValueError('A setlist supports up to 1000 skits.')
        self._paths.append(self._path(path))
        if self.index < 0:
            self.index = 0
        return len(self._paths) - 1

    def remove(self, index):
        if not 0 <= index < len(self._paths):
            raise IndexError('Select an existing skit.')
        removed = self._paths.pop(index)
        if index < self.index:
            self.index -= 1
        self.index = min(self.index, len(self._paths) - 1)
        return removed

    def move(self, source, destination):
        if not 0 <= source < len(self._paths) or not 0 <= destination < len(self._paths):
            raise IndexError('Select existing source and destination skits.')
        order = list(range(len(self._paths)))
        order.insert(destination, order.pop(source))
        self.index = order.index(self.index)
        self._paths = [self._paths[index] for index in order]

    def next(self):
        self.index = min(self.index + 1, len(self._paths) - 1)
        return self.current

    def previous(self):
        self.index = max(0, self.index - 1) if self._paths else -1
        return self.current

    def save(self, path):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        for entry in self._paths:
            try:
                entries.append(os.path.relpath(entry, path.parent))
            except ValueError:  # Windows paths on different drives.
                entries.append(str(entry))
        _atomic_json(path, {'version': 1, 'index': self.index, 'paths': entries})

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Setlist file is too large.')
        document = json.loads(path.read_text('utf-8'))
        if not isinstance(document, dict) or document.get('version') != 1:
            raise ValueError('Unsupported TouchMusic setlist format.')
        entries = document.get('paths')
        if not isinstance(entries, list) or len(entries) > cls.MAX_ENTRIES:
            raise ValueError('Invalid setlist entries.')
        return cls([cls._path(entry, path.parent) for entry in entries], document.get('index', 0))
