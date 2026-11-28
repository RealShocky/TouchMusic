import numpy as np
from touchmusic import ui
from touchmusic.audio import AudioEngine, RATE, Recorder
from touchmusic.library import VoiceLibrary


def test_tone_is_monitoring_only_and_obeys_emergency_mute(tmp_path):
    engine = AudioEngine()
    engine.params['dialogue'] = True
    engine.recorder = Recorder(tmp_path / 'mix.wav')
    engine.commands.put(('loop', 0))
    engine.play_test_tone()
    output = engine.process(np.zeros(RATE, np.float32))
    assert output.max() > .03
    engine.commands.put(('loop', 0))
    engine.process(np.zeros(512, np.float32))
    assert not engine.loop.clip.any()
    engine.stop_recording()
    import soundfile as sf
    assert not sf.read(tmp_path / 'mix.wav')[0].any()
    engine.play_test_tone()
    engine.muted = True
    assert not engine.process(np.zeros(512, np.float32)).any()


def test_new_gesture_targets_stage_and_precision_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    window = ui.MainWindow()
    try:
        window.gesture_level('Tempo', 1)
        assert window.engine.params['bpm'] == 240
        window.gesture_level('Capture length', .5)
        assert window.engine.params['capture_bars'] == 2
        window.gesture_level('Overdub feedback', .72)
        assert window.engine.params['overdub_feedback'] == .72
        window.gesture_action('Toggle overdub mode')
        assert window.engine.params['loop_mode'] == 'Overdub'
        window.gesture_action('Next count-in')
        assert window.engine.params['count_in'] == 1
        window.arm.setChecked(True)
        window.emergency_mute()
        assert window.engine.muted and not window.arm.isChecked()
        window.open_stage()
        window.tick()
        assert '240 BPM' in window.stage_view.music.text()
        window.precision_controls['deadband'].setValue(5)
        window.precision.ranges = {'Right': [.2, .8]}
        saved = window.performance_settings()
        window.precision.ranges = {}
        window.apply_performance(saved)
        assert window.precision.ranges == {'Right': [.2, .8]}
        assert window.precision.deadband == .05
    finally:
        window.close()


def test_calibration_disarms_and_collects_without_changing_effects(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: VoiceLibrary(tmp_path / 'voices'))
    window = ui.MainWindow()
    try:
        window.camera = type('Camera', (), {})()
        window.arm.setChecked(True)
        before = window.engine.params['harmony']
        window.start_calibration()
        assert not window.arm.isChecked()
        for position in np.linspace(.2, .8, 30):
            window.gestures([dict(hand='Left', x=position, y=position, span=position, pose=0, fingers=0)])
        assert window.engine.commands.empty()
        assert window.engine.params['harmony'] == before
        window.calibrating_until = 1
        window.calibration_tick()
        assert len(window.precision.ranges) == 3
        window.precision_dialog.freeze.setChecked(True)
        window.precise_level('Left', .8)
        assert window.engine.params['harmony'] == before
    finally:
        window.camera = None
        window.close()
