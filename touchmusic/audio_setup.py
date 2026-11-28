"""Guided standalone routing, device profiles and observable diagnostics."""
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QProgressBar, QPlainTextEdit, QFileDialog, QInputDialog, QApplication)
from .diagnostics import diagnostics_report


class AudioSetup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle('Audio setup and diagnostics')
        self.resize(760, 660)
        layout = QVBoxLayout(self)
        hint = QLabel('1. Choose the microphone and output. 2. Apply and start audio. '
                      '3. Speak and watch Input. 4. Test output with speaker volume low. '
                      'Use headphones for live monitoring. A test tone confirms playback only when you hear it.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.profiles = QComboBox()
        self.profiles.setPlaceholderText('Saved routing profiles')
        layout.addWidget(QLabel('Routing profile'))
        layout.addWidget(self.profiles)
        self.inputs, self.outputs = QComboBox(), QComboBox()
        self.inputs.currentIndexChanged.connect(self.refresh_outputs)
        for label, combo in [('Microphone', self.inputs), ('Output', self.outputs)]:
            layout.addWidget(QLabel(label))
            layout.addWidget(combo)
        row = QHBoxLayout()
        for label, callback in [('Refresh devices', self.refresh_devices), ('Load profile', self.load_profile),
                                ('Save profile', self.save_profile), ('Apply and start audio', self.apply_devices)]:
            self.button(label, callback, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.input_meter, self.output_meter = QProgressBar(), QProgressBar()
        for text, meter in [('Input', self.input_meter), ('Output', self.output_meter)]:
            meter.setRange(0, 100)
            meter.setTextVisible(False)
            row.addWidget(QLabel(text))
            row.addWidget(meter)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button('Play output test', self.test_output, row)
        self.heard = QCheckBox('I heard the test tone')
        row.addWidget(self.heard)
        self.button('Stop audio', self.stop_audio, row)
        layout.addLayout(row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.health = QLabel('Audio stopped. Choose devices, apply them, and speak to check the input meter.')
        self.health.setWordWrap(True)
        self.health.setStyleSheet('font-size: 18px; padding: 16px; background: #202b2b; color: #bfe4d8;')
        layout.addWidget(self.health)
        details = QCheckBox('Show technical report')
        layout.addWidget(details)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.hide()
        details.toggled.connect(self.report.setVisible)
        layout.addWidget(self.report, 1)
        row = QHBoxLayout()
        self.button('Copy report', self.copy_report, row)
        self.button('Export report', self.export_report, row)
        self.button('Done', self.accept, row)
        layout.addLayout(row)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh_status)

    @staticmethod
    def button(text, callback, row):
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_devices()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def refresh_devices(self):
        parent = self.owner
        if not parent.engine.stream:
            parent.refresh_devices()
        self.inputs.blockSignals(True)
        self.inputs.clear()
        for index in range(parent.inputs.count()):
            self.inputs.addItem(parent.inputs.itemText(index), parent.inputs.itemData(index))
        self.inputs.setCurrentIndex(self.inputs.findData(parent.inputs.currentData()))
        self.inputs.blockSignals(False)
        self.refresh_outputs()
        self.outputs.setCurrentIndex(self.outputs.findData(parent.outputs.currentData()))
        self.profiles.clear()
        self.profiles.addItems(sorted(parent.routing_profiles))
        self.heard.setChecked(False)
        self.refresh_status()

    def refresh_outputs(self, *_):
        self.outputs.clear()
        parent = self.owner
        device = self.inputs.currentData()
        if device is None:
            return
        host = parent.audio_devices[device]['hostapi']
        for index, entry in enumerate(parent.audio_devices):
            if entry['hostapi'] == host and entry['max_output_channels'] >= 2:
                api = parent.audio_apis[host]['name']
                self.outputs.addItem(f'{entry["name"]} ({api})', index)
        self.heard.setChecked(False)

    def apply_devices(self):
        parent = self.owner
        if self.inputs.currentData() is None or self.outputs.currentData() is None:
            self.status.setText('Choose an available microphone and output.')
            return
        if parent.engine.stream:
            self.status.setText('Stop audio before changing or reapplying devices.')
            return
        parent.inputs.setCurrentIndex(parent.inputs.findData(self.inputs.currentData()))
        parent.outputs.setCurrentIndex(parent.outputs.findData(self.outputs.currentData()))
        parent.toggle_audio()
        self.status.setText(parent.notice.text())

    def stop_audio(self):
        if self.owner.engine.stream:
            self.owner.toggle_audio()
        self.status.setText(self.owner.notice.text())

    def test_output(self):
        parent = self.owner
        if (self.inputs.currentData(), self.outputs.currentData()) != (parent.inputs.currentData(), parent.outputs.currentData()):
            self.status.setText('Apply the selected devices before testing output.')
            return
        self.heard.setChecked(False)
        parent.test_output()
        self.status.setText(parent.notice.text())

    def save_profile(self):
        name, accepted = QInputDialog.getText(self, 'Save routing profile', 'Profile name')
        if accepted and name.strip() and self.inputs.currentData() is not None and self.outputs.currentData() is not None:
            self.owner.routing_profiles[name.strip()] = {'input': self.inputs.currentText(), 'output': self.outputs.currentText()}
            self.owner.save_settings()
            self.profiles.clear()
            self.profiles.addItems(sorted(self.owner.routing_profiles))
            self.profiles.setCurrentText(name.strip())

    def load_profile(self):
        profile = self.owner.routing_profiles.get(self.profiles.currentText(), {})
        input_index = self.inputs.findText(profile.get('input', ''))
        if input_index < 0:
            self.status.setText('The saved microphone is unavailable. Reconnect it or choose another device.')
            return
        self.inputs.setCurrentIndex(input_index)
        output_index = self.outputs.findText(profile.get('output', ''))
        self.outputs.setCurrentIndex(output_index)
        self.status.setText('Profile selected. Apply when ready.' if output_index >= 0 else 'The saved output is unavailable.')

    def refresh_status(self):
        parent = self.owner
        self.input_meter.setValue(min(100, round(parent.engine.input_peak * 100)))
        self.output_meter.setValue(min(100, round(parent.engine.peak * 100)))
        report = diagnostics_report(parent.engine, parent.camera is not None)
        report.update(input_device=parent.inputs.currentText(), output_device=parent.outputs.currentText(),
                      output_confirmed_by_user=self.heard.isChecked(), recovery_error=parent.recovery.error)
        state = 'Audio running' if report['audio_running'] else 'Audio stopped'
        messages = [state, 'Output muted' if report['output_muted'] else 'Output enabled',
                    f'Audio status events: {report["audio_status_events"]}',
                    f'Input near-full-scale samples: {report["input_near_full_scale_samples"]}']
        if report['ai']:
            messages.append(report['ai']['status'])
            messages.append(f'AI dropped chunks: {report["ai"]["dropped"]}')
        if report['plugin_error']:
            messages.append('A plugin was bypassed: '+report['plugin_error'])
        if report['audio_error']:
            messages.append('Audio error: '+report['audio_error'])
        self.health.setText('\n'.join(messages))
        self.report.setPlainText(json.dumps(report, indent=2))

    def copy_report(self):
        self.refresh_status()
        QApplication.clipboard().setText(self.report.toPlainText())

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export diagnostics', 'touchmusic-diagnostics.json', 'JSON (*.json)')
        if path:
            try:
                from pathlib import Path
                self.refresh_status()
                Path(path).write_text(self.report.toPlainText(), encoding='utf-8')
                self.status.setText('Report saved. It contains device names and runtime counters.')
            except Exception as exc:
                self.status.setText(str(exc))
