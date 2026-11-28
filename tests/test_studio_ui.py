import numpy as np
from touchmusic import ui
from touchmusic.library import VoiceLibrary
from touchmusic.diagnostics import diagnostics_report
from touchmusic.audio import AudioEngine


def test_workspaces_macro_dispatch_and_saved_plugin_review(tmp_path, monkeypatch, qt_application):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    window = ui.MainWindow()
    try:
        window.show()
        for name in window.workspaces.names:
            window.workspaces.open(name)
            qt_application.processEvents()
        assert window.audio_setup.owner is window
        assert window.setlist_dialog.owner is window
        window.macro_bank.set('Macro 1', ['Toggle overdub mode', 'Next capture length', 'Chord III'])
        window.gesture_action('Macro 1')
        assert window.engine.params['loop_mode'] == 'Overdub'
        assert window.engine.params['capture_bars'] == 1
        assert window.engine.params['chord'] == 2
        config = {'effects': [{'path': str(tmp_path/'external.vst3'), 'parameters': {}}]}
        window.apply_performance({'plugins': config})
        assert not window.engine.rack.slots
        assert window.plugin_dialog.pending == config
        assert window.performance_settings()['plugins'] == config
        window.save_settings()
        assert window.settings['macros']['Macro 1'][0] == 'Toggle overdub mode'
    finally:
        window.close()


def test_audio_setup_profiles_do_not_silently_replace_missing_devices(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    devices = [dict(name='Mic', hostapi=0, max_input_channels=1, max_output_channels=0),
               dict(name='Headphones', hostapi=0, max_input_channels=0, max_output_channels=2)]
    monkeypatch.setattr(ui.sd, 'query_devices', lambda: devices)
    monkeypatch.setattr(ui.sd, 'query_hostapis', lambda: [dict(name='Windows WASAPI', default_input_device=0, default_output_device=1)])
    window = ui.MainWindow()
    try:
        window.routing_profiles['Missing'] = {'input': 'Disconnected mic', 'output': 'Missing output'}
        wizard = window.audio_setup
        wizard.refresh_devices()
        assert wizard.outputs.currentData() == 1
        wizard.profiles.setCurrentText('Missing')
        wizard.load_profile()
        assert 'unavailable' in wizard.status.text()
        assert not window.engine.stream
        window.save_settings()
        assert window.settings['routing_profiles']['Missing']['input'] == 'Disconnected mic'
    finally:
        window.close()


def test_diagnostics_observe_audio_clipping_and_callback_cost():
    engine = AudioEngine()
    inputs = np.ones((512, 1), np.float32)
    outputs = np.zeros((512, 2), np.float32)
    engine._callback(inputs, outputs, 512, None, True)
    report = diagnostics_report(engine)
    assert report['input_near_full_scale_samples'] == 512
    assert report['audio_status_events'] == 1
    assert report['max_callback_ms'] > 0
    assert not report['audio_error']


def test_saved_rack_survives_restart_as_pending_without_native_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path/'voices'))
    config = {'effects': [{'path': str(tmp_path/'installed.vst3'), 'parameters': {}}]}
    first = ui.MainWindow()
    first.apply_performance({'plugins': config})
    first.close()
    second = ui.MainWindow()
    try:
        assert second.plugin_dialog.pending == config
        assert not second.engine.rack.slots
        assert second.performance_settings()['plugins'] == config
    finally:
        second.close()
