import threading
import numpy as np
import pytest
from touchmusic.sessions import SessionRecovery, Setlist


def test_recovery_retains_detached_snapshot_and_clean_shutdown(tmp_path):
    session = SessionRecovery(tmp_path)
    audio = np.full(480, .2, np.float32)
    settings = {'music': {'bpm': 100}}
    session.submit(settings, {'loop-1': audio})
    audio.fill(.8)
    settings['music']['bpm'] = 180
    assert session.flush(5)
    saved, assets, _ = session.load_recovery()
    assert saved['music']['bpm'] == 100
    np.testing.assert_allclose(assets['loop-1'], .2)
    assert session.close(clean=False)
    resumed = SessionRecovery(tmp_path)
    assert resumed.recovery_available
    assert resumed.close(clean=True)
    clean = SessionRecovery(tmp_path)
    assert not clean.recovery_available
    assert clean.close()


def test_partial_failure_preserves_previous_usable_archive(tmp_path):
    session = SessionRecovery(tmp_path)
    try:
        session.submit({'music': {'bpm': 90}}, {'loop-1': np.ones(100, np.float32)})
        assert session.flush(5)
        session.submit({'music': {'bpm': 130}}, {'unrecognized': np.ones(100, np.float32)})
        assert not session.flush(5)
        assert session.error
        assert session.load_recovery()[0]['music']['bpm'] == 90
    finally:
        assert not session.close(clean=True)
    resumed = SessionRecovery(tmp_path)
    assert resumed.recovery_available
    resumed.close()


def test_writer_coalesces_pending_snapshots(tmp_path, monkeypatch):
    import touchmusic.sessions as module
    actual = module.save_project
    entered, release = threading.Event(), threading.Event()
    calls = []

    def held_save(path, settings, assets, voices):
        calls.append(settings['music']['bpm'])
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return actual(path, settings, assets, voices)

    monkeypatch.setattr(module, 'save_project', held_save)
    session = SessionRecovery(tmp_path)
    try:
        session.submit({'music': {'bpm': 100}}, {})
        assert entered.wait(5)
        for bpm in range(101, 120):
            session.submit({'music': {'bpm': bpm}}, {})
        release.set()
        assert session.flush(5)
        assert calls == [100, 119]
        assert session.load_recovery()[0]['music']['bpm'] == 119
    finally:
        release.set()
        session.close()


def test_setlist_order_selection_and_relative_roundtrip(tmp_path):
    paths = [tmp_path / f'{name}.touchmusic' for name in ('one', 'two', 'three')]
    setlist = Setlist(paths)
    assert setlist.previous() == paths[0]
    assert setlist.next() == paths[1]
    setlist.move(1, 0)
    assert setlist.current == paths[1] and setlist.index == 0
    setlist.remove(0)
    assert setlist.current == paths[0]
    output = tmp_path / 'show.setlist'
    setlist.save(output)
    assert str(tmp_path) not in output.read_text('utf-8')
    restored = Setlist.load(output)
    assert restored.paths == (paths[0], paths[2])
    assert restored.next() == paths[2]
    assert restored.next() == paths[2]
    restored.remove(1)
    restored.remove(0)
    assert restored.current is None and restored.next() is None


def test_setlist_rejects_invalid_entries_without_opening_projects(tmp_path):
    path = tmp_path / 'bad.setlist'
    path.write_text('{"version":1,"index":0,"paths":["https://example.com/x.touchmusic"]}')
    with pytest.raises(ValueError):
        Setlist.load(path)
    path.write_text('{"version":1,"index":0,"paths":["missing.touchmusic"]}')
    assert Setlist.load(path).current == tmp_path / 'missing.touchmusic'


def test_timed_out_shutdown_retains_crash_recovery(tmp_path, monkeypatch):
    import touchmusic.sessions as module
    actual = module.save_project
    entered, release = threading.Event(), threading.Event()

    def held_save(path, settings, assets, voices):
        entered.set()
        assert release.wait(5)
        actual(path, settings, assets, voices)

    monkeypatch.setattr(module, 'save_project', held_save)
    session = SessionRecovery(tmp_path)
    session.submit({}, {})
    try:
        assert entered.wait(5)
        assert not session.close(timeout=.01)
        with pytest.raises(RuntimeError, match='closed'):
            session.submit({}, {})
    finally:
        release.set()
        session.thread.join(timeout=5)
    resumed = SessionRecovery(tmp_path)
    assert resumed.recovery_available
    resumed.close()


def test_corrupt_recovery_is_offered_but_validated_before_use(tmp_path):
    (tmp_path / 'latest.touchmusic').write_bytes(b'broken archive')
    (tmp_path / 'session.json').write_text('broken marker')
    session = SessionRecovery(tmp_path)
    try:
        assert session.recovery_available
        from zipfile import BadZipFile
        with pytest.raises(BadZipFile):
            session.load_recovery()
    finally:
        session.close(clean=False)
def test_recovery_history_is_bounded_and_can_restore_prior_snapshot(tmp_path):
    session = SessionRecovery(tmp_path)
    session.HISTORY_COUNT = 2
    try:
        for bpm in (90, 100, 110, 120):
            session.submit({'music': {'bpm': bpm}}, {})
            assert session.flush(5)
        snapshots = session.snapshots()
        assert len(snapshots) == 3
        assert session.load_recovery(snapshots[1])[0]['music']['bpm'] == 110
        assert session.load_recovery(snapshots[2])[0]['music']['bpm'] == 100
    finally:
        session.close()

