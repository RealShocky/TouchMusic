"""Native desktop controls for TouchMusic."""
import json
import time
from datetime import datetime
from pathlib import Path
from statistics import median
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFileDialog, QMessageBox, QInputDialog,
    QProgressBar, QCheckBox, QGroupBox, QGridLayout, QSpinBox, QDialog, QScrollArea, QTabWidget, QSizePolicy, QMenu)
from .audio import AudioEngine, LOOP_COUNT, RATE
from .library import VoiceLibrary, DATA, save_json, read_audio
from .camera import CameraWorker
from .neural import StreamingConverter
from .music import DEGREES, NOTES, SCALES, chord_name, chord_notes
from .project import load_project, save_project
from .transport import BEATS_PER_BAR, QUANTIZE
from .vocal import HARMONY_MODES, VOCAL_RANGES
from .reference_picker import ReferencePicker
from .midi import MidiOutput, MIDI_ACTIONS, MIDI_CHORDS, MIDI_LEVELS, MIDI_NOTES
from .midi_dialog import MidiDialog
from .sessions import SessionRecovery
from .setlist_dialog import SetlistDialog

EFFECT_TARGETS = ['None', 'Reverb', 'Delay', 'Harmony', 'Robot', 'Pitch', 'Gain',
                  'Chorus', 'Drive', 'Radio', 'Octave', 'Tremolo', 'Warmth',
                  'Brightness', 'Gate', 'Feedback', 'Delay time', 'AI mix',
                  'Track level', 'Master level', 'Tune strength', 'Retune speed', 'Chord level',
                  'Formant', 'Vibrato',
                  *(f'Loop {i} level' for i in range(1, LOOP_COUNT + 1)), *MIDI_LEVELS]
VOICE_SLOTS = [f'Voice {number}' for number in range(1, 6)]
BUILTIN_PRESETS = {
    'Clean': {}, 'Space': {'reverb': 65, 'delay': 35},
    'Choir': {'reverb': 35, 'harmony': 70, 'chorus': 30},
    'Machine': {'pitch': -3, 'reverb': 12, 'delay': 8, 'robot': 65},
    'Intercom': {'radio': 95, 'drive': 22},
    'Villain': {'pitch': -5, 'octave': 48, 'drive': 12, 'reverb': 20},
    'Ghost': {'chorus': 50, 'tremolo': 50, 'reverb': 55, 'delay': 15},
}
LOOP_ACTIONS = {
    f'{label} {i+1}': (command, i)
    for i in range(LOOP_COUNT)
    for label, command in [('Capture loop', 'loop'), ('Overdub loop', 'overdub'), ('Mute loop', 'mute'),
                           ('Restart loop', 'restart'), ('Undo loop', 'undo'), ('Redo loop', 'redo')]
}
CHORD_ACTIONS = [f'Chord {degree}' for degree in DEGREES]
TUNE_PRESETS = {'Natural': (55, 30), 'Tight': (80, 60), 'Hard': (100, 100)}
ACTIONS = ['None', *VOICE_SLOTS, 'Next voice', 'Previous voice', 'Loop', *LOOP_ACTIONS,
           'Next loop', 'Previous loop', 'Mute output', 'AI conversion', 'Dialogue mode',
           'Play / pause track', 'Restart track', 'Record performance', *BUILTIN_PRESETS,
           *CHORD_ACTIONS, 'Next chord', 'Previous chord', 'Toggle chords', 'Toggle Auto-Tune',
           'Toggle dry monitoring', 'Undo selected loop', 'Redo selected loop', 'Overdub selected loop',
           'Next song', 'Previous song', 'Toggle metronome', 'Tap tempo', *MIDI_ACTIONS]
EFFECT_DEFAULTS = {'gain': 70, 'aimix': 100, 'delaytime': 300, 'feedback': 29}
TARGET_KEYS = {'AI mix': 'aimix', 'Delay time': 'delaytime', 'Master level': 'master',
               'Tune strength': 'tune', 'Retune speed': 'retune', 'Chord level': 'chord_level'}
SCENE_PREFIX = 'Scene · '

STYLE = '''
QMainWindow, QWidget { background: #14191c; color: #f3f1e9; font-family: 'Segoe UI'; font-size: 13px; }
QGroupBox { background: #1b2226; border: 1px solid #394448; border-radius: 8px; margin-top: 12px; padding: 8px 10px 6px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 5px; }
QLabel { background: transparent; }
QPushButton { background: #293337; border: 1px solid #435158; border-radius: 5px; padding: 4px 10px; }
QPushButton:hover { background: #39484e; }
QPushButton:checked { background: #1d4d44; border-color: #77d5b8; }
QPushButton#startAudio { background: #8fe1c4; color: #0b221a; border-color: #a3e8d1; font-weight: 700; }
QPushButton[loopState="recording"] { background: #722d38; border-color: #f391a1; }
QPushButton[loopState="playing"] { background: #21483f; border-color: #67c8a6; }
QPushButton[loopState="queued"] { background: #594624; border-color: #e3b871; }
QPushButton:disabled { color: #78828e; background: #2d343e; }
QComboBox, QSpinBox { background: #101619; border: 1px solid #435158; padding: 5px; border-radius: 5px; }
QComboBox QAbstractItemView { background: #20252d; selection-background-color: #366c7b; }
QSlider::groove:horizontal { background: #151b22; height: 7px; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #81d7b7; border-radius: 3px; }
QSlider::handle:horizontal { background: #e4edf0; border: 1px solid #fff; width: 15px; margin: -5px 0; border-radius: 7px; }
QProgressBar { border: 0; background: #131a20; border-radius: 4px; height: 7px; }
QProgressBar::chunk { background: #81d7b7; border-radius: 4px; }
QCheckBox { background: transparent; padding: 3px 0; }
QCheckBox::indicator { width: 12px; height: 12px; background: #101619; border: 1px solid #637771; border-radius: 3px; }
QCheckBox::indicator:checked { background: #81d7b7; border-color: #a3e8d1; }
QCheckBox::indicator:disabled { border-color: #414a4b; }
QLabel#performanceStatus { background: #202b2b; border: 1px solid #384b46; padding: 6px 10px; color: #bfe4d8; }
QTabWidget::pane { border: 1px solid #394448; }
QTabBar::tab { padding: 6px 14px; background: #1b2226; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { border-bottom-color: #81d7b7; color: #c3f1e2; }
'''


class PitchMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.cents = None
        self.setFixedHeight(18)
        self.setAccessibleName('Detected pitch deviation in cents')

    def set_cents(self, cents):
        if cents != self.cents:
            self.cents = cents
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#101619'))
        painter.drawRoundedRect(0, 4, self.width(), 10, 4, 4)
        painter.setPen(QColor('#84948e'))
        center = self.width() // 2
        painter.drawLine(center, 2, center, 16)
        if self.cents is not None:
            x = center + (center - 8) * max(-1., min(1., self.cents / 100))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#81d7b7' if abs(self.cents) <= 15 else '#e3b871'))
            painter.drawEllipse(round(x) - 4, 5, 8, 8)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('TouchMusic • Standalone')
        self.resize(1280, 880)
        self.setStyleSheet(STYLE)
        DATA.mkdir(parents=True, exist_ok=True)
        self.library = VoiceLibrary()
        self.engine = AudioEngine()
        self.midi = MidiOutput()
        self.camera = None
        self.closing = False
        self.last_pinch = {}
        self.ai_requested = False
        self.music_controls = {}
        self.last_tune = 80
        self.tempo_taps = []
        self.pending_exports = []
        self.sliders = {}
        self.gesture_selectors = []
        self.voices = []
        self.settings_path = DATA / 'settings.json'
        self.settings = {}
        if self.settings_path.exists():
            try:
                self.settings = json.loads(self.settings_path.read_text('utf-8'))
            except (ValueError, OSError):
                pass
        self.saved_presets = self.settings.get('presets', {})
        self.recovery = SessionRecovery(DATA / 'recovery')
        self.recovery_pending = self.recovery.recovery_available
        self.recovery_fingerprint = None
        self.recovery_changed_at = time.monotonic()
        self.last_recovery_check = 0.
        root = QWidget()
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QScrollArea.NoFrame)
        page.setWidget(root)
        self.setCentralWidget(page)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(4)
        header = QHBoxLayout()
        title = QLabel('TouchMusic')
        title.setStyleSheet('font-size: 31px; font-weight: 650;')
        header.addWidget(title)
        header.addStretch()
        session_button = QPushButton('Session')
        self.session_menu = QMenu(self)
        self.session_menu.addAction('Open skit…', self.open_skit)
        self.session_menu.addAction('Save skit…', self.save_skit)
        self.session_menu.addAction('Setlist…', self.open_setlist)
        self.session_menu.addSeparator()
        self.session_menu.addAction('Save recovery now', lambda: self.backup_session(force=True))
        self.recover_action = self.session_menu.addAction('Recover last session', self.restore_recovery)
        self.session_menu.aboutToShow.connect(lambda: self.recover_action.setEnabled(self.recovery.archive_path.exists()))
        session_button.setMenu(self.session_menu)
        header.addWidget(session_button)
        self.button('Music tools', self.open_music_tools, header)
        self.button('MIDI / FL', self.open_midi_dialog, header)
        self.audio_button = self.button('Start audio', self.toggle_audio, header)
        self.audio_button.setObjectName('startAudio')
        self.mute_button = self.button('Mute output', self.toggle_mute, header, True)
        layout.addLayout(header)
        self.music_status = QLabel()
        self.music_status.setObjectName('performanceStatus')
        self.music_status.setWordWrap(True)
        layout.addWidget(self.music_status)
        self.notice = QLabel('Choose your microphone and output, then start audio. Use headphones for live monitoring.')
        self.notice.setWordWrap(True)
        notices = QHBoxLayout()
        notices.addWidget(self.notice, 1)
        self.recover_button = self.button('Recover session', self.restore_recovery, notices)
        self.keep_button = self.button('Use current session', self.use_current_session, notices)
        self.recover_button.setVisible(self.recovery_pending)
        self.keep_button.setVisible(self.recovery_pending)
        layout.addLayout(notices)
        devices = QHBoxLayout()
        self.inputs, self.outputs = QComboBox(), QComboBox()
        for combo in (self.inputs, self.outputs):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(18)
        self.inputs.currentIndexChanged.connect(self.refresh_outputs)
        devices.addWidget(QLabel('Microphone'))
        devices.addWidget(self.inputs, 1)
        devices.addWidget(QLabel('Output'))
        devices.addWidget(self.outputs, 1)
        self.button('Refresh', self.refresh_devices, devices)
        layout.addLayout(devices)
        body = QHBoxLayout()
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(4)
        right.setSpacing(4)
        body.addLayout(left, 3)
        body.addLayout(right, 2)
        layout.addLayout(body, 1)
        self.camera_label = QLabel('Your performance space\n\nStart camera to see hand tracking')
        self.camera_label.setMinimumSize(420, 220)
        self.camera_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet('background: #141b24; border: 1px solid #465363; border-radius: 12px; font-size: 18px; color: #b7c6d4;')
        left.addWidget(self.camera_label, 1)
        camera_row = QHBoxLayout()
        self.camera_button = self.button('Start camera', self.toggle_camera, camera_row)
        camera_row.addWidget(QLabel('Camera'))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 8)
        self.camera_index.setFixedWidth(60)
        camera_row.addWidget(self.camera_index)
        self.arm = QCheckBox('Arm gestures')
        self.arm.toggled.connect(lambda armed: self.midi.panic() if not armed else None)
        camera_row.addWidget(self.arm)
        self.rehearse = QCheckBox('Rehearse gestures')
        camera_row.addWidget(self.rehearse)
        self.button('Gesture mapping', self.open_gesture_dialog, camera_row)
        left.addLayout(camera_row)
        self.tracking = QLabel('Camera off')
        left.addWidget(self.tracking)
        self.gesture_preview = QLabel()
        self.gesture_preview.setWordWrap(True)
        self.rehearse.toggled.connect(self.toggle_rehearsal)
        left.addWidget(self.gesture_preview)
        mapping_box = QGroupBox('Quick mappings')
        mapping = QGridLayout(mapping_box)
        self.mappings = {}
        for row, (key, label, default) in enumerate([
            ('Right', 'Right hand height', 'Reverb'), ('Left', 'Left hand height', 'Harmony'),
            ('pinch', 'Right thumb + index pinch', 'Next voice')]):
            combo = self.mapping_combo(key, ACTIONS if key == 'pinch' else EFFECT_TARGETS, default)
            mapping.addWidget(QLabel(label), row, 0)
            mapping.addWidget(combo, row, 1)
        self.build_gesture_dialog()
        self.gesture_dialog.layout().insertWidget(1, mapping_box)
        voice_box = QGroupBox('Character voice')
        voice_layout = QVBoxLayout(voice_box)
        voice_layout.setSpacing(4)
        self.voice_combo = QComboBox()
        self.voice_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.voice_combo.setMinimumContentsLength(16)
        self.voice_combo.currentIndexChanged.connect(self.select_voice)
        voice_layout.addWidget(self.voice_combo)
        voice_row = QHBoxLayout()
        self.button('Import audio', self.import_voice, voice_row)
        self.button('Preview', self.preview_voice, voice_row)
        self.button('Rename', self.rename_voice, voice_row)
        voice_layout.addLayout(voice_row)
        self.model_button = self.button('Load singing engine', self.load_model, voice_layout)
        self.ai = QCheckBox('Use AI character conversion')
        self.ai.setEnabled(False)
        self.ai.toggled.connect(self.toggle_ai)
        voice_layout.addWidget(self.ai)
        self.dialogue = QCheckBox('Dialogue mode')
        self.dialogue.setToolTip('Bypass pitch correction and vocal effects for dialogue.')
        self.dialogue.toggled.connect(self.toggle_dialogue)
        self.dialogue.setChecked(bool(self.settings.get('dialogue', False)))
        voice_layout.removeWidget(self.ai)
        voice_options = QHBoxLayout()
        voice_options.addWidget(self.ai)
        voice_options.addWidget(self.dialogue)
        voice_layout.addLayout(voice_options)
        self.model_status = QLabel('Effects ready. Singing engine has not been loaded.')
        self.model_status.setWordWrap(True)
        voice_layout.addWidget(self.model_status)
        right.addWidget(voice_box)
        tuning_row = QHBoxLayout()
        self.tune_button = self.button('Auto-Tune Off', self.toggle_tune, tuning_row, True)
        for label, values in TUNE_PRESETS.items():
            self.button(label, lambda _, v=values: self.apply_tune_preset(*v), tuning_row)
        right.addLayout(tuning_row)
        vocal_tabs = QTabWidget()
        vocal_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        vocal_tabs.setMinimumHeight(180)
        pitch_box = QWidget()
        pitch_layout = QVBoxLayout(pitch_box)
        self.pitch_status = QLabel('Auto-Tune off')
        pitch_layout.addWidget(self.pitch_status)
        self.pitch_meter = PitchMeter()
        pitch_layout.addWidget(self.pitch_meter)
        vocal_tabs.addTab(pitch_box, 'Pitch correction')
        effects = QWidget()
        effects_layout = QVBoxLayout(effects)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([*BUILTIN_PRESETS, 'Custom'])
        self.preset_combo.addItems(list(self.saved_presets))
        self.preset_combo.setCurrentText('Custom')
        self.preset_combo.currentTextChanged.connect(self.preset)
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.preset_combo, 1)
        self.button('Save preset', self.save_preset, preset_row)
        effects_layout.addLayout(preset_row)
        effects_scroll = QScrollArea()
        effects_scroll.setWidgetResizable(True)
        effects_scroll.setMinimumHeight(90)
        sliders_panel = QWidget()
        sliders_layout = QVBoxLayout(sliders_panel)
        sliders_layout.setContentsMargins(0, 0, 8, 0)
        for key, label, minimum, maximum, initial in [
            ('pitch', 'Pitch', -12, 12, 0), ('reverb', 'Reverb', 0, 100, 0),
            ('delay', 'Delay', 0, 100, 0), ('harmony', 'Harmony', 0, 100, 0),
            ('robot', 'Robot', 0, 100, 0), ('chorus', 'Chorus', 0, 100, 0),
            ('drive', 'Drive', 0, 100, 0), ('radio', 'Radio', 0, 100, 0),
            ('octave', 'Low octave', 0, 100, 0), ('tremolo', 'Tremolo', 0, 100, 0),
            ('warmth', 'Warmth', -100, 100, 0), ('brightness', 'Brightness', -100, 100, 0),
            ('gate', 'Noise gate', 0, 100, 0), ('feedback', 'Delay feedback', 0, 100, 29),
            ('delaytime', 'Delay time', 50, 1000, 300), ('aimix', 'AI mix', 0, 100, 100),
            ('gain', 'Vocal level', 0, 100, 70), ('master', 'Master level', 0, 100, 100)]:
            row = QHBoxLayout()
            text = QLabel(label)
            text.setMinimumWidth(75)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(minimum, maximum)
            value = QLabel()
            value.setMinimumWidth(40)
            self.sliders[key] = slider
            slider.valueChanged.connect(lambda v, k=key, out=value: self.parameter(k, v, out))
            slider.setValue(int(self.settings.get('effects', {}).get(key, initial)))
            self.parameter(key, slider.value(), value)
            row.addWidget(text)
            row.addWidget(slider, 1)
            row.addWidget(value)
            sliders_layout.addLayout(row)
        effects_scroll.setWidget(sliders_panel)
        effects_layout.addWidget(effects_scroll, 1)
        vocal_tabs.addTab(effects, 'Vocal effects')
        right.addWidget(vocal_tabs, 1)
        transport = QGroupBox('Looper and transport')
        transport_layout = QVBoxLayout(transport)
        transport_layout.setSpacing(4)
        self.build_transport(transport_layout)
        track_row = QHBoxLayout()
        self.button('Open track', self.open_track, track_row)
        self.play_button = self.button('Play / pause', self.play_track, track_row)
        self.button('Restart', self.engine.track.restart, track_row)
        self.track_label = QLabel('No backing track loaded')
        track_row.addWidget(self.track_label, 1)
        track_row.addWidget(QLabel('Track level'))
        self.track_volume = QSlider(Qt.Horizontal)
        self.track_volume.setRange(0, 100)
        self.track_volume.valueChanged.connect(lambda v: setattr(self.engine.track, 'gain', v / 100))
        self.track_volume.setValue(self.settings.get('track_level', 60))
        track_row.addWidget(self.track_volume)
        transport_layout.addLayout(track_row)
        row = QHBoxLayout()
        self.loop_select = QComboBox()
        self.loop_select.addItems([f'Loop {i}' for i in range(1, LOOP_COUNT + 1)])
        row.addWidget(self.loop_select)
        self.button('Restart loop', lambda: self.loop_command('restart'), row)
        self.button('Export loop', self.export_loop, row)
        self.button('Clear loop', lambda: self.loop_command('clear'), row)
        self.undo_button = self.button('Undo', lambda: self.loop_command('undo'), row)
        self.redo_button = self.button('Redo', lambda: self.loop_command('redo'), row)
        self.record_button = self.button('Record performance', self.toggle_recording, row)
        for track, level in zip(self.engine.loops, self.settings.get('loop_levels', [])):
            track.gain = max(0, min(100, level)) / 100
        self.loop_select.currentIndexChanged.connect(self.sync_loop_level)
        self.sync_loop_level()
        transport_layout.addLayout(row)
        layout.addWidget(transport)
        meters = QHBoxLayout()
        self.input_meter, self.output_meter = QProgressBar(), QProgressBar()
        for label, meter in [('Input', self.input_meter), ('Output', self.output_meter)]:
            meter.setTextVisible(False)
            meters.addWidget(QLabel(label))
            meters.addWidget(meter)
        layout.addLayout(meters)
        self.build_music_tools(pitch_layout)
        pitch_layout.addStretch()
        self.midi_dialog = MidiDialog(self.midi, self.settings.get('midi', {}), self)
        self.midi_dialog.finished.connect(self.save_settings)
        self.setlist_dialog = SetlistDialog(self)
        stored_setlist = self.settings.get('setlist_file')
        if stored_setlist and Path(stored_setlist).is_file():
            self.setlist_dialog.load_list(stored_setlist)
        self.apply_music(self.settings.get('music', {}))
        self.refresh_devices()
        self.refresh_voices()
        if self.recovery_pending:
            self.notice.setText('An unfinished session has a recovery backup. Recover it or choose Use current session.')
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)

    def button(self, text, callback, layout, checkable=False):
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def error(self, exc):
        self.notice.setText(str(exc))
        QMessageBox.warning(self, 'TouchMusic', str(exc))

    def parameter(self, key, value, label):
        if key == 'delaytime':
            self.engine.params[key] = value / 1000
            label.setText(f'{value} ms')
        else:
            semitones = key in ('pitch', 'formant')
            self.engine.params[key] = value if semitones else value / 100
            label.setText(f'{value:+d} st' if semitones else f'{value}%')
        if key == 'tune':
            if value:
                self.last_tune = value
            self.tune_button.setChecked(bool(value))
            self.tune_button.setText('Auto-Tune On' if value else 'Auto-Tune Off')

    def toggle_tune(self, checked):
        self.sliders['tune'].setValue(self.last_tune if checked else 0)

    def apply_tune_preset(self, strength, speed):
        self.sliders['retune'].setValue(speed)
        self.sliders['tune'].setValue(strength)

    def build_transport(self, layout):
        controls = QHBoxLayout()
        tempo = QSpinBox()
        tempo.setRange(40, 240)
        tempo.setValue(120)
        tempo.setSuffix(' BPM')
        tempo.setAccessibleName('Tempo')
        tempo.valueChanged.connect(lambda value: self.set_music('bpm', value))
        self.music_controls['bpm'] = tempo
        controls.addWidget(tempo)
        self.button('Tap tempo', self.tap_tempo, controls)
        quantize = QComboBox()
        quantize.addItems(QUANTIZE)
        quantize.setAccessibleName('Loop and chord timing')
        quantize.currentTextChanged.connect(lambda value: self.set_music('quantize', value))
        self.music_controls['quantize'] = quantize
        controls.addWidget(quantize)
        click = QCheckBox('Metronome')
        click.toggled.connect(lambda value: self.set_music('metronome', value))
        self.music_controls['metronome'] = click
        controls.addWidget(click)
        source = QComboBox()
        source.addItems(['Processed vocal', 'Mic before AI'])
        source.setAccessibleName('Loop input')
        source.setToolTip('Choose what new loops capture. Mic before AI skips conversion delay and downstream effects.')
        source.currentTextChanged.connect(lambda value: self.set_music('loop_input', value))
        self.music_controls['loop_input'] = source
        controls.addWidget(source)
        self.beat_status = QLabel('4/4')
        controls.addWidget(self.beat_status)
        controls.addStretch()
        layout.addLayout(controls)
        capture_row = QHBoxLayout()
        mode = QComboBox()
        mode.addItems(['Replace', 'Overdub'])
        mode.setToolTip('Replace records a fresh take. Overdub adds to an existing loop. Click its pad again to finish.')
        mode.currentTextChanged.connect(lambda value: self.set_music('loop_mode', value))
        self.music_controls['loop_mode'] = mode
        capture_row.addWidget(QLabel('Capture'))
        capture_row.addWidget(mode)
        count = QSpinBox()
        count.setRange(0, 2)
        count.setSuffix(' bars')
        count.valueChanged.connect(lambda value: self.set_music('count_in', value))
        self.music_controls['count_in'] = count
        capture_row.addWidget(QLabel('Count-in'))
        capture_row.addWidget(count)
        length = QComboBox()
        length.addItem('Free length', 0)
        for bars in (1, 2, 4, 8):
            length.addItem(f'{bars} bar' if bars == 1 else f'{bars} bars', bars)
        length.currentIndexChanged.connect(lambda _: self.set_music('capture_bars', length.currentData()))
        self.music_controls['capture_bars'] = length
        capture_row.addWidget(length)
        feedback = QSpinBox()
        feedback.setRange(0, 100)
        feedback.setValue(100)
        feedback.setSuffix('%')
        feedback.setToolTip('Existing-layer level kept on each overdub pass. 100% keeps it unchanged.')
        feedback.valueChanged.connect(lambda value: self.set_music('overdub_feedback', value))
        self.music_controls['overdub_feedback'] = feedback
        capture_row.addWidget(QLabel('Layer feedback'))
        capture_row.addWidget(feedback)
        seam = QSpinBox()
        seam.setRange(0, 20)
        seam.setSuffix(' ms')
        seam.setToolTip('Short fade at each loop edge reduces clicks without changing its length.')
        seam.valueChanged.connect(lambda value: self.set_music('seam_ms', value))
        self.music_controls['seam_ms'] = seam
        capture_row.addWidget(QLabel('Edge fade'))
        capture_row.addWidget(seam)
        capture_row.addStretch()
        layout.addLayout(capture_row)
        pads = QHBoxLayout()
        self.loop_pads = []
        self.loop_progress = []
        self.pad_levels = []
        self.pad_mutes = []
        for index in range(LOOP_COUNT):
            column = QVBoxLayout()
            capture = self.button(f'Loop {index+1}', lambda _, i=index: self.loop_command('loop', i), column)
            capture.setMinimumHeight(38)
            self.loop_pads.append(capture)
            progress = QProgressBar()
            progress.setRange(0, 1000)
            progress.setValue(0)
            progress.setTextVisible(False)
            progress.setFixedHeight(5)
            progress.setAccessibleName(f'Loop {index+1} playback progress')
            self.loop_progress.append(progress)
            column.addWidget(progress)
            mix = QHBoxLayout()
            level = QSlider(Qt.Horizontal)
            level.setRange(0, 100)
            level.setAccessibleName(f'Loop {index+1} level')
            level.setValue(round(self.engine.loops[index].gain * 100))
            level.valueChanged.connect(lambda value, i=index: setattr(self.engine.loops[i], 'gain', value / 100))
            self.pad_levels.append(level)
            mix.addWidget(level, 1)
            mute = self.button('Mute', lambda _, i=index: self.loop_command('mute', i), mix, True)
            mute.setAccessibleName(f'Mute loop {index+1}')
            self.pad_mutes.append(mute)
            column.addLayout(mix)
            pads.addLayout(column, 1)
        layout.addLayout(pads)

    def tap_tempo(self):
        now = time.monotonic()
        if self.tempo_taps and now - self.tempo_taps[-1] > 1.8:
            self.tempo_taps.clear()
        self.tempo_taps = [*self.tempo_taps[-4:], now]
        if len(self.tempo_taps) > 1:
            interval = median(np.diff(self.tempo_taps))
            if interval >= .25:
                self.music_controls['bpm'].setValue(round(60 / interval))

    def build_music_tools(self, pitch_layout):
        dialog = QDialog(self)
        dialog.setWindowTitle('Music tools')
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)
        grid = QGridLayout()
        layout.addLayout(grid)
        pitch_grid = QGridLayout()
        pitch_layout.addLayout(pitch_grid)
        choices = [
            ('key', 'Song key', NOTES, 0),
            ('scale', 'Scale', SCALES, 'Major'),
            ('tune_target', 'Auto-Tune target', ('Key / scale', 'Chromatic', 'Current chord'), 'Key / scale'),
            ('chord', 'Chord', DEGREES, 0),
            ('monitor', 'Headphone mix', ('Wet vocal', 'Dry mic'), 'Wet vocal'),
            ('quality', 'AI quality', ('Live', 'Studio'), 'Live'),
            ('vocal_range', 'Vocal range', VOCAL_RANGES, 'Wide'),
            ('harmony_mode', 'Harmony mode', HARMONY_MODES, 'Fixed fifth'),
        ]
        for row, (key, label, items, default) in enumerate(choices):
            combo = QComboBox()
            combo.addItems(list(items))
            combo.setAccessibleName(label)
            area = pitch_grid if row < 3 else grid
            column = row if row < 3 else 0
            area.addWidget(QLabel(label), 0 if row < 3 else row - 3, column)
            if row < 3:
                area.addWidget(combo, 1, column)
            else:
                area.addWidget(combo, row - 3, 1, 1, 2)
            self.music_controls[key] = combo
            if isinstance(default, int):
                combo.currentIndexChanged.connect(lambda value, k=key: self.set_music(k, value))
            else:
                combo.currentTextChanged.connect(lambda value, k=key: self.set_music(k, value))
        for row, (key, label, low, high) in enumerate([
            ('tune', 'Tune strength', 0, 100), ('retune', 'Retune speed', 0, 100),
            ('chord_level', 'Chord level', 0, 100), ('vibrato', 'Preserve vibrato', 0, 100),
            ('formant', 'Formant', -5, 5),
        ], start=2):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(low, high)
            slider.setAccessibleName(label)
            value = QLabel()
            self.sliders[key] = slider
            slider.valueChanged.connect(lambda v, k=key, out=value: self.parameter(k, v, out))
            slider.setValue(round(self.engine.params.get(key, 0) * (1 if key == 'formant' else 100)))
            self.parameter(key, slider.value(), value)
            area, position = (pitch_grid, row) if row < 4 else (grid, row + 2)
            area.addWidget(QLabel(label), position, 0)
            area.addWidget(slider, position, 1)
            area.addWidget(value, position, 2)
            slider.setValue(self.settings.get('effects', {}).get(key, slider.value()))
        for key, label in [('chord_enabled', 'Play chord pad'), ('stems', 'Record separate WAV stems'),
                           ('align_ai', 'Export aligned vocal and mix')]:
            box = QCheckBox(label)
            self.music_controls[key] = box
            box.toggled.connect(lambda value, k=key: self.set_music(k, value))
            layout.addWidget(box)
        help_text = QLabel('Map Chord I–VII or Next chord in Gesture mapping. '
                           'Studio uses a longer buffer. Dry mic monitoring keeps the recorded mix wet.')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.button('Map left fingers 1–5 to chords I–V', self.map_left_chords, layout)
        self.button('Done', dialog.accept, layout)
        dialog.finished.connect(self.save_settings)
        self.music_dialog = dialog

    def open_music_tools(self):
        self.music_dialog.show()
        self.music_dialog.raise_()

    def open_midi_dialog(self):
        self.midi_dialog.refresh()
        self.midi_dialog.show()
        self.midi_dialog.raise_()

    def open_setlist(self):
        self.setlist_dialog.show()
        self.setlist_dialog.raise_()

    def map_left_chords(self):
        for index, action in enumerate(CHORD_ACTIONS[:5], 1):
            self.mappings[f'Left_{index}'].setCurrentText(action)
        self.notice.setText('Left fingers 1–5 now select chords I–V.')

    def toggle_rehearsal(self, active):
        self.gesture_preview.setText('Hold a mapped pose to preview its action.' if active else '')
        if active:
            self.arm.setChecked(False)
        self.arm.setEnabled(not active)

    def set_music(self, key, value):
        if key == 'quality':
            if self.engine.converter:
                self.engine.converter.set_quality(value)
        elif key == 'chord' and self.engine.stream:
            self.engine.commands.put(('chord', value))
        elif key == 'overdub_feedback':
            self.engine.params[key] = value / 100
        elif key not in ('stems', 'align_ai'):
            self.engine.params[key] = value

    def apply_music(self, settings):
        for key, combo in self.music_controls.items():
            value = settings.get(key)
            if isinstance(combo, QCheckBox) and isinstance(value, bool):
                combo.setChecked(value)
            elif isinstance(combo, QSpinBox) and type(value) is int:
                combo.setValue(value)
            elif key in ('key', 'chord') and type(value) is int and 0 <= value < combo.count():
                combo.setCurrentIndex(value)
            elif isinstance(combo, QComboBox) and isinstance(value, str) and combo.findText(value) >= 0:
                combo.setCurrentText(value)

    def mapping_combo(self, key, choices, default='None'):
        combo = QComboBox()
        combo.addItems(choices)
        if choices is ACTIONS:
            combo.addItems([SCENE_PREFIX + name for name in self.saved_presets])
            self.gesture_selectors.append(combo)
        combo.setCurrentText(self.settings.get('mapping', {}).get(key, default))
        self.mappings[key] = combo
        return combo

    def build_gesture_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Gesture mapping')
        dialog.setMinimumWidth(560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Arm gestures in the main window. Hold a pose for a quarter second.'))
        grid = QGridLayout()
        grid.addWidget(QLabel('Pose or movement'), 0, 0)
        grid.addWidget(QLabel('Left hand'), 0, 1)
        grid.addWidget(QLabel('Right hand'), 0, 2)
        grid.addWidget(QLabel('Side to side'), 1, 0)
        grid.addWidget(QLabel('Thumb + index spread'), 2, 0)
        grid.addWidget(QLabel('Thumb + index pinch'), 3, 0)
        for count in range(6):
            label = 'Fist' if count == 0 else '1 finger' if count == 1 else f'{count} fingers'
            grid.addWidget(QLabel(label), 4 + count, 0)
        for column, hand in enumerate(('Left', 'Right'), start=1):
            grid.addWidget(self.mapping_combo(hand + '_x', EFFECT_TARGETS), 1, column)
            grid.addWidget(self.mapping_combo(hand + '_span', EFFECT_TARGETS), 2, column)
            if hand == 'Left':
                grid.addWidget(self.mapping_combo('left_pinch', ACTIONS), 3, column)
            else:
                grid.addWidget(QLabel('Set in the main window'), 3, column)
            for count in range(6):
                default = f'Voice {count}' if hand == 'Right' and 1 <= count <= 4 else 'None'
                grid.addWidget(self.mapping_combo(f'{hand}_{count}', ACTIONS, default), 4 + count, column)
        layout.addLayout(grid)
        slots = QGridLayout()
        self.voice_slots = {}
        for row, slot in enumerate(VOICE_SLOTS):
            slots.addWidget(QLabel(slot), row, 0)
            self.voice_slots[slot] = QComboBox()
            slots.addWidget(self.voice_slots[slot], row, 1)
        layout.addLayout(slots)
        self.button('Done', dialog.accept, layout)
        dialog.finished.connect(self.save_settings)
        self.gesture_dialog = dialog

    def open_gesture_dialog(self):
        self.gesture_dialog.show()
        self.gesture_dialog.raise_()
        self.gesture_dialog.activateWindow()

    def refresh_voice_slots(self):
        stored = self.settings.get('voice_slots', {})
        for position, (slot, combo) in enumerate(self.voice_slots.items()):
            if combo.count():
                selected = combo.currentData()
            elif slot in stored:
                selected = stored[slot]
            else:
                selected = self.voices[position]['id'] if position < len(self.voices) else None
            combo.clear()
            combo.addItem('Unassigned', None)
            for voice in self.voices:
                combo.addItem(voice['name'], voice['id'])
            combo.setCurrentIndex(max(0, combo.findData(selected)))

    def preset(self, name):
        saved = self.saved_presets.get(name)
        if saved:
            self.apply_performance(saved)
            return
        if name in BUILTIN_PRESETS:
            for key, slider in self.sliders.items():
                if key not in ('gain', 'aimix', 'master', 'tune', 'retune', 'chord_level', 'formant', 'vibrato'):
                    slider.setValue(BUILTIN_PRESETS[name].get(key, EFFECT_DEFAULTS.get(key, 0)))

    def apply_performance(self, saved):
        for key, value in saved.get('effects', {}).items():
            if key in self.sliders and type(value) is int:
                self.sliders[key].setValue(value)
        self.apply_music(saved.get('music', {}))
        self.midi_dialog.apply_settings(saved.get('midi', {}))
        if isinstance(saved.get('dialogue'), bool):
            self.dialogue.setChecked(saved['dialogue'])
        if type(saved.get('track_level')) is int:
            self.track_volume.setValue(saved['track_level'])
        for track, level in zip(self.engine.loops, saved.get('loop_levels', [])):
            if type(level) is int:
                track.gain = max(0, min(100, level)) / 100
        self.sync_loop_level()
        for key, action in saved.get('mapping', {}).items():
            if key in self.mappings and isinstance(action, str):
                self.mappings[key].setCurrentText(action)
        for slot, voice_id in saved.get('voice_slots', {}).items():
            if slot in self.voice_slots:
                combo = self.voice_slots[slot]
                combo.setCurrentIndex(max(0, combo.findData(voice_id)))
        voice_index = self.voice_combo.findData(saved.get('voice'))
        if voice_index >= 0:
            self.voice_combo.setCurrentIndex(voice_index)

    def save_preset(self):
        name, accepted = QInputDialog.getText(self, 'Save performance preset', 'Preset name')
        name = name.strip()
        if not accepted or not name:
            return
        index = self.preset_combo.findText(name, Qt.MatchFixedString)
        if 0 <= index <= len(BUILTIN_PRESETS):
            self.notice.setText('Choose a name different from the built-in presets.')
            return
        self.saved_presets[name] = self.performance_settings()
        if index < 0:
            self.preset_combo.addItem(name)
            for selector in self.gesture_selectors:
                selector.addItem(SCENE_PREFIX + name)
        self.preset_combo.setCurrentText(name)
        self.save_settings()

    def performance_settings(self):
        music = {}
        for key, control in self.music_controls.items():
            if isinstance(control, QCheckBox):
                music[key] = control.isChecked()
            elif isinstance(control, QSpinBox):
                music[key] = control.value()
            elif key in ('key', 'chord'):
                music[key] = control.currentIndex()
            else:
                music[key] = control.currentText()
        return {
            'effects': {key: slider.value() for key, slider in self.sliders.items()},
            'mapping': {key: combo.currentText() for key, combo in self.mappings.items()},
            'voice': self.voice_combo.currentData(),
            'voice_slots': {slot: combo.currentData() for slot, combo in self.voice_slots.items()},
            'dialogue': self.dialogue.isChecked(),
            'track_level': self.track_volume.value(),
            'loop_levels': [round(track.gain * 100) for track in self.engine.loops],
            'music': music,
            'midi': self.midi_dialog.settings(),
        }

    def save_skit(self):
        if any(loop.recording for loop in self.engine.loops):
            self.notice.setText('Finish the active loop capture before saving.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save skit', 'Performance.touchmusic',
                                              'TouchMusic skit (*.touchmusic)')
        if not path:
            return
        if not path.lower().endswith('.touchmusic'):
            path += '.touchmusic'
        try:
            settings, assets, voices = self.session_snapshot()
            save_project(path, settings, assets, voices)
            self.notice.setText(f'Skit saved to {path}')
        except Exception as exc:
            self.error(exc)

    def session_snapshot(self):
        settings = self.performance_settings()
        settings.update(track_name=self.track_label.text(), ai=self.ai.isChecked() or self.ai_requested,
                        loop_selected=self.loop_select.currentIndex(),
                        muted_loops=[loop.muted for loop in self.engine.loops],
                        scenes=self.saved_presets)
        assets = {f'loop-{index}': loop.clip for index, loop in enumerate(self.engine.loops, 1)
                  if loop.clip is not None}
        if len(self.engine.track.audio):
            assets['backing'] = self.engine.track.audio
        identities = {settings['voice'], *settings['voice_slots'].values()}
        for scene in self.saved_presets.values():
            identities.update([scene.get('voice'), *scene.get('voice_slots', {}).values()])
        voices = [(voice, self.library.path(voice)) for voice in self.voices
                  if voice['id'] in identities and voice.get('file') and self.library.path(voice).is_file()]
        return settings, assets, voices

    def open_skit(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open skit', '', 'TouchMusic skit (*.touchmusic)')
        if path:
            self.load_skit_path(path)

    def load_skit_path(self, path):
        if self.engine.recorder or any(loop.recording for loop in self.engine.loops):
            self.notice.setText('Finish recording before opening a skit.')
            return False
        try:
            self.apply_session(*load_project(path))
            self.notice.setText(f'Opened {Path(path).name}. Start audio when ready.')
            return True
        except Exception as exc:
            self.notice.setText('Could not open skit: ' + str(exc))
            return False

    def apply_session(self, settings, assets, voices):
        if self.engine.stream:
            self.toggle_audio()
        self.arm.setChecked(False)
        self.library.restore_references(voices)
        self.refresh_voices()
        for name, scene in settings.get('scenes', {}).items():
            self.saved_presets[name] = scene
            if self.preset_combo.findText(name, Qt.MatchFixedString) < 0:
                self.preset_combo.addItem(name)
                for selector in self.gesture_selectors:
                    selector.addItem(SCENE_PREFIX + name)
        self.preset_combo.setCurrentText('Custom')
        for index, loop in enumerate(self.engine.loops, 1):
            loop.load(assets.get(f'loop-{index}'))
            loop.previous = None
            loop.muted = False
        for loop, muted in zip(self.engine.loops, settings.get('muted_loops', [])):
            loop.muted = bool(muted)
        self.engine.track.load(assets.get('backing', np.zeros(0, np.float32)))
        self.track_label.setText(settings.get('track_name', 'Backing track') if 'backing' in assets else 'No backing track loaded')
        self.loop_select.setCurrentIndex(settings.get('loop_selected', 0))
        self.apply_performance(settings)
        self.ai.setChecked(False)
        self.ai_requested = bool(settings.get('ai'))

    def use_current_session(self):
        self.recovery_pending = False
        self.recover_button.hide()
        self.keep_button.hide()
        self.recovery_fingerprint = None
        self.notice.setText('Current session selected. Automatic recovery saves are enabled.')

    def restore_recovery(self):
        if self.engine.recorder or any(loop.recording for loop in self.engine.loops):
            self.notice.setText('Finish recording before recovering a session.')
            return
        try:
            self.apply_session(*self.recovery.load_recovery())
            self.use_current_session()
            self.notice.setText('Recovered completed loops and settings. Start audio when ready.')
        except Exception as exc:
            self.notice.setText('Recovery failed: ' + str(exc))

    def backup_session(self, force=False):
        if self.recovery_pending or any(loop.recording for loop in self.engine.loops):
            if force:
                self.notice.setText('Choose Recover or Use current session, and finish loop capture before saving recovery.')
            return
        now = time.monotonic()
        if not force and now - self.last_recovery_check < 1:
            return
        self.last_recovery_check = now
        try:
            settings, assets, voices = self.session_snapshot()
        except Exception as exc:
            self.notice.setText('Recovery snapshot failed: ' + str(exc))
            return
        fingerprint = (json.dumps(settings, sort_keys=True), tuple((key, id(value)) for key, value in assets.items()))
        if fingerprint != self.recovery_fingerprint:
            self.recovery_fingerprint = fingerprint
            self.recovery_changed_at = now
        if force or (fingerprint != getattr(self, 'recovery_submitted', None) and now - self.recovery_changed_at >= 3):
            self.recovery.submit(settings, assets, voices, copy_assets=False)
            self.recovery_submitted = fingerprint
            if force:
                self.notice.setText('Recovery save queued. Completed loops and settings are saved in the background.')
        if self.recovery.error and self.recovery.error != getattr(self, 'last_recovery_error', ''):
            self.last_recovery_error = self.recovery.error
            self.notice.setText('Recovery save failed: ' + self.recovery.error)

    def save_settings(self):
        self.settings = {**self.performance_settings(), 'presets': self.saved_presets,
                         'input': self.inputs.currentText(), 'output': self.outputs.currentText(),
                         'setlist_file': str(self.setlist_dialog.path or '')}
        save_json(self.settings_path, self.settings)

    def refresh_devices(self):
        if self.engine.stream:
            self.notice.setText('Stop audio before refreshing devices.')
            return
        old_input = self.inputs.currentText() or self.settings.get('input', '')
        old_output = self.outputs.currentText() or self.settings.get('output', '')
        self.inputs.blockSignals(True)
        self.inputs.clear()
        try:
            self.audio_devices = sd.query_devices()
            self.audio_apis = sd.query_hostapis()
            for index, device in enumerate(self.audio_devices):
                api = self.audio_apis[device['hostapi']]['name']
                label = f"{device['name']} ({api})"
                if device['max_input_channels']:
                    self.inputs.addItem(label, index)
            index = self.inputs.findText(old_input)
            if index < 0:
                wasapi = next((api for api in self.audio_apis if api['name'] == 'Windows WASAPI'), None)
                if wasapi:
                    index = self.inputs.findData(wasapi['default_input_device'])
            self.inputs.setCurrentIndex(max(index, 0))
            self.refresh_outputs(preferred=old_output)
        except Exception as exc:
            self.notice.setText(str(exc))
        finally:
            self.inputs.blockSignals(False)

    def refresh_outputs(self, *_args, preferred=None):
        old_output = self.outputs.currentText() if preferred is None else preferred
        self.outputs.clear()
        input_device = self.inputs.currentData()
        if input_device is None:
            return
        host = self.audio_devices[input_device]['hostapi']
        api = self.audio_apis[host]
        for index, device in enumerate(self.audio_devices):
            if device['hostapi'] == host and device['max_output_channels'] >= 2:
                self.outputs.addItem(f"{device['name']} ({api['name']})", index)
        index = self.outputs.findText(old_output)
        if index < 0:
            index = self.outputs.findData(api['default_output_device'])
        self.outputs.setCurrentIndex(max(index, 0))

    def toggle_audio(self):
        try:
            if self.engine.stream:
                recorder = self.engine.stop()
                self.music_controls['chord'].setCurrentIndex(self.engine.params['chord'])
                self.audio_button.setText('Start audio')
                self.notice.setText('Audio stopped')
                self.record_button.setText('Record performance')
                if recorder:
                    self.show_recording_result(recorder)
            else:
                if self.inputs.currentData() is None or self.outputs.currentData() is None:
                    raise ValueError('Select an available microphone and output.')
                self.engine.start(self.inputs.currentData(), self.outputs.currentData())
                self.audio_button.setText('Stop audio')
                self.notice.setText('Audio running. Space mutes output. Settings are saved when you close.')
            self.inputs.setEnabled(not self.engine.stream)
            self.outputs.setEnabled(not self.engine.stream)
        except Exception as exc:
            self.error(exc)

    def toggle_mute(self, checked):
        self.engine.muted = checked
        self.mute_button.setText('Unmute output' if checked else 'Mute output')

    def refresh_voices(self):
        selected = self.voice_combo.currentData() or self.settings.get('voice')
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        self.voices = self.library.voices
        for voice in self.voices:
            self.voice_combo.addItem(f"{voice['name']}  ·  {voice['seconds']} s", voice['id'])
        index = self.voice_combo.findData(selected)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        self.voice_combo.blockSignals(False)
        self.refresh_voice_slots()
        self.select_voice()

    def current_voice(self):
        index = self.voice_combo.currentIndex()
        return self.voices[index] if 0 <= index < len(self.voices) else None

    def import_voice(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Import reference voices', '', 'Audio (*.wav *.mp3 *.flac *.ogg)')
        errors = []
        imported = None
        for path in paths:
            try:
                picker = ReferencePicker(path, self)
                if picker.exec() == QDialog.Accepted:
                    imported = self.library.import_file(
                        path, picker.name.text().strip(), start_seconds=picker.waveform.start,
                        duration_seconds=picker.waveform.end - picker.waveform.start)
                picker.deleteLater()
            except Exception as exc:
                errors.append(f'{Path(path).name}: {exc}')
        self.refresh_voices()
        if imported:
            self.voice_combo.setCurrentIndex(self.voice_combo.findData(imported['id']))
            self.notice.setText(f"Selected {imported['name']} · {imported['seconds']} s reference. "
                                'Load the singing engine and enable AI conversion to use it.')
        if errors:
            self.error('\n'.join(errors))

    def rename_voice(self):
        voice = self.current_voice()
        if voice:
            name, accepted = QInputDialog.getText(self, 'Rename voice', 'Display name', text=voice['name'])
            if accepted:
                try:
                    self.library.rename(voice['id'], name)
                    self.refresh_voices()
                except Exception as exc:
                    self.error(exc)

    def preview_voice(self):
        voice = self.current_voice()
        if not self.engine.stream:
            self.notice.setText('Start audio to preview the selected reference.')
            return
        if voice:
            try:
                self.engine.preview.load(read_audio(self.library.path(voice)))
                self.engine.preview.restart()
            except Exception as exc:
                self.error(exc)

    def select_voice(self, *_):
        voice = self.current_voice()
        if voice and self.engine.converter:
            self.engine.converter.select(self.library.path(voice))

    def load_model(self):
        if self.engine.converter and self.engine.converter.thread.is_alive():
            return
        self.engine.converter = StreamingConverter()
        self.engine.converter.set_quality(self.music_controls['quality'].currentText())
        self.model_button.setEnabled(False)
        self.model_button.setText('Loading singing engine…')
        self.select_voice()

    def toggle_ai(self, checked):
        self.engine.neural = checked
        if self.engine.converter:
            self.engine.converter.reset()
        if checked:
            self.notice.setText('AI conversion uses buffered audio. Its timing appears below the voice selector.')

    def toggle_dialogue(self, checked):
        self.engine.params['dialogue'] = checked

    def toggle_camera(self):
        if self.camera:
            self.camera.stop()
            self.camera_button.setEnabled(False)
            self.tracking.setText('Stopping camera…')
            self.arm.setChecked(False)
        else:
            self.camera = CameraWorker(self.camera_index.value())
            self.camera.frame.connect(self.camera_frame)
            self.camera.controls.connect(self.gestures)
            self.camera.status.connect(self.tracking.setText)
            self.camera.finished.connect(self.camera_finished)
            self.camera.start()
            self.camera_button.setText('Stop camera')

    def camera_finished(self):
        self.camera.deleteLater()
        self.camera = None
        self.camera_button.setEnabled(True)
        self.camera_button.setText('Start camera')
        self.arm.setChecked(False)
        if self.closing:
            self.close()

    def camera_frame(self, frame):
        height, width, _ = frame.shape
        image = QImage(frame.data, width, height, frame.strides[0], QImage.Format_RGB888).copy()
        self.camera_label.setPixmap(QPixmap.fromImage(image).scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def gestures(self, controls):
        detected = []
        for control in controls:
            hand = control['hand']
            pinch_action = self.pinch_action(hand)
            fingers = control.get('fingers')
            if control.get('held') and (pinch_action != 'None' or fingers != 0):
                pose = 'pinch'
            elif fingers == 0:
                pose = 'fist'
            elif fingers is not None:
                pose = f'{fingers} fingers' if fingers != 1 else '1 finger'
            else:
                pose = None
            detected.append(f'{hand} {pose}' if pose else hand)
        rehearsal = self.rehearse.isChecked()
        state = 'Rehearsal' if rehearsal else 'Armed' if self.arm.isChecked() else 'Disarmed'
        self.tracking.setText(f"{state} · {', '.join(detected)}" if detected else f'{state} · Show your hands')
        if not self.arm.isChecked() and not rehearsal:
            return
        for control in controls:
            hand = control['hand']
            for key, value in ((hand, control['y']), (hand + '_x', 1 - control['x'])):
                self.gesture_level(self.mappings[key].currentText(), value)
            if 'span' in control:
                self.gesture_level(self.mappings[hand + '_span'].currentText(), control['span'])
            now = time.monotonic()
            pinch_action = self.pinch_action(hand)
            if control.get('held') and pinch_action != 'None':
                if control['pinch'] and now - self.last_pinch.get(hand, 0) > .6:
                    self.last_pinch[hand] = now
                    self.gesture_action(pinch_action, f'{hand} pinch')
                continue
            if control.get('pose') is not None:
                count = control['pose']
                pose_label = 'fist' if count == 0 else '1 finger' if count == 1 else f'{count} fingers'
                self.gesture_action(self.mappings[f'{hand}_{count}'].currentText(), f'{hand} {pose_label}')

    def pinch_action(self, hand):
        return self.mappings['pinch' if hand == 'Right' else 'left_pinch'].currentText()

    def gesture_level(self, target, value):
        if self.rehearse.isChecked():
            return
        if target.startswith('MIDI CC '):
            self.midi.control(int(target.removeprefix('MIDI CC ')), value)
            return
        if target == 'Track level':
            slider = self.track_volume
        elif target.startswith('Loop ') and target.endswith(' level'):
            index = int(target.split()[1]) - 1
            slider = self.pad_levels[index]
        else:
            slider = self.sliders.get(TARGET_KEYS.get(target, target.lower()))
        if slider is not None:
            slider.setValue(round(slider.minimum() + value * (slider.maximum() - slider.minimum())))

    def sync_loop_level(self, *_):
        for slider, track in zip(self.pad_levels, self.engine.loops):
            slider.setValue(round(track.gain * 100))

    def selected_loop(self):
        return self.engine.loops[self.loop_select.currentIndex()]

    def toggle_loop(self):
        self.loop_command('loop')

    def loop_command(self, action, index=None):
        if action in ('loop', 'overdub') and not self.engine.stream:
            self.notice.setText('Start audio before capturing a loop.')
            return
        if index is None:
            index = self.loop_select.currentIndex()
        else:
            self.loop_select.setCurrentIndex(index)
        self.engine.commands.put((action, index))
        if not self.engine.stream:
            self.engine.apply_loop_commands()

    def export_loop(self):
        clip = self.selected_loop().clip
        if clip is None:
            self.notice.setText('Finish capturing the selected loop before exporting.')
            return
        folder = DATA / 'recordings'
        folder.mkdir(exist_ok=True)
        suggested = folder / f'loop-{self.loop_select.currentIndex()+1}-{datetime.now():%Y%m%d-%H%M%S}.wav'
        path, _ = QFileDialog.getSaveFileName(self, 'Export loop', str(suggested), 'Wave audio (*.wav)')
        if path:
            try:
                sf.write(path, clip, RATE, subtype='PCM_24')
                self.notice.setText(f'Loop saved to {path}')
            except (OSError, RuntimeError) as exc:
                self.error(exc)

    def gesture_action(self, action, pose='Gesture'):
        if self.rehearse.isChecked():
            self.gesture_preview.setText(f'{pose} would trigger {action}' if action != 'None' else f'{pose} is unassigned')
            return
        if action in MIDI_ACTIONS:
            if action == 'MIDI panic':
                self.midi.panic()
            else:
                p = self.engine.params
                notes = [MIDI_NOTES[action]] if action in MIDI_NOTES else [
                    note + 48 for note in chord_notes(p['key'], p['scale'], MIDI_CHORDS.get(action, p['chord']))]
                self.midi.play(notes, self.midi_dialog.velocity.value(), self.midi_dialog.length.value() / 1000)
        elif action in self.voice_slots:
            voice = self.voice_slots[action].currentData()
            index = self.voice_combo.findData(voice) if voice is not None else -1
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
        elif action in ('Next voice', 'Previous voice') and self.voice_combo.count():
            step = 1 if action == 'Next voice' else -1
            self.voice_combo.setCurrentIndex((self.voice_combo.currentIndex() + step) % self.voice_combo.count())
        elif action == 'Loop':
            self.toggle_loop()
        elif action == 'Undo selected loop':
            self.loop_command('undo')
        elif action == 'Overdub selected loop':
            self.loop_command('overdub')
        elif action == 'Redo selected loop':
            self.loop_command('redo')
        elif action in ('Next song', 'Previous song'):
            self.setlist_dialog.step(1 if action == 'Next song' else -1)
        elif action in LOOP_ACTIONS:
            self.loop_command(*LOOP_ACTIONS[action])
        elif action in CHORD_ACTIONS:
            self.music_controls['chord'].setCurrentIndex(CHORD_ACTIONS.index(action))
        elif action in ('Next chord', 'Previous chord'):
            selection = self.music_controls['chord']
            step = 1 if action == 'Next chord' else -1
            selection.setCurrentIndex((selection.currentIndex() + step) % len(DEGREES))
        elif action == 'Toggle chords':
            self.music_controls['chord_enabled'].toggle()
        elif action == 'Toggle Auto-Tune':
            self.tune_button.click()
        elif action == 'Tap tempo':
            self.tap_tempo()
        elif action == 'Toggle metronome':
            self.music_controls['metronome'].toggle()
        elif action == 'Toggle dry monitoring':
            monitor = self.music_controls['monitor']
            monitor.setCurrentIndex(1 - monitor.currentIndex())
        elif action in ('Next loop', 'Previous loop'):
            step = 1 if action == 'Next loop' else -1
            self.loop_select.setCurrentIndex((self.loop_select.currentIndex() + step) % LOOP_COUNT)
        elif action == 'Mute output':
            self.mute_button.click()
        elif action == 'AI conversion':
            if self.ai.isEnabled():
                self.ai.click()
            else:
                self.notice.setText('Load the singing engine and select a reference voice first.')
        elif action == 'Dialogue mode':
            self.dialogue.click()
        elif action == 'Play / pause track':
            self.play_track()
        elif action == 'Restart track':
            self.engine.track.restart()
        elif action == 'Record performance':
            self.toggle_recording(quick=True)
        elif action.startswith(SCENE_PREFIX):
            name = action.removeprefix(SCENE_PREFIX)
            if self.preset_combo.currentText() == name:
                self.preset(name)
            else:
                self.preset_combo.setCurrentText(name)
        elif action in BUILTIN_PRESETS:
            if self.preset_combo.currentText() == action:
                self.preset(action)
            else:
                self.preset_combo.setCurrentText(action)

    def open_track(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open backing track', '', 'Audio (*.wav *.mp3 *.flac *.ogg)')
        if path:
            try:
                self.engine.track.load(read_audio(path))
                self.track_label.setText(Path(path).name)
            except Exception as exc:
                self.error(exc)

    def play_track(self):
        self.engine.track.toggle()

    def toggle_recording(self, quick=False):
        if self.engine.recorder:
            recorder = self.engine.stop_recording()
            self.record_button.setText('Record performance')
            self.show_recording_result(recorder)
        else:
            if not self.engine.stream:
                self.notice.setText('Start audio before recording.')
                return
            folder = DATA / 'recordings'
            folder.mkdir(exist_ok=True)
            name = folder / (datetime.now().strftime('performance-%Y%m%d-%H%M%S-%f') + '.wav')
            if quick:
                path = str(name)
            else:
                path, _ = QFileDialog.getSaveFileName(self, 'Record performance', str(name), 'Wave audio (*.wav)')
            if path:
                try:
                    self.engine.start_recording(path, stems=self.music_controls['stems'].isChecked(),
                                                align=self.music_controls['align_ai'].isChecked())
                    self.record_button.setText('Stop recording')
                    self.notice.setText('Recording to ' + path)
                except Exception as exc:
                    self.error(exc)

    def show_recording_result(self, recorder):
        if recorder.error:
            self.notice.setText('Recording failed: ' + recorder.error)
        elif recorder.alignment_thread:
            self.pending_exports.append(recorder)
            self.notice.setText('Recording saved. Exporting aligned vocal and mix…')
        elif recorder.alignment_error:
            self.notice.setText('Recording saved. Alignment skipped: ' + recorder.alignment_error)
        else:
            self.notice.setText(f'Recording saved. Dropped audio blocks: {recorder.dropped}.')

    def tick(self):
        self.midi.tick()
        self.backup_session()
        if self.midi.error:
            self.midi_dialog.update_status()
        for recorder in self.pending_exports[:]:
            if not recorder.alignment_thread.is_alive():
                self.pending_exports.remove(recorder)
                if recorder.alignment_error:
                    self.notice.setText('Recording saved. Alignment failed: ' + recorder.alignment_error)
                else:
                    self.notice.setText(f'Aligned mix saved to {recorder.aligned_mix}')
        if self.engine.recorder and self.engine.recorder.error:
            recorder = self.engine.stop_recording()
            self.record_button.setText('Record performance')
            self.notice.setText('Recording failed: ' + recorder.error)
        self.input_meter.setValue(min(100, int(self.engine.input_peak * 100)))
        self.output_meter.setValue(min(100, int(self.engine.peak * 100)))
        track = self.selected_loop()
        self.undo_button.setEnabled(track.previous is not None and not track.recording)
        self.redo_button.setEnabled(bool(track.future) and not track.recording)
        for index, (loop, pad, mute) in enumerate(zip(self.engine.loops, self.loop_pads, self.pad_mutes)):
            clip = loop.clip
            self.loop_progress[index].setValue(round(1000 * loop.position / len(clip)) if clip is not None and len(clip) else 0)
            pending = self.engine.clock.pending
            key = next((key for key in (('loop', index), ('overdub', index)) if key in pending), None)
            if key is not None:
                beats = max(0, (pending[key][0] - self.engine.clock.frame) / self.engine.clock.period)
                status = ('Finish' if loop.recording else 'Capture') + f' in {beats:.1f} beats'
                state = 'queued'
            elif loop.recording:
                status = f'{"Overdub" if loop.overdubbing else "Recording"} {loop.size / RATE:.1f} s'
                if ('finish', index) in pending:
                    seconds = max(0, (pending[('finish', index)][0] - self.engine.clock.frame) / RATE)
                    status += f' / {seconds:.1f} s left'
                state = 'recording'
            elif clip is not None:
                status = f'{"Muted" if loop.muted else "Playing"} {len(clip) / RATE:.1f} s'
                state = '' if loop.muted else 'playing'
            else:
                status = 'Empty'
                state = ''
            pad.setText(f'Loop {index+1}  ·  {status}')
            if pad.property('loopState') != state:
                pad.setProperty('loopState', state)
                pad.style().unpolish(pad)
                pad.style().polish(pad)
            mute.setChecked(loop.muted)
        beat = self.engine.clock.beat
        self.beat_status.setText(f'Bar {beat // BEATS_PER_BAR + 1} · Beat {beat % BEATS_PER_BAR + 1}'
                                 if self.engine.stream else '4/4')
        converter = self.engine.converter
        if converter:
            details = f' | {converter.quality} {converter.inference_ms:.0f} ms / {converter.hop // 48} ms chunk | Dropped {converter.dropped}'
            self.model_status.setText(converter.status + (details if converter.ready else ''))
            self.ai.setEnabled(converter.ready)
            if converter.ready and self.ai_requested:
                self.ai_requested = False
                self.ai.setChecked(True)
            if converter.error:
                self.ai.setChecked(False)
                self.model_button.setEnabled(True)
                self.model_button.setText('Retry singing engine')
            elif converter.ready:
                self.model_button.setText('Singing engine loaded')
        p = self.engine.params.copy()
        chord = chord_name(chord_notes(p['key'], p['scale'], p['chord']))
        voice = self.current_voice()
        detected, target = self.engine.detected_note, self.engine.target_note
        pitch = 'Auto-Tune off'
        cents = None
        if p['tune']:
            if p['dialogue']:
                pitch = 'Bypassed by Dialogue mode'
            elif detected is None or target is None:
                pitch = 'Waiting for a sung note'
            else:
                cents = self.engine.pitch_cents
                pitch = f'{NOTES[detected % 12]} to {NOTES[target % 12]}  ·  {cents:+d} cents from target'
        self.pitch_status.setText(pitch)
        self.pitch_meter.set_cents(cents)
        queued = self.engine.queued_chord
        chord_text = f'Chord {DEGREES[p["chord"]]} ({chord})'
        if queued is not None:
            chord_text += f' → {DEGREES[queued]} queued'
        recording = '  |  Recording' if self.engine.recorder else ''
        audio = 'Audio on' if self.engine.stream else 'Audio off'
        gestures = 'Gestures armed' if self.arm.isChecked() else 'Gestures off'
        self.music_status.setText(f"{voice['name'] if voice else 'No voice selected'}  |  {NOTES[p['key']]} {p['scale']}  |  "
                                  f"{chord_text}  |  {p['monitor']}  |  {audio}  |  {gestures}{recording}")
        if self.engine.error:
            self.notice.setText('Audio error: ' + self.engine.error)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.mute_button.click()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        self.midi.close()
        self.engine.stop()
        if self.camera:
            self.closing = True
            self.camera.stop()
            event.ignore()
            return
        if self.engine.converter:
            self.engine.converter.close()
        self.save_settings()
        if not self.recovery_pending:
            self.backup_session(force=True)
        self.recovery.close(clean=not self.recovery_pending)
        event.accept()
