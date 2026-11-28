"""Large performance controls backed by the existing main-window state."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QProgressBar


class StageView(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('TouchMusic stage view')
        self.resize(1100, 680)
        layout = QVBoxLayout(self)
        self.voice = QLabel()
        self.voice.setWordWrap(True)
        self.voice.setStyleSheet('font-size: 38px; font-weight: 700; color: #a3e8d1;')
        layout.addWidget(self.voice)
        self.music = QLabel()
        self.music.setStyleSheet('font-size: 26px;')
        self.music.setWordWrap(True)
        layout.addWidget(self.music)
        self.state = QLabel()
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self.action = QLabel()
        self.action.setWordWrap(True)
        layout.addWidget(self.action)
        grid = QGridLayout()
        self.pads, self.progress = [], []
        for index in range(4):
            column = QVBoxLayout()
            pad = self.button('', lambda _, i=index: parent.loop_command('loop', i), column)
            pad.setMinimumHeight(85)
            pad.setStyleSheet('font-size: 21px; padding: 12px;')
            pad.setCheckable(False)
            self.pads.append(pad)
            progress = QProgressBar()
            progress.setRange(0, 1000)
            progress.setTextVisible(False)
            self.progress.append(progress)
            column.addWidget(progress)
            mute = self.button('Toggle loop mute', lambda _, i=index: parent.loop_command('mute', i), column)
            mute.setAccessibleName(f'Toggle loop {index+1} mute')
            grid.addLayout(column, index // 2, index % 2)
        layout.addLayout(grid, 1)
        row = QHBoxLayout()
        self.button('Previous voice', lambda: parent.gesture_action('Previous voice'), row)
        self.button('Next voice', lambda: parent.gesture_action('Next voice'), row)
        self.record = self.button('Record performance', parent.toggle_recording, row)
        self.monitor = self.button('Mute output', parent.mute_button.click, row)
        self.button('Emergency mute (F12)', parent.emergency_mute, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button('Previous song', lambda: parent.setlist_dialog.step(-1), row)
        self.button('Next song', lambda: parent.setlist_dialog.step(1), row)
        self.button('Fullscreen (F11)', self.toggle_fullscreen, row)
        self.button('Back to controls', self.hide, row)
        layout.addLayout(row)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)

    @staticmethod
    def button(text, callback, row):
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)
        return button

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Space:
            self.parent().mute_button.click()
        else:
            super().keyPressEvent(event)

    def refresh(self):
        parent = self.parent()
        voice = parent.current_voice()
        active = parent.ai.isChecked()
        self.voice.setText(voice['name'] if voice and active else 'Your voice')
        self.music.setText(parent.stage_music_text())
        audio = 'Audio on' if parent.engine.stream else 'Audio off'
        conversion = 'AI on' if active else 'AI off'
        reference = f' | Selected: {voice["name"]}' if voice and not active else ''
        self.state.setText(('OUTPUT MUTED | ' if parent.engine.muted else '') + audio + ' | ' + conversion
                           + reference + ' | ' + parent.pitch_status.text() + ' | ' + parent.tracking.text())
        self.action.setText(parent.gesture_preview.text())
        self.notice.setText(parent.notice.text())
        self.record.setText(parent.record_button.text())
        self.monitor.setText(parent.mute_button.text())
        for index, pad in enumerate(self.pads):
            pad.setText(parent.loop_pads[index].text())
            pad.setProperty('loopState', parent.loop_pads[index].property('loopState'))
            pad.style().unpolish(pad)
            pad.style().polish(pad)
            self.progress[index].setValue(parent.loop_progress[index].value())
