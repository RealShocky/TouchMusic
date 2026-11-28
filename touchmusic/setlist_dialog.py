"""An ordered performance list of portable skit files."""
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel,
    QListWidget, QMessageBox, QPushButton, QVBoxLayout)
from .sessions import Setlist


class SetlistDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.model = Setlist()
        self.path = None
        self.dirty = False
        self.setWindowTitle('TouchMusic setlist')
        self.resize(620, 470)
        layout = QVBoxLayout(self)
        text = QLabel('Save performances as skits, then arrange them in playing order. Opening a song stops audio '
                      'and disarms gestures so you can check the restored setup.')
        text.setWordWrap(True)
        layout.addWidget(text)
        self.songs = QListWidget()
        self.songs.itemDoubleClicked.connect(lambda _: self.open_selected())
        layout.addWidget(self.songs, 1)
        row = QHBoxLayout()
        for label, callback in [('Add skits', self.add), ('Remove', self.remove),
                                ('Move up', lambda: self.move(-1)), ('Move down', lambda: self.move(1))]:
            self.button(label, callback, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        for label, callback in [('Previous song', lambda: self.step(-1)), ('Open selected', self.open_selected),
                                ('Next song', lambda: self.step(1))]:
            self.button(label, callback, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button('Open setlist', self.open_list, row)
        self.button('Save setlist', self.save_list, row)
        self.button('Done', self.accept, row)
        layout.addLayout(row)
        self.status = QLabel('Empty setlist')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    @staticmethod
    def button(label, callback, layout):
        button = QPushButton(label)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def refresh(self, selected=None):
        self.songs.clear()
        for index, path in enumerate(self.model.paths):
            marker = '  ·  current' if index == self.model.index else ''
            self.songs.addItem(f'{index+1}.  {path.stem}{marker}')
            self.songs.item(index).setToolTip(str(path))
        self.songs.setCurrentRow(self.model.index if selected is None else selected)
        title = self.path.name if self.path else 'Unsaved setlist'
        self.status.setText(f'{title} · {len(self.model.paths)} songs' + (' · modified' if self.dirty else ''))

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add skits to setlist', '', 'TouchMusic skits (*.touchmusic)')
        try:
            for path in paths:
                self.model.add(path)
            self.dirty |= bool(paths)
            self.refresh()
        except Exception as exc:
            self.status.setText(str(exc))

    def remove(self):
        row = self.songs.currentRow()
        if row >= 0:
            self.model.remove(row)
            self.dirty = True
            self.refresh()

    def move(self, direction):
        row = self.songs.currentRow()
        target = row + direction
        if 0 <= target < len(self.model.paths) and row >= 0:
            self.model.move(row, target)
            self.dirty = True
            self.refresh(target)

    def open_selected(self):
        row = self.songs.currentRow()
        if row >= 0:
            self.open_index(row)

    def open_index(self, index):
        path = self.model.paths[index]
        if self.owner.load_skit_path(path):
            self.model.select(index)
            self.refresh()
            return True
        self.status.setText(self.owner.notice.text())
        return False

    def step(self, direction):
        if self.model.paths:
            index = max(0, min(len(self.model.paths)-1, self.model.index + direction))
            self.open_index(index)
        else:
            self.owner.notice.setText('Add saved skits in Session > Setlist first.')

    def open_list(self):
        if self.dirty:
            choice = QMessageBox.question(self, 'Modified setlist', 'Save this setlist before opening another?',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if choice == QMessageBox.Cancel:
                return
            if choice == QMessageBox.Save:
                self.save_list()
                if self.dirty:
                    return
        path, _ = QFileDialog.getOpenFileName(self, 'Open setlist', '', 'TouchMusic setlists (*.tmsetlist)')
        if path:
            self.load_list(path)

    def load_list(self, path):
        try:
            model = Setlist.load(path)
            self.model, self.path, self.dirty = model, Path(path), False
            self.refresh()
        except Exception as exc:
            self.status.setText(str(exc))

    def save_list(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save setlist', str(self.path or 'Performance.tmsetlist'),
                                              'TouchMusic setlists (*.tmsetlist)')
        if path:
            if not path.lower().endswith('.tmsetlist'):
                path += '.tmsetlist'
            try:
                self.model.save(path)
                self.path, self.dirty = Path(path), False
                self.refresh()
                self.owner.save_settings()
            except Exception as exc:
                self.status.setText(str(exc))
