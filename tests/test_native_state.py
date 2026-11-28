import base64
import hashlib
import json
import threading
from zipfile import ZipFile
import pytest
from touchmusic.plugin_state import StateStore, MAX_STATE
from touchmusic.isolated_rack import IsolatedPluginRack
from touchmusic.project import save_project, load_project


class StateClient:
    def __init__(self):
        self.raw = b'factory'
        self.closed = False
        self.writes = 0
    def request(self, action, **kw):
        if action == 'configure':
            self.settings = kw['settings']
            return self.settings
        if action == 'set_values':
            return True
        if action == 'state_info':
            return {'size': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()}
        if action == 'state_read':
            return base64.b64encode(self.raw[kw['offset']:kw['offset']+65536]).decode()
        if action == 'state_begin':
            self.incoming = bytearray()
        elif action == 'state_write':
            assert kw['offset'] == len(self.incoming)
            self.incoming.extend(base64.b64decode(kw['data']))
            self.writes += 1
        elif action == 'state_commit':
            self.raw = bytes(self.incoming)
        elif action == 'inspect':
            return self.settings
        return True
    def kill(self):
        self.closed = True
    def close(self):
        self.closed = True


def test_large_native_state_chunks_restore_and_changed_binary_rolls_back(tmp_path):
    path = tmp_path/'native.vst3'
    path.write_bytes(b'binary-v1')
    clients = []
    def factory():
        value = StateClient()
        clients.append(value)
        return value
    rack = IsolatedPluginRack(factory, StateStore(tmp_path/'states'))
    try:
        rack.restore({'effects': [{'path': str(path), 'plugin_name': '', 'parameters': {'gain': .5}, 'bypass': False}]})
        clients[0].raw = b'program-with-hidden-values' * 100000
        rack.capture_states()
        saved = rack.settings()
        identity = saved['effects'][0]['state_id']
        assert rack.state_store.get(identity) == clients[0].raw
        rack.restore(saved)
        assert clients[1].raw == clients[0].raw and clients[1].writes > 32
        path.write_bytes(b'binary-v2')
        with pytest.raises(ValueError, match='binary changed'):
            rack.restore(saved)
        assert rack.client is clients[1] and clients[2].closed
    finally:
        rack.close()


def test_portable_project_contains_deduplicated_checked_states_and_legacy_stays_readable(tmp_path):
    store = StateStore(tmp_path/'source')
    identity = store.put(b'opaque-program')
    settings = {'plugins': {'effects': [{'path': 'a.vst3', 'state_id': identity}]},
                'scenes': {'again': {'plugins': {'effects': [{'path': 'a.vst3', 'state_id': identity}]}}}}
    path = tmp_path/'portable.touchmusic'
    save_project(path, settings, {}, state_store=store)
    with ZipFile(path) as archive:
        assert len([n for n in archive.namelist() if n.startswith('plugin-states/')]) == 1
    target = StateStore(tmp_path/'target')
    restored, _, _ = load_project(path, state_store=target)
    assert restored == settings and target.get(identity) == b'opaque-program'
    bad = tmp_path/'tampered.touchmusic'
    with ZipFile(path) as source, ZipFile(bad, 'w') as output:
        for name in source.namelist():
            output.writestr(name, b'tampered' if name.startswith('plugin-states/') else source.read(name))
    with pytest.raises(ValueError, match='checksum'):
        load_project(bad, state_store=StateStore(tmp_path/'never-imported'))
    assert not (tmp_path/'never-imported').exists()


def test_state_store_rejects_traversal_oversize_and_corruption(tmp_path):
    store = StateStore(tmp_path)
    with pytest.raises(ValueError):
        store.get('../bad')
    with pytest.raises(ValueError):
        store.put(b'x'*(MAX_STATE+1))
    identity = store.put(b'correct')
    (tmp_path/(identity+'.bin')).write_bytes(b'wrong')
    with pytest.raises(ValueError, match='checksum'):
        store.get(identity)


def test_shutdown_cancels_owned_candidate_without_committing(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class Loading(StateClient):
        def request(self, action, **kw):
            entered.set()
            release.wait(2)
            raise RuntimeError('cancelled')
        def kill(self):
            self.closed = True
            release.set()
    client = Loading()
    rack = IsolatedPluginRack(lambda: client)
    errors = []
    def run():
        try:
            rack.restore({'effects': [{'path': 'loading.vst3'}]})
        except RuntimeError as exc:
            errors.append(str(exc))
    thread = threading.Thread(target=run)
    thread.start()
    assert entered.wait(1)
    rack.close()
    thread.join(2)
    assert not thread.is_alive() and errors and client.closed
    assert rack.client is None and not rack.slots and not rack.loading
