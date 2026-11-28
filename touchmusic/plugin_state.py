"""Bounded content-addressed native state; no native code runs in this store."""
import hashlib
import os
from pathlib import Path
import re
import tempfile

MAX_STATE = 8*1024*1024
MAX_PROJECT_STATES = 32*1024*1024
CHUNK = 65536


def valid_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{64}', value))


class StateStore:
    def __init__(self, root=None):
        if root is None:
            from .runtime import DATA
            root = DATA/'plugin-states'
        self.root = Path(root)

    def put(self, raw, expected=None):
        if not isinstance(raw, bytes) or len(raw) > MAX_STATE:
            raise ValueError('Native plugin state exceeds the 8 MiB limit.')
        identity = hashlib.sha256(raw).hexdigest()
        if expected is not None and identity != expected:
            raise ValueError('Native plugin state checksum mismatch.')
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(dir=self.root, suffix='.tmp')
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(raw)
            os.replace(name, self.root/(identity+'.bin'))
        finally:
            Path(name).unlink(missing_ok=True)
        return identity

    def get(self, identity):
        if not valid_id(identity):
            raise ValueError('Invalid native plugin state identity.')
        path = self.root/(identity+'.bin')
        if path.stat().st_size > MAX_STATE:
            raise ValueError('Stored native state exceeds limit.')
        with path.open('rb') as source:
            raw = source.read(MAX_STATE+1)
        if len(raw) > MAX_STATE:
            raise ValueError('Stored native state exceeds limit.')
        if hashlib.sha256(raw).hexdigest() != identity:
            raise ValueError('Stored native state checksum mismatch.')
        return raw


def state_ids(settings):
    found = set()
    def visit(value, depth):
        if depth > 16:
            raise ValueError('Performance settings are too deeply nested.')
        if isinstance(value, dict):
            if 'state_id' in value:
                identity = value['state_id']
                if not valid_id(identity):
                    raise ValueError('Invalid native plugin state identity.')
                found.add(identity)
            for child in value.values():
                visit(child, depth+1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth+1)
    visit(settings, 0)
    if len(found) > 32:
        raise ValueError('A performance supports at most 32 unique native states.')
    return found
