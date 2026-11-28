"""A separate opt-in audio receiver so the existing control bridge stays compatible."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton
from .audio_bridge import AudioBridge


class AudioBridgeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.server = AudioBridge(parent.engine)
        layout = QVBoxLayout(self)
        hint = QLabel('Experimental live audio return: load TouchMusic Audio Bridge.vst3 on a DAW insert at '
            '48 kHz, stop standalone audio, then enable this receiver. DAW input is processed by TouchMusic '
            'and returned in stereo, including AI when its model is ready and enabled. No virtual cable is required. '
            'The plugin adds/reports 4096 transport frames (85.3 ms). AI, FX and instrument worker delays are additional '
            'and are not yet included in DAW latency compensation. Offline fast rendering is not supported. '
            'Do not enable a second microphone monitoring route.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.enabled = QCheckBox('Enable DAW audio receiver on 127.0.0.1:26790')
        self.enabled.toggled.connect(self.toggle)
        layout.addWidget(self.enabled)
        button = QPushButton('Forget current audio plugin instance')
        button.clicked.connect(lambda: setattr(self.server, 'active', None))
        layout.addWidget(button)
        self.status = QLabel('Disabled. The Control Bridge remains a separate automation/timing plugin.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

    def toggle(self, enabled):
        try:
            if enabled:
                self.server.start()
            elif not self.server.close():
                raise RuntimeError(self.server.error)
            self.status.setText('Waiting for 48 kHz DAW audio.' if enabled else 'Disabled.')
        except Exception as exc:
            self.enabled.blockSignals(True)
            self.enabled.setChecked(bool(self.server.socket))
            self.enabled.blockSignals(False)
            self.status.setText(str(exc))

    def poll(self):
        if self.server.socket:
            self.status.setText(f'{self.server.packets} returned blocks | {self.server.gaps} missing input blocks | '
                                f'{self.server.rejected} rejected | '+(self.server.error or '48 kHz, stereo return'))
