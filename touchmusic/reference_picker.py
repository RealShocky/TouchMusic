"""Listen to a full recording and choose the short reference used by the model."""
from pathlib import Path
from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollBar, QSlider, QVBoxLayout)
from .waveform import Waveform, time_label
from .reference_quality import analyze_reference


class WaveformLoader(QThread):
    loaded = Signal(float, object)
    qualityLoaded = Signal(object)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            result = analyze_reference(self.path, self.isInterruptionRequested)
            if result is not None and not self.isInterruptionRequested():
                duration, peaks, quality = result
                self.loaded.emit(duration, peaks)
                self.qualityLoaded.emit(quality)
        except Exception as exc:
            self.failed.emit(str(exc))


class ReferencePicker(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.setWindowTitle('Choose voice reference')
        self.resize(900, 560)
        self.ready = False
        self.closing = False
        self.quality = None
        self.candidate_index = -1
        self.preview_selection = False
        self.pending_play = False
        self.song_pending = False
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(.6)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.position_changed)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(lambda error, text: self.status.setText('Preview unavailable. ' + text))
        layout = QVBoxLayout(self)
        title = QLabel(self.path.name)
        title.setWordWrap(True)
        title.setStyleSheet('font-size: 20px; font-weight: 600;')
        layout.addWidget(title)
        hint = QLabel('Listen to the track, then choose 1–8 seconds of clear solo vocals for the character voice.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.waveform = Waveform()
        self.waveform.selectionChanged.connect(self.selection_changed)
        self.waveform.seekRequested.connect(self.seek)
        self.waveform.viewChanged.connect(self.update_scroll)
        layout.addWidget(self.waveform, 1)
        self.scroll = QScrollBar(Qt.Horizontal)
        self.scroll.setAccessibleName('Scroll waveform through the song')
        self.scroll.valueChanged.connect(lambda ms: self.waveform.scroll_to(ms / 1000))
        layout.addWidget(self.scroll)
        seek_row = QHBoxLayout()
        self.position_label = QLabel('00:00.00')
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setAccessibleName('Seek through the full song')
        self.timeline.setRange(0, 0)
        self.timeline.sliderMoved.connect(lambda ms: self.seek(ms / 1000))
        self.duration_label = QLabel()
        seek_row.addWidget(self.position_label)
        seek_row.addWidget(self.timeline, 1)
        seek_row.addWidget(self.duration_label)
        layout.addLayout(seek_row)
        playback = QHBoxLayout()
        self.play_button = self.button('Play song', self.play_song, playback)
        self.selection_button = self.button('Play selection', self.play_selection, playback)
        self.button('Use playhead as start', self.use_playhead, playback)
        self.loop_preview = QCheckBox('Loop selection')
        playback.addWidget(self.loop_preview)
        playback.addStretch()
        self.button('Zoom in', lambda: self.waveform.zoom(.7), playback)
        self.button('Zoom out', lambda: self.waveform.zoom(1.4), playback)
        layout.addLayout(playback)
        selection = QHBoxLayout()
        self.start = self.time_spin('Selection start in seconds')
        self.length = self.time_spin('Selection length in seconds')
        self.length.setRange(1, 8)
        self.start.valueChanged.connect(self.update_selection)
        self.length.valueChanged.connect(self.update_selection)
        selection.addWidget(QLabel('Start'))
        selection.addWidget(self.start)
        selection.addWidget(QLabel('Length'))
        selection.addWidget(self.length)
        self.section_label = QLabel()
        selection.addWidget(self.section_label, 1)
        layout.addLayout(selection)
        suggestions = QHBoxLayout()
        self.suggest_button = self.button('Suggest section', self.suggest_section, suggestions)
        self.next_button = self.button('Next suggestion', self.next_suggestion, suggestions)
        self.suggestion_label = QLabel('Checking recording levels.')
        self.suggestion_label.setWordWrap(True)
        suggestions.addWidget(self.suggestion_label, 1)
        layout.addLayout(suggestions)
        self.quality_label = QLabel('Selection quality is being checked.')
        self.quality_label.setWordWrap(True)
        layout.addWidget(self.quality_label)
        quality_hint = QLabel('Suggestions use level, silence, and clipping checks. Listen for clear solo vocals.')
        quality_hint.setWordWrap(True)
        layout.addWidget(quality_hint)
        self.suggest_button.setEnabled(False)
        self.next_button.setEnabled(False)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Voice name'))
        self.name = QLineEdit(self.path.stem.replace('_', ' '))
        name_row.addWidget(self.name, 1)
        layout.addLayout(name_row)
        outputs = QHBoxLayout()
        outputs.addWidget(QLabel('Preview output'))
        self.outputs = QComboBox()
        self.devices = QMediaDevices.audioOutputs()
        default = QMediaDevices.defaultAudioOutput()
        for device in self.devices:
            self.outputs.addItem(device.description())
        selected = next((i for i, device in enumerate(self.devices) if device.id() == default.id()), -1)
        self.outputs.setCurrentIndex(selected)
        self.outputs.currentIndexChanged.connect(self.change_output)
        outputs.addWidget(self.outputs, 1)
        outputs.addWidget(QLabel('Volume'))
        volume = QSlider(Qt.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(60)
        volume.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        outputs.addWidget(volume)
        layout.addLayout(outputs)
        self.status = QLabel('Reading audio and building waveform…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.button('Cancel', self.reject, buttons)
        self.use_button = self.button('Use this section', self.accept, buttons)
        self.use_button.setDefault(True)
        layout.addLayout(buttons)
        self.use_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.selection_button.setEnabled(False)
        self.loader = WaveformLoader(self.path, self)
        self.loader.loaded.connect(self.loaded)
        self.loader.qualityLoaded.connect(self.quality_loaded)
        self.loader.failed.connect(self.status.setText)
        self.loader.start()

    @staticmethod
    def button(label, callback, layout):
        button = QPushButton(label)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    @staticmethod
    def time_spin(label):
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setSingleStep(.1)
        spin.setSuffix(' s')
        spin.setAccessibleName(label)
        return spin

    def loaded(self, duration, peaks):
        if self.closing:
            return
        self.ready = True
        self.start.setRange(0, max(0, duration - 1))
        self.length.setMaximum(min(8, duration))
        self.waveform.set_audio(duration, peaks)
        self.timeline.setRange(0, int(duration * 1000))
        self.duration_label.setText(time_label(duration))
        self.update_scroll()
        self.play_button.setEnabled(True)
        self.selection_button.setEnabled(True)
        self.use_button.setEnabled(True)
        self.status.setText('Drag the green section or its edges. Use the full-track slider to find another part.')

    def quality_loaded(self, quality):
        if self.closing:
            return
        self.quality = quality
        available = bool(quality.candidates)
        self.suggest_button.setEnabled(available)
        self.next_button.setEnabled(len(quality.candidates) > 1)
        self.suggestion_label.setText(f'{len(quality.candidates)} sections suggested.' if available else
                                     'No section passed the level checks. Choose a section manually.')
        self.update_quality()

    def update_quality(self):
        if self.quality is not None:
            self.quality_label.setText(self.quality.report(self.waveform.start, self.waveform.end).text())

    def suggest_section(self):
        self.candidate_index = -1
        self.next_suggestion()

    def next_suggestion(self):
        if self.quality is None or not self.quality.candidates:
            return
        self.candidate_index = (self.candidate_index + 1) % len(self.quality.candidates)
        start, end = self.quality.candidates[self.candidate_index]
        self.waveform.set_selection(start, end)
        self.waveform.show_selection()
        self.suggestion_label.setText(f'Suggestion {self.candidate_index + 1} of {len(self.quality.candidates)}. '
                                     'Preview this section before using it.')

    def update_scroll(self):
        self.scroll.blockSignals(True)
        self.scroll.setRange(0, max(0, round((self.waveform.duration - self.waveform.view_seconds) * 1000)))
        self.scroll.setPageStep(round(self.waveform.view_seconds * 1000))
        self.scroll.setValue(round(self.waveform.view_start * 1000))
        self.scroll.blockSignals(False)

    def selection_changed(self, start, end):
        for widget, value in ((self.start, start), (self.length, end-start)):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.section_label.setText(f'{time_label(start)} – {time_label(end)}')
        self.update_quality()
        if self.preview_selection and self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.setPosition(round(start * 1000))

    def update_selection(self):
        self.waveform.set_selection(self.start.value(), self.start.value() + self.length.value())
        self.waveform.show_selection()

    def seek(self, seconds):
        self.preview_selection = False
        if not self.player.source().isEmpty():
            self.player.setPosition(round(seconds * 1000))
        self.waveform.position = seconds
        if seconds < self.waveform.view_start or seconds > self.waveform.view_start + self.waveform.view_seconds:
            self.waveform.scroll_to(seconds - self.waveform.view_seconds * .5)
            self.update_scroll()
        self.waveform.update()

    def use_playhead(self):
        if self.ready:
            start = min(self.waveform.position, self.waveform.duration - 1)
            length = min(8, self.waveform.duration - start)
            self.waveform.set_selection(start, start + length)
            self.waveform.show_selection()

    def play_song(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.ready:
            self.preview_selection = False
            self.pending_play = False
            if self.player.source().isEmpty():
                self.song_pending = True
                self.player.setSource(QUrl.fromLocalFile(str(self.path.resolve())))
                return
            if self.player.position() >= round(self.waveform.duration * 1000) - 50:
                self.player.setPosition(0)
            self.player.play()

    def play_selection(self):
        if self.ready:
            self.song_pending = False
            if self.player.source().isEmpty():
                self.pending_play = True
                self.player.setSource(QUrl.fromLocalFile(str(self.path.resolve())))
                return
            if self.player.mediaStatus() in (QMediaPlayer.LoadingMedia, QMediaPlayer.NoMedia):
                self.pending_play = True
                self.player.play()
                return
            self.pending_play = False
            self.preview_selection = True
            self.player.setPosition(round(self.waveform.start * 1000))
            self.player.play()

    def position_changed(self, position):
        if self.preview_selection and position >= round(self.waveform.end * 1000):
            self.preview_selection = False
            if self.loop_preview.isChecked():
                QTimer.singleShot(0, self.play_selection)
            else:
                self.player.pause()
            return
        self.waveform.position = position / 1000
        self.waveform.update()
        self.position_label.setText(time_label(position / 1000))
        if not self.timeline.isSliderDown():
            self.timeline.setValue(position)

    def media_status(self, status):
        if self.closing:
            return
        if self.song_pending and status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self.song_pending = False
            self.player.setPosition(round(self.waveform.position * 1000))
            self.player.play()
        elif self.pending_play and status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            QTimer.singleShot(0, self.play_selection)
        elif status == QMediaPlayer.EndOfMedia and self.preview_selection and self.loop_preview.isChecked():
            QTimer.singleShot(0, self.play_selection)

    def playback_changed(self, state):
        self.play_button.setText('Pause' if state == QMediaPlayer.PlayingState else 'Play song')

    def change_output(self, index):
        if 0 <= index < len(self.devices):
            self.audio_output.setDevice(self.devices[index])

    def done(self, result):
        if result == QDialog.Accepted and (not self.ready or not self.name.text().strip()):
            self.status.setText('Enter a voice name before using this section.')
            return
        self.preview_selection = False
        self.pending_play = False
        self.song_pending = False
        self.ready = False
        self.closing = True
        self.player.stop()
        if not self.player.source().isEmpty():
            self.player.setSource(QUrl())
        self.loader.requestInterruption()
        self.loader.wait()
        super().done(result)
