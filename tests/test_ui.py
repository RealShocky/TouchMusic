import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from touchmusic.ui import MainWindow


def test_audio_picker_pairs_devices_from_the_same_backend(monkeypatch, tmp_path):
    from touchmusic import ui
    from touchmusic.library import VoiceLibrary
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    devices = [
        dict(name='Mic', hostapi=0, max_input_channels=1, max_output_channels=0),
        dict(name='Headphones', hostapi=0, max_input_channels=0, max_output_channels=2),
        dict(name='Mic', hostapi=1, max_input_channels=1, max_output_channels=0),
        dict(name='Headphones', hostapi=1, max_input_channels=0, max_output_channels=2),
    ]
    apis = [
        dict(name='MME', default_input_device=0, default_output_device=1),
        dict(name='Windows WASAPI', default_input_device=2, default_output_device=3),
    ]
    monkeypatch.setattr(ui.sd, 'query_devices', lambda: devices)
    monkeypatch.setattr(ui.sd, 'query_hostapis', lambda: apis)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert window.inputs.currentData() == 2
        assert window.outputs.count() == 1 and window.outputs.currentData() == 3
        window.inputs.setCurrentIndex(window.inputs.findData(0))
        assert window.outputs.count() == 1 and window.outputs.currentData() == 1
    finally:
        window.close()


def test_native_window_presets_and_controls(tmp_path, monkeypatch):
    from touchmusic import ui
    from touchmusic.library import VoiceLibrary
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.preset_combo.setCurrentText('Machine')
    assert window.engine.params['pitch'] == -3
    assert window.engine.params['robot'] == .65
    window.apply_tune_preset(55, 30)
    assert window.tune_button.isChecked()
    window.tune_button.click()
    assert window.engine.params['tune'] == 0
    window.gesture_action('Toggle Auto-Tune')
    assert window.engine.params['tune'] == .55
    window.music_controls['bpm'].setValue(95)
    window.music_controls['quantize'].setCurrentText('Next bar')
    assert window.performance_settings()['music']['bpm'] == 95
    assert window.engine.params['quantize'] == 'Next bar'
    from touchmusic.midi import MidiOutput
    from test_midi import Port
    port = Port()
    window.midi = MidiOutput(lambda: port)
    window.midi_dialog.output = window.midi
    window.midi.connect('TouchMusic test')
    window.rehearse.setChecked(True)
    window.gesture_action('MIDI note C4')
    assert not any(message[0] == 0x90 for message in port.messages)
    window.rehearse.setChecked(False)
    window.gesture_action('MIDI note C4')
    assert [0x90, 60, 100] in port.messages
    window.mute_button.click()
    assert window.engine.muted
    window.mute_button.click()
    assert not window.engine.muted
    assert not window.engine.stream
    assert not window.ai.isEnabled()
    window.show()
    app.processEvents()
    assert not window.grab().isNull()
    window.close()


def test_two_finger_pose_switches_to_the_assigned_reference(tmp_path, monkeypatch):
    from touchmusic import ui
    from touchmusic.library import VoiceLibrary
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    library = VoiceLibrary(tmp_path / 'voices')
    library.voices = [{'id': 'first', 'name': 'Performer', 'seconds': 2},
                      {'id': 'second', 'name': 'Villain', 'seconds': 2}]
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: library)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        control = dict(hand='Right', fingers=2, pose=2, pinch=False, x=.5, y=.5)
        window.gestures([control])
        assert window.voice_combo.currentData() == 'first'
        window.arm.setChecked(True)
        window.gestures([control])
        assert window.voice_combo.currentData() == 'second'
        window.mappings['Left_2'].setCurrentText('Intercom')
        window.gestures([{**control, 'hand': 'Left'}])
        assert window.engine.params['radio'] == .95
        window.save_settings()
        assert window.settings['voice_slots']['Voice 2'] == 'second'
        assert window.settings['mapping']['Left_2'] == 'Intercom'
    finally:
        window.close()


def test_fist_loop_works_with_unassigned_pinch_and_no_double_toggle(tmp_path, monkeypatch):
    from touchmusic import ui
    from touchmusic.library import VoiceLibrary
    import numpy as np

    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        event = dict(hand='Left', fingers=0, pose=0, pinch=False, held=True, x=.5, y=.5)
        window.mappings['Left_0'].setCurrentText('Loop')
        window.arm.setChecked(True)
        window.gestures([event])
        assert window.engine.commands.empty()
        assert 'Start audio' in window.notice.text()
        window.engine.stream = object()
        window.gestures([event])
        window.engine.process(np.ones(512, dtype=np.float32))
        assert window.engine.loop.recording
        window.mappings['left_pinch'].setCurrentText('Loop')
        window.gestures([{**event, 'pose': None, 'pinch': True}])
        window.gestures([event])
        window.engine.process(np.ones(512, dtype=np.float32))
        assert not window.engine.loop.recording
    finally:
        window.engine.stream = None
        window.close()


def test_skit_roundtrip_and_chord_rehearsal(tmp_path, monkeypatch):
    from touchmusic import ui
    from touchmusic.library import VoiceLibrary
    import numpy as np
    import soundfile as sf

    monkeypatch.setattr(ui, 'DATA', tmp_path)
    library = VoiceLibrary(tmp_path / 'voices')
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: library)
    reference = tmp_path / 'reference.wav'
    sf.write(reference, np.full(24000, .12, np.float32), 24000)
    voice = library.import_file(reference, 'Character')
    path = tmp_path / 'skit.touchmusic'
    monkeypatch.setattr(ui.QFileDialog, 'getSaveFileName', lambda *args: (str(path), ''))
    monkeypatch.setattr(ui.QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window.map_left_chords()
        event = dict(hand='Left', x=.5, y=.5, fingers=2, pose=2)
        window.rehearse.setChecked(True)
        window.gestures([event])
        assert 'would trigger Chord II' in window.gesture_preview.text()
        assert window.engine.params['chord'] == 0
        window.rehearse.setChecked(False)
        window.arm.setChecked(True)
        window.gestures([event])
        assert window.engine.params['chord'] == 1
        window.sliders['tune'].setValue(75)
        clip = np.full(512, .15, np.float32)
        window.engine.loops[1].load(clip)
        window.engine.loops[1].muted = True
        window.engine.track.load(clip * 2)
        window.save_skit()
        assert path.is_file(), window.notice.text()
        assert sf.info(library.path(voice)).samplerate == 24000
        library.path(voice).unlink()
        window.sliders['tune'].setValue(0)
        window.engine.loops[1].clear()
        window.engine.track.load([])
        window.open_skit()
        assert library.path(voice).is_file()
        assert window.voice_combo.currentData() == voice['id']
        assert window.sliders['tune'].value() == 75
        assert window.mappings['Left_2'].currentText() == 'Chord II'
        assert window.engine.loops[1].muted
        np.testing.assert_array_equal(window.engine.loops[1].clip, clip)
        np.testing.assert_array_equal(window.engine.track.audio, clip * 2)
    finally:
        window.close()
