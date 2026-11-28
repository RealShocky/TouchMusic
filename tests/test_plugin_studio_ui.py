import time
import numpy as np
from touchmusic import ui
from touchmusic.library import VoiceLibrary
from touchmusic.isolated_rack import IsolatedPluginRack


def test_gesture_learn_records_mapping_without_emitting_performance_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    window = ui.MainWindow()
    try:
        window.engine.rack.slots = [{'path': 'test.vst3', 'plugin_name': '',
                                     'parameters': {'gain': .5}, 'bypass': False}]
        window.plugin_dialog.refresh()
        window.camera = object()
        window.plugin_dialog.learn()
        assert not window.arm.isChecked()
        first = {'hand': 'Right', 'x': .5, 'y': .5, 'span': .5, 'pose': 0}
        window.gestures([first])
        window.gestures([{**first, 'y': .8}])
        assert window.mappings['Right'].currentText() == 'Plugin knob 1'
        assert window.engine.rack.bindings['1'] == {'slot': 0, 'parameter': 'gain'}
        assert not window.engine.loop.recording
        assert window.engine.rack.slots[0]['parameters']['gain'] == .5
        assert window.plugin_dialog.learner is None
    finally:
        window.camera = None
        window.close()


def test_motion_score_and_search_folders_survive_restart_without_autoplay(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    first = ui.MainWindow()
    first.settings['plugin_folders'] = [str(tmp_path/'plugins')]
    score = {'version': 1, 'events': [{'beat': 0, 'kind': 'level', 'target': 'Reverb', 'value': .8}]}
    first.motion_dialog.checked_load(score)
    first.close()
    second = ui.MainWindow()
    try:
        assert second.settings['plugin_folders'] == [str(tmp_path/'plugins')]
        assert second.motion_dialog.score.settings() == score
        assert second.motion_dialog.score.mode == 'Stopped'
        assert not second.engine.stream
        assert not second.arm.isChecked()
    finally:
        second.close()


def test_motion_score_edits_and_emergency_stop(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    window = ui.MainWindow()
    try:
        score = {'version': 1, 'events': [{'beat': 0, 'kind': 'level', 'target': 'Reverb', 'value': .8}]}
        dialog = window.motion_dialog
        dialog.checked_load(score)
        dialog.table.item(0, 3).setText('.6')
        dialog.apply_edits()
        assert dialog.score.events[0]['value'] == .6
        dialog.table.item(0, 2).setText('Unknown target')
        dialog.apply_edits()
        assert dialog.score.events[0]['target'] == 'Reverb'
        dialog.score.start('Recording', 0)
        window.emergency_mute()
        assert dialog.score.mode == 'Stopped' and window.engine.muted
    finally:
        window.close()


def test_native_editor_broker_updates_parameters_and_clears_busy_flag():
    class EditorClient:
        def request(self, action, **kwargs):
            assert action == 'editor' and kwargs == {'timeout': None, 'index': 0}
            assert rack.editor_open
            return {'effects': [{'path': 'test.vst3', 'parameters': {'gain': .7}}]}
    rack = IsolatedPluginRack()
    rack.client = EditorClient()
    rack.show_editor(0)
    assert not rack.editor_open
    assert rack.slots[0]['parameters']['gain'] == .7


def test_timed_wet_results_preserve_stereo_and_never_shift_later_blocks():
    rack = IsolatedPluginRack()
    rack.slots = [{'parameters': {}, 'bypass': False}]
    rack.error = 'offline fixture'
    source = np.ones(512, np.float32)
    assert not rack.process(source, 48000, stereo=True).any()
    first = rack.entries[0]
    first['wet'] = np.stack((source*.2, source*.7))
    for _ in range(3):
        assert not rack.process(source*2, 48000, stereo=True).any()
    wet = rack.process(source*3, 48000, stereo=True)
    np.testing.assert_allclose(wet[0], .2)
    np.testing.assert_allclose(wet[1], .7)
    # A result that arrived after its playback deadline cannot be heard on a later block.
    first['wet'] = np.stack((source*99, source*99))
    dry = rack.process(source*4, 48000, stereo=True)
    np.testing.assert_array_equal(dry, 2)
