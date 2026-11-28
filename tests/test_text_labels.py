from copy import deepcopy
import json
from touchmusic.text_labels import LEGACY_SCENE_PREFIXES, SCENE_PREFIX, saved_labels, score_labels
from touchmusic import ui
from touchmusic.library import VoiceLibrary


def test_legacy_scene_mappings_macros_and_scores_migrate_without_changing_user_text():
    name = 'Beyonc\u00e9 / \u5929'
    for prefix in LEGACY_SCENE_PREFIXES:
        settings = {'voice': name, 'mapping': {'Left_1': prefix+name},
                    'macros': {'Macro 1': [prefix+name, 'Loop']},
                    'motion_score': {'version': 1, 'events': [{'beat': 0, 'kind': 'action', 'target': prefix+name}]},
                    'presets': {name: {'mapping': {'Right_1': prefix+name}}}}
        original = deepcopy(settings)
        fixed = saved_labels(settings)
        assert fixed['voice'] == name and name in fixed['presets']
        assert fixed['mapping']['Left_1'] == SCENE_PREFIX+name
        assert fixed['macros']['Macro 1'] == [SCENE_PREFIX+name, 'Loop']
        assert fixed['motion_score']['events'][0]['target'] == SCENE_PREFIX+name
        assert fixed['presets'][name]['mapping']['Right_1'] == SCENE_PREFIX+name
        assert settings == original
        assert saved_labels(fixed) == fixed


def test_score_label_migration_preserves_unknown_targets_for_validation():
    settings = {'version': 1, 'events': [{'kind': 'action', 'target': 'Unknown action'},
                                        {'kind': 'level', 'target': 'Master level', 'value': .5}]}
    assert score_labels(settings) == settings


def test_voice_loop_and_menu_labels_are_readable_and_keep_unicode_names(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    library = VoiceLibrary(tmp_path/'voices')
    library.voices = [{'id': 'sample', 'name': 'Beyonc\u00e9 / \u5929', 'seconds': 8.0, 'file': 'local.wav'}]
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: library)
    legacy = LEGACY_SCENE_PREFIXES[0]+'Duet'
    (tmp_path/'settings.json').write_text(json.dumps({
        'presets': {'Duet': {}}, 'mapping': {'Left_1': legacy},
        'macros': {'Macro 1': [legacy]},
        'motion_score': {'version': 1, 'events': [{'beat': 0, 'kind': 'action', 'target': legacy}]}}),
        encoding='utf-8')
    window = ui.MainWindow()
    try:
        assert window.mappings['Left_1'].currentText() == SCENE_PREFIX+'Duet'
        assert window.macro_bank.settings()['Macro 1'] == [SCENE_PREFIX+'Duet']
        assert window.motion_dialog.score.events[0]['target'] == SCENE_PREFIX+'Duet'
        assert window.voice_combo.itemText(0) == 'Beyonc\u00e9 / \u5929  |  8.0 s'
        window.tick()
        assert window.loop_pads[0].text() == 'Loop 1  |  Empty'
        assert any(action.text() == 'Open skit...' for action in window.session_menu.actions())
        from PySide6.QtWidgets import QLabel, QPushButton
        for widget in window.findChildren(QLabel)+window.findChildren(QPushButton):
            assert '\u00c3\u0192' not in widget.text() and '\ufffd' not in widget.text()
    finally:
        window.close()
