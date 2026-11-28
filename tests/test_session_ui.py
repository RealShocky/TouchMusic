import numpy as np
from touchmusic import ui
from touchmusic.library import VoiceLibrary
from touchmusic.project import save_project
from touchmusic.sessions import SessionRecovery


def test_pending_recovery_survives_startup_and_restores_completed_loop(tmp_path, monkeypatch):
    clip = np.full(1024, .2, np.float32)
    recovery = SessionRecovery(tmp_path / 'recovery')
    recovery.submit({'music': {'bpm': 96}}, {'loop-1': clip})
    assert recovery.close(clean=False)
    original = recovery.archive_path.read_bytes()
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    window = ui.MainWindow()
    try:
        assert window.recovery_pending
        window.backup_session(force=True)
        assert recovery.archive_path.read_bytes() == original
        window.restore_recovery()
        assert not window.recovery_pending
        np.testing.assert_array_equal(window.engine.loop.clip, clip)
        assert window.engine.params['bpm'] == 96
        assert not window.arm.isChecked()
        window.music_controls['capture_bars'].setCurrentIndex(3)
        window.music_controls['count_in'].setValue(2)
        window.music_controls['overdub_feedback'].setValue(75)
        assert window.engine.params['capture_bars'] == 4
        assert window.engine.params['count_in'] == 2
        assert window.engine.params['overdub_feedback'] == .75
    finally:
        window.close()


def test_setlist_recall_and_failed_song_preserve_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    first, second = tmp_path / 'first.touchmusic', tmp_path / 'second.touchmusic'
    save_project(first, {'music': {'bpm': 100}}, {})
    save_project(second, {'music': {'bpm': 140}}, {})
    window = ui.MainWindow()
    try:
        dialog = window.setlist_dialog
        dialog.model.add(first)
        dialog.model.add(second)
        assert dialog.open_index(0)
        window.gesture_action('Next song')
        assert dialog.model.index == 1
        assert window.engine.params['bpm'] == 140
        first.unlink()
        window.gesture_action('Previous song')
        assert dialog.model.index == 1
        assert window.engine.params['bpm'] == 140
    finally:
        window.close()
