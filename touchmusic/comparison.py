"""Audition the same bounded source phrase through two voice variants."""
from math import gcd
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QFileDialog)


class VoiceComparison(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle('Voice comparison lab')
        self.resize(760, 520)
        self.source = None
        self.job = None
        self.displayed = None
        self.files = []
        self.cache = tempfile.TemporaryDirectory(prefix='touchmusic-audition-', ignore_cleanup_errors=True)
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.output.setVolume(.5)
        self.player.setAudioOutput(self.output)
        layout = QVBoxLayout(self)
        hint = QLabel('Stop main audio and load the singing engine first. Choose a short phrase, then render A and B '
                      'on the same model worker. This compares references and quality settings, not trained models.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.source_label = QLabel('No source phrase selected')
        layout.addWidget(self.source_label)
        row = QHBoxLayout()
        self.button('Choose source audio', self.choose_source, row)
        self.start = QDoubleSpinBox()
        self.start.setRange(0, 3600)
        self.start.setSuffix(' s start')
        self.length = QDoubleSpinBox()
        self.length.setRange(1, 8)
        self.length.setValue(4)
        self.length.setSuffix(' s length')
        row.addWidget(self.start)
        row.addWidget(self.length)
        layout.addLayout(row)
        self.voices, self.qualities = [], []
        for name in ('A', 'B'):
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            voice, quality = QComboBox(), QComboBox()
            quality.addItems(['Live', 'Studio'])
            row.addWidget(voice, 1)
            row.addWidget(quality)
            self.voices.append(voice)
            self.qualities.append(quality)
            layout.addLayout(row)
        self.qualities[1].setCurrentText('Studio')
        row = QHBoxLayout()
        self.render = self.button('Render comparison', self.run, row)
        self.button('Cancel render', self.cancel, row)
        self.button('Stop preview', self.player.stop, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.devices = list(QMediaDevices.audioOutputs())
        self.device_combo = QComboBox()
        for device in self.devices:
            self.device_combo.addItem(device.description())
        self.device_combo.currentIndexChanged.connect(self.change_output)
        self.change_output(0)
        row.addWidget(QLabel('Preview output'))
        row.addWidget(self.device_combo, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.play_buttons = []
        for index, name in enumerate(('Dry source', 'A', 'B')):
            button = self.button('Play '+name, lambda _, i=index: self.play(i), row)
            button.setEnabled(False)
            self.play_buttons.append(button)
        self.button('Export A', lambda: self.export(0), row)
        self.button('Export B', lambda: self.export(1), row)
        layout.addLayout(row)
        self.status = QLabel('Choose one to eight seconds with a clear sung phrase.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.metrics = QLabel()
        self.metrics.setWordWrap(True)
        layout.addWidget(self.metrics)
        layout.addStretch()
        self.button('Done', self.hide, layout)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.poll)
        self.player.errorOccurred.connect(lambda _, message: self.status.setText('Preview error: '+message))

    @staticmethod
    def button(text, callback, row):
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)
        return button

    def showEvent(self, event):
        super().showEvent(event)
        selected_output = self.owner.outputs.currentText()
        default = QMediaDevices.defaultAudioOutput()
        preferred = next((index for index, device in enumerate(self.devices) if device.description() in selected_output),
                         next((index for index, device in enumerate(self.devices) if device.id() == default.id()), 0))
        self.device_combo.setCurrentIndex(preferred)
        for combo in self.voices:
            selected = combo.currentData()
            combo.clear()
            for voice in self.owner.voices:
                combo.addItem(voice['name'], voice['id'])
            combo.setCurrentIndex(max(0, combo.findData(selected)))
        self.timer.start()

    def hideEvent(self, event):
        self.player.stop()
        self.timer.stop()
        super().hideEvent(event)

    def change_output(self, index):
        if 0 <= index < len(self.devices):
            self.output.setDevice(self.devices[index])

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose source phrase', '', 'Audio (*.wav *.mp3 *.flac *.ogg)')
        if path:
            try:
                duration = sf.info(path).duration
                if duration < 1:
                    raise ValueError('Choose audio at least one second long.')
                self.source = path
                self.start.setRange(0, duration-1)
                self.source_label.setText(Path(path).name)
            except Exception as exc:
                self.status.setText(str(exc))

    def run(self):
        parent = self.owner
        if parent.engine.stream:
            self.status.setText('Stop main audio before rendering a comparison.')
            return
        try:
            if not self.source or not parent.engine.converter:
                raise ValueError('Choose source audio and load the singing engine first.')
            with sf.SoundFile(self.source) as source:
                rate = source.samplerate
                source.seek(round(self.start.value()*rate))
                audio = source.read(round(self.length.value()*rate), dtype='float32', always_2d=True).mean(axis=1)
            factor = gcd(rate, 48000)
            audio = resample_poly(audio, 48000//factor, rate//factor).astype(np.float32)
            variants = []
            for voice_combo, quality in zip(self.voices, self.qualities):
                voice = next((voice for voice in parent.voices if voice['id'] == voice_combo.currentData()), None)
                if voice is None:
                    raise ValueError('Select a voice for both variants.')
                variants.append((str(parent.library.path(voice)), quality.currentText()))
            self.job = parent.engine.converter.submit_audition(audio, variants)
            self.render.setEnabled(False)
            for button in self.play_buttons:
                button.setEnabled(False)
        except Exception as exc:
            self.status.setText(str(exc))

    def poll(self):
        if self.job is None:
            return
        self.status.setText(self.job.status)
        if self.job.done.is_set() and self.displayed is not self.job:
            self.displayed = self.job
            self.render.setEnabled(True)
            if self.job.error or not self.job.results:
                return
            self.player.stop()
            if not self.player.source().isEmpty():
                self.player.setSource(QUrl())
            self.cache.cleanup()
            self.cache = tempfile.TemporaryDirectory(prefix='touchmusic-audition-', ignore_cleanup_errors=True)
            self.files = []
            for index, audio in enumerate([self.job.audio, *[result['audio'] for result in self.job.results]]):
                path = Path(self.cache.name)/f'{index}.wav'
                sf.write(path, audio, 48000, subtype='FLOAT')
                self.files.append(path)
                self.play_buttons[index].setEnabled(True)
            self.metrics.setText('\n'.join(f'{name}: {result["quality"]}, {result["render_ms"]:.0f} ms render, '
                f'{result["rms_db"]:.1f} dBFS RMS, {result["near_full_scale"]:.1%} near full scale'
                for name, result in zip(('A', 'B'), self.job.results)))

    def cancel(self):
        if self.job and not self.job.done.is_set():
            self.job.cancel.set()
            self.status.setText('Cancellation requested; the current model chunk must finish.')

    def play(self, index):
        if index < len(self.files):
            self.player.setSource(QUrl.fromLocalFile(str(self.files[index])))
            self.player.play()

    def export(self, index):
        if not self.job or not self.job.done.is_set() or index >= len(self.job.results):
            self.status.setText('Render this variant first.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export comparison', f'voice-{index+1}.wav', 'WAV (*.wav)')
        if path:
            try:
                sf.write(path, self.job.results[index]['audio'], 48000, subtype='FLOAT')
                self.status.setText('Exported '+path)
            except Exception as exc:
                self.status.setText(str(exc))
