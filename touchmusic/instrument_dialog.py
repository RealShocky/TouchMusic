"""Instrument loading is explicit; saved native instruments never auto-load."""
from pathlib import Path
from .background import BackgroundTask
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QSlider, QFileDialog)


class InstrumentDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.task = None
        self.task_editor = False
        self.task_clear = True
        self.pending = None
        layout = QVBoxLayout(self)
        hint = QLabel('One isolated stereo VST3 synthesizer. Stop audio to load. Start audio to play notes. '
            'Map Instrument note/chord actions to finger poses, and Instrument knobs to movement. '
            'Notes have timed release; disarm and F12 release all notes. Worker delay is 42.7 ms at 48 kHz.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        for title, callback in [('Load instrument file', self.file), ('Load bundle', self.bundle),
                                ('Restore reviewed instrument', self.restore), ('Remove', self.remove),
                                ('Restart', self.restart), ('Panic', self.owner.engine.instrument.panic)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        for title, callback in [('Open native editor', self.open_editor), ('Capture native preset', self.capture_state)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.parameter = QComboBox()
        self.parameter.currentTextChanged.connect(self.select)
        layout.addWidget(self.parameter)
        self.value = QSlider(Qt.Horizontal)
        self.value.setRange(0, 1000)
        self.value.valueChanged.connect(self.set_value)
        layout.addWidget(self.value)
        self.knob = QComboBox()
        self.knob.addItems([f'Instrument knob {i}' for i in range(1, 9)])
        layout.addWidget(self.knob)
        bind = QPushButton('Bind selected knob to this parameter')
        bind.clicked.connect(self.bind)
        layout.addWidget(bind)
        row = QHBoxLayout()
        for name, notes in [('Play C4', [60]), ('Play C major', [60, 64, 67]), ('Play A minor', [57, 60, 64])]:
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, pitches=notes: self.play(pitches))
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(QLabel('Synth level'))
        self.level = QSlider(Qt.Horizontal)
        self.level.setRange(0, 100)
        self.level.setValue(30)
        self.level.valueChanged.connect(lambda value: setattr(self.rack, 'gain', value/100))
        layout.addWidget(self.level)
        self.status = QLabel('No instrument loaded. Effects belong in FX rack.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

    @property
    def rack(self):
        return self.owner.engine.instrument

    def refresh(self):
        name = self.parameter.currentText()
        self.parameter.clear()
        if self.rack.slots:
            self.parameter.addItems(sorted(self.rack.slots[0]['parameters']))
            self.parameter.setCurrentText(name)
        if self.pending:
            self.status.setText('Review saved instrument before Restore: '+(self.pending['effects'][0]['path'] if self.pending.get('effects') else 'empty instrument bus'))

    def select(self, name):
        if self.rack.slots and name in self.rack.slots[0]['parameters']:
            self.value.blockSignals(True)
            self.value.setValue(round(self.rack.slots[0]['parameters'][name]*1000))
            self.value.blockSignals(False)

    def file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose VST3 instrument', '', 'VST3 (*.vst3)')
        if path:
            self.load({'effects': [{'path': path}]})

    def bundle(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose .vst3 instrument bundle')
        if path:
            self.load({'effects': [{'path': path}]})

    def load(self, settings):
        self.native_operation(lambda: self.rack.restore(settings), clear=True)

    def native_operation(self, operation, clear=False, editor=False):
        if self.owner.engine.stream or self.owner.engine.external or self.task:
            self.status.setText('Stop audio/DAW receiver and wait for the current operation.')
            return
        self.marker = self.pending
        self.owner.arm.setChecked(False)
        self.task_clear, self.task_editor = clear, editor
        self.rack.ui_busy = True
        self.rack.editor_pending = editor
        self.status.setText('Native operation running in background. Close the editor before starting audio.' if editor
                            else 'Native instrument operation running in background...')
        self.task = BackgroundTask(operation)

    def open_editor(self):
        if self.rack.slots:
            self.owner.arm.setChecked(False)
            self.owner.motion_dialog.stop()
            self.native_operation(lambda: self.rack.show_editor(0), editor=True)

    def capture_state(self):
        self.native_operation(self.rack.capture_states)

    def poll(self):
        if self.task and self.task.done:
            error = self.task.error
            self.task = None
            self.rack.ui_busy = False
            self.rack.editor_pending = False
            if error:
                self.status.setText('Instrument load failed; previous configuration retained: '+error)
            else:
                if self.task_clear and self.pending is self.marker:
                    self.pending = None
                elif self.task_clear and self.pending is not None:
                    for slot in self.rack.slots:
                        slot['bypass'] = True
                self.refresh()
                self.status.setText('Instrument ready.' if self.rack.slots else 'Instrument removed.')

    def restore(self):
        if self.pending is not None:
            self.load(self.pending)

    def remove(self):
        self.load({'effects': []})

    def restart(self):
        self.load(self.rack.settings())

    def bind(self):
        if self.task or self.rack.loading:
            return
        name = self.parameter.currentText()
        if name:
            self.rack.bindings[str(self.knob.currentIndex()+1)] = {'slot': 0, 'parameter': name}
            self.status.setText('Choose '+self.knob.currentText()+' in Gesture mapping.')

    def set_value(self, value):
        if not self.task and not self.rack.loading:
            self.rack.set_parameter(0, self.parameter.currentText(), value/1000)

    def play(self, notes):
        if not self.owner.engine.stream and not self.owner.engine.external:
            self.status.setText('Start audio or the DAW audio receiver before playing.')
            return
        if not self.rack.play(notes):
            self.status.setText('Load a healthy instrument first.')
