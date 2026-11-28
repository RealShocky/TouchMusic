"""Instrument loading is explicit; saved native instruments never auto-load."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QSlider, QFileDialog)


class InstrumentDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
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
        self.parameter = QComboBox()
        self.parameter.currentTextChanged.connect(self.select)
        layout.addWidget(self.parameter)
        self.value = QSlider(Qt.Horizontal)
        self.value.setRange(0, 1000)
        self.value.valueChanged.connect(lambda value: self.rack.set_parameter(0, self.parameter.currentText(), value/1000))
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
        if self.owner.engine.stream or self.owner.engine.external:
            self.status.setText('Stop audio and the DAW audio receiver first.')
            return
        try:
            self.rack.restore(settings)
            self.pending = None
            self.refresh()
            self.status.setText('Loaded: '+Path(self.rack.slots[0]['path']).name if self.rack.slots else 'Instrument removed.')
        except Exception as exc:
            self.status.setText(str(exc))

    def restore(self):
        if self.pending is not None:
            self.load(self.pending)

    def remove(self):
        self.load({'effects': []})

    def restart(self):
        self.load(self.rack.settings())

    def bind(self):
        name = self.parameter.currentText()
        if name:
            self.rack.bindings[str(self.knob.currentIndex()+1)] = {'slot': 0, 'parameter': name}
            self.status.setText('Choose '+self.knob.currentText()+' in Gesture mapping.')

    def play(self, notes):
        if not self.owner.engine.stream and not self.owner.engine.external:
            self.status.setText('Start audio or the DAW audio receiver before playing.')
            return
        if not self.rack.play(notes):
            self.status.setText('Load a healthy instrument first.')
