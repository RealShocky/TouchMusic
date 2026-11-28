"""MIDI connection controls for DAWs such as FL Studio."""
from PySide6.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout)


class MidiDialog(QDialog):
    def __init__(self, output, settings, parent=None):
        super().__init__(parent)
        self.output = output
        self.preferred = settings.get('port', '')
        self.setWindowTitle('MIDI / FL Studio')
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        text = QLabel('Create a virtual MIDI port in loopMIDI, select it here, then enable the same port '
                      'as an input in FL Studio. Link a knob to a gesture MIDI CC or play an instrument with note poses.')
        text.setWordWrap(True)
        layout.addWidget(text)
        grid = QGridLayout()
        self.ports = QComboBox()
        grid.addWidget(QLabel('Output port'), 0, 0)
        grid.addWidget(self.ports, 0, 1)
        refresh = QPushButton('Refresh ports')
        refresh.clicked.connect(self.refresh)
        grid.addWidget(refresh, 0, 2)
        self.channel = QSpinBox()
        self.channel.setRange(1, 16)
        self.channel.setValue(settings.get('channel', 1))
        self.channel.valueChanged.connect(self.reconnect)
        grid.addWidget(QLabel('MIDI channel'), 1, 0)
        grid.addWidget(self.channel, 1, 1)
        self.velocity = QSpinBox()
        self.velocity.setRange(1, 127)
        self.velocity.setValue(settings.get('velocity', 100))
        grid.addWidget(QLabel('Note velocity'), 2, 0)
        grid.addWidget(self.velocity, 2, 1)
        self.length = QSpinBox()
        self.length.setRange(50, 10000)
        self.length.setSingleStep(50)
        self.length.setSuffix(' ms')
        self.length.setValue(settings.get('note_ms', 500))
        grid.addWidget(QLabel('Note length'), 3, 0)
        grid.addWidget(self.length, 3, 1)
        layout.addLayout(grid)
        self.status = QLabel('Disconnected')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.connect_button = QPushButton('Connect MIDI')
        self.connect_button.setCheckable(True)
        self.connect_button.clicked.connect(self.connect_port)
        row.addWidget(self.connect_button)
        test = QPushButton('Test C4')
        test.clicked.connect(lambda: self.output.play([60], self.velocity.value(), self.length.value() / 1000))
        row.addWidget(test)
        panic = QPushButton('All notes off')
        panic.clicked.connect(self.output.panic)
        row.addWidget(panic)
        layout.addLayout(row)
        mapping = QPushButton('Map hand heights to CC 1 / 74')
        mapping.clicked.connect(self.map_defaults)
        layout.addWidget(mapping)
        done = QPushButton('Done')
        done.clicked.connect(self.accept)
        layout.addWidget(done)
        self.ports.currentTextChanged.connect(self.port_changed)

    def refresh(self):
        selected = self.ports.currentText() or self.preferred
        try:
            ports = self.output.ports()
            self.ports.blockSignals(True)
            self.ports.clear()
            self.ports.addItems(ports)
            self.ports.setCurrentIndex(max(0, self.ports.findText(selected)))
            self.ports.blockSignals(False)
            if not ports:
                self.status.setText('No MIDI output ports. Create a virtual port in loopMIDI, then refresh.')
        except Exception as exc:
            self.status.setText(str(exc))

    def port_changed(self, name):
        self.preferred = name
        if self.output.backend:
            self.connect_port(True)

    def reconnect(self):
        if self.output.backend:
            self.connect_port(True)

    def connect_port(self, active):
        try:
            if active:
                self.output.connect(self.ports.currentText(), self.channel.value())
            else:
                self.output.close()
        except Exception as exc:
            self.status.setText(str(exc))
        self.update_status()

    def update_status(self):
        connected = self.output.backend is not None
        self.connect_button.setChecked(connected)
        self.connect_button.setText('Disconnect MIDI' if connected else 'Connect MIDI')
        self.ports.setEnabled(not connected)
        if connected:
            self.status.setText(f'Connected to {self.output.port} · Channel {self.output.channel}')
        elif self.output.error:
            self.status.setText(self.output.error)

    def map_defaults(self):
        self.parent().mappings['Left'].setCurrentText('MIDI CC 1')
        self.parent().mappings['Right'].setCurrentText('MIDI CC 74')
        self.status.setText('Left height sends CC 1. Right height sends CC 74. Arm gestures to send.')

    def settings(self):
        return {'port': self.ports.currentText() or self.preferred, 'channel': self.channel.value(),
                'velocity': self.velocity.value(), 'note_ms': self.length.value()}

    def apply_settings(self, settings):
        port = settings.get('port')
        if isinstance(port, str):
            self.preferred = port
        for name, key in (('channel', 'channel'), ('velocity', 'velocity'), ('length', 'note_ms')):
            value = settings.get(key)
            if type(value) is int:
                getattr(self, name).setValue(value)
