"""Draggable reference selection on a zoomable waveform."""
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


def time_label(seconds):
    minutes, seconds = divmod(max(0., seconds), 60)
    return f'{int(minutes):02d}:{seconds:05.2f}'


class Waveform(QWidget):
    selectionChanged = Signal(float, float)
    seekRequested = Signal(float)
    viewChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self.setAccessibleName('Voice reference waveform with draggable selection')
        self.setToolTip('Drag the highlighted section or either edge. Click outside to seek. Scroll to zoom.')
        self.duration = 0.
        self.peaks = np.empty((0, 2), np.float32)
        self.start = self.end = self.position = self.view_start = 0.
        self.view_seconds = 20.
        self.dragging = None

    def set_audio(self, duration, peaks):
        self.duration, self.peaks = duration, peaks
        self.view_start = 0.
        self.view_seconds = min(duration, 20.)
        self.set_selection(0., min(8., duration))

    def set_selection(self, start, end):
        maximum = min(8., self.duration)
        length = min(maximum, max(1., end - start))
        self.start = max(0., min(start, self.duration - length))
        self.end = self.start + length
        self.update()
        self.selectionChanged.emit(self.start, self.end)

    def scroll_to(self, seconds):
        self.view_start = max(0., min(seconds, self.duration - self.view_seconds))
        self.update()

    def zoom(self, factor):
        center = self.view_start + self.view_seconds * .5
        self.view_seconds = min(self.duration, max(min(8., self.duration), self.view_seconds * factor))
        self.scroll_to(center - self.view_seconds * .5)
        self.viewChanged.emit()

    def show_selection(self):
        if self.start < self.view_start or self.end > self.view_start + self.view_seconds:
            self.scroll_to((self.start + self.end - self.view_seconds) * .5)
            self.viewChanged.emit()

    def x_at(self, seconds):
        return 12 + (self.width() - 24) * (seconds - self.view_start) / max(.001, self.view_seconds)

    def time_at(self, x):
        value = self.view_start + (x - 12) / max(1, self.width() - 24) * self.view_seconds
        return max(0., min(self.duration, value))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#101619'))
        if not self.duration:
            painter.setPen(QColor('#aabbb6'))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Loading waveform…')
            return
        left, right = self.x_at(self.start), self.x_at(self.end)
        painter.fillRect(round(left), 24, round(right-left), self.height()-50, QColor('#20483e'))
        center, amplitude = self.height() * .5, (self.height() - 72) * .5
        painter.setPen(QPen(QColor('#82c8b0'), 1))
        step = max(1, round(len(self.peaks) * self.view_seconds / self.duration / max(1, self.width())))
        first = int(self.view_start / self.duration * len(self.peaks))
        last = min(len(self.peaks), int((self.view_start + self.view_seconds) / self.duration * len(self.peaks)) + 1)
        for index in range(first, last, step):
            chunk = self.peaks[index:min(index+step, last)]
            x = round(self.x_at(index / len(self.peaks) * self.duration))
            painter.drawLine(x, round(center - chunk[:, 1].max() * amplitude),
                             x, round(center - chunk[:, 0].min() * amplitude))
        painter.setPen(QPen(QColor('#b1f1d8'), 2))
        for x in (left, right):
            if 0 <= x < self.width():
                painter.drawLine(round(x), 25, round(x), self.height()-28)
                painter.fillRect(round(x)-4, 26, 8, 20, QColor('#b1f1d8'))
        x = self.x_at(self.position)
        if 0 <= x < self.width():
            painter.setPen(QPen(QColor('#e9bc75'), 2))
            painter.drawLine(round(x), 24, round(x), self.height()-28)
        painter.setPen(QColor('#aabbb6'))
        for tick in range(5):
            seconds = self.view_start + self.view_seconds * tick / 4
            x = min(self.width()-75, max(8, round(self.x_at(seconds))))
            painter.drawText(x, self.height()-8, time_label(seconds))
        painter.drawText(12, 17, 'Drag selection or its edges · scroll to zoom')

    def mousePressEvent(self, event):
        if not self.duration or event.button() != Qt.LeftButton:
            return
        x = event.position().x()
        if abs(x - self.x_at(self.start)) <= 10:
            self.dragging = 'start'
        elif abs(x - self.x_at(self.end)) <= 10:
            self.dragging = 'end'
        elif self.start <= self.time_at(x) <= self.end:
            self.dragging = 'move'
        else:
            self.seekRequested.emit(self.time_at(x))
            return
        self.drag_origin = self.time_at(x), self.start, self.end

    def mouseMoveEvent(self, event):
        if not self.duration:
            return
        x = event.position().x()
        if self.dragging:
            time = self.time_at(x)
            _, start, end = self.drag_origin
            if self.dragging == 'move':
                self.set_selection(start + time - self.drag_origin[0], end + time - self.drag_origin[0])
            elif self.dragging == 'start':
                self.set_selection(max(end - 8., min(end - 1., time)), end)
            else:
                self.set_selection(start, min(self.duration, start + 8., max(start + 1., time)))
        else:
            near = min(abs(x-self.x_at(self.start)), abs(x-self.x_at(self.end))) <= 10
            inside = self.start <= self.time_at(x) <= self.end
            self.setCursor(Qt.SizeHorCursor if near else Qt.OpenHandCursor if inside else Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        self.dragging = None

    def wheelEvent(self, event):
        if self.duration:
            self.zoom(.8 if event.angleDelta().y() > 0 else 1.25)
        event.accept()
