"""Host automation and timing controls with explicit opt-in."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton
from .bridge import LocalBridge, PORT
import time


class BridgeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.server = LocalBridge()
        self.setWindowTitle('VST3 control bridge')
        layout = QVBoxLayout(self)
        hint = QLabel('Load TouchMusic Control Bridge.vst3 on a DAW mixer insert, then enable the receiver here. '
            'The plugin passes DAW audio through unchanged and sends automation and timing over localhost. '
            'Processed TouchMusic audio still needs an audio route into the DAW. This is a control bridge, not the AI audio engine in a plugin.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.enabled = QCheckBox(f'Enable localhost receiver (127.0.0.1:{PORT})')
        self.enabled.toggled.connect(self.toggle)
        layout.addWidget(self.enabled)
        self.tempo = QCheckBox('Follow DAW tempo and musical position for scheduled actions')
        self.tempo.setChecked(True)
        self.automation = QCheckBox('Accept DAW automation for effects, voice slot and chord')
        self.transport = QCheckBox('Follow DAW play/stop and timeline position for backing track')
        for checkbox in (self.tempo, self.automation, self.transport):
            layout.addWidget(checkbox)
        self.status = QLabel('Receiver disabled. Each receiver follows one plugin instance at a time.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        reset = QPushButton('Forget current plugin instance')
        reset.clicked.connect(self.server.reset_source)
        layout.addWidget(reset)
        done = QPushButton('Done')
        done.clicked.connect(self.accept)
        layout.addWidget(done)
        layout.addStretch()

    def toggle(self, enabled):
        try:
            self.server.start() if enabled else self.server.close()
            self.status.setText('Waiting for the VST3 plugin.' if enabled else 'Receiver disabled.')
        except Exception as exc:
            self.enabled.blockSignals(True)
            self.enabled.setChecked(False)
            self.enabled.blockSignals(False)
            self.status.setText(str(exc))

    def poll(self):
        packet = self.server.consume()
        if not packet and self.server.socket and self.server.latest and time.monotonic()-self.server.latest['received_at'] > 1:
            self.status.setText('DAW signal is idle or disconnected. Waiting for new bridge packets.')
        if packet:
            self.status.setText(f'Connected: {packet["instance"]} | Tempo {packet.get("tempo")} | '
                f'Beat {packet.get("ppq")} | {"Playing" if packet["playing"] else "Stopped"} | '
                f'{self.server.packets} packets, {self.server.rejected} ignored')
            if packet['parameters'][9] < .5:
                self.owner.apply_bridge_packet(packet, self.tempo.isChecked(),
                                               self.automation.isChecked(), self.transport.isChecked())
