"""VST3 effects, generic controls, and eight gesture parameter bindings."""
from pathlib import Path
import threading
import time
from .gesture_learn import GestureLearner
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QComboBox, QSlider, QFileDialog, QInputDialog, QMenu)


class PluginDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle('VST3 effect rack')
        self.resize(760, 580)
        self.pending = None
        self.learner = None
        self.learn_binding = None
        self.editor_task = None
        self.editor_error = ''
        layout = QVBoxLayout(self)
        hint = QLabel('Four audio effects, processed in list order after built-in vocal effects. Stereo effect output '
                      'is preserved at the output. Isolated hosting adds 2048 frames (42.7 ms at 48 kHz). '
                      'Stop audio before loading, removing, or reordering plugins. '
                      'Install plugins yourself; saved skits never load native plugins automatically.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        downloads = QPushButton('Get free effects from their publishers')
        menu = QMenu(downloads)
        for name, url in [('TDR Nova: dynamic EQ', 'https://www.tokyodawn.net/tdr-nova/free/'),
                          ('Valhalla Supermassive: delay / reverb', 'https://valhalladsp.com/shop/reverb/valhalla-supermassive/'),
                          ('Melda MFreeFXBundle', 'https://www.meldaproduction.com/MFreeFXBundle')]:
            menu.addAction(name, lambda checked=False, link=url: QDesktopServices.openUrl(QUrl(link)))
        downloads.setMenu(menu)
        layout.addWidget(downloads)
        self.button('Plugin Center: discover, scan and download',
                    lambda: self.owner.workspaces.open('Plugin Center'), layout)
        self.effects = QListWidget()
        self.effects.currentRowChanged.connect(self.select_effect)
        layout.addWidget(self.effects, 1)
        row = QHBoxLayout()
        for text, callback in [('Load VST3 file', self.add_file), ('Load VST3 bundle', self.add_bundle),
                               ('Remove', self.remove), ('Move up', lambda: self.move(-1)),
                               ('Move down', lambda: self.move(1)), ('Bypass', self.bypass)]:
            self.button(text, callback, row)
        layout.addLayout(row)
        self.parameter = QComboBox()
        self.parameter.currentTextChanged.connect(self.select_parameter)
        layout.addWidget(self.parameter)
        self.value = QSlider(Qt.Horizontal)
        self.value.setRange(0, 1000)
        self.value.valueChanged.connect(self.set_value)
        layout.addWidget(self.value)
        row = QHBoxLayout()
        self.gesture_knob = QComboBox()
        self.gesture_knob.addItems([f'Plugin knob {i}' for i in range(1, 9)])
        row.addWidget(self.gesture_knob)
        self.button('Bind to selected parameter', self.bind, row)
        self.button('Restore saved rack', self.restore, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button('Gesture Learn', self.learn, row)
        self.button('Cancel Learn', self.cancel_learn, row)
        self.button('Open native editor', self.open_editor, row)
        self.button('Restart isolated rack', self.restart, row)
        layout.addLayout(row)
        self.status = QLabel('Load an installed VST3 audio effect. Generic parameter controls are shown here.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.button('Done', self.accept, layout)

    @property
    def rack(self):
        return self.owner.engine.rack

    @staticmethod
    def button(text, callback, row):
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)

    def refresh(self):
        selected = max(0, self.effects.currentRow())
        self.effects.clear()
        for index, slot in enumerate(self.rack.slots):
            self.effects.addItem(f'{index+1}. {Path(slot["path"]).name}' + (' [bypassed]' if slot['bypass'] else ''))
        self.effects.setCurrentRow(min(selected, len(self.rack.slots)-1))
        if self.pending:
            paths = ', '.join(item['path'] for item in self.pending.get('effects', []))
            self.status.setText('Saved rack pending. Review these plugin files, then Restore saved rack: '+paths)

    def stopped(self):
        if self.rack.editor_open or (self.editor_task and self.editor_task.is_alive()):
            self.status.setText('Close the native editor before changing the rack.')
            return False
        if self.owner.engine.stream:
            self.status.setText('Stop audio before changing the rack structure.')
            return False
        return True

    def add_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose VST3 effect', '', 'VST3 (*.vst3)')
        if path:
            self.add(path)

    def add_bundle(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose a .vst3 bundle directory')
        if path:
            self.add(path)

    def add(self, path):
        if not self.stopped():
            return
        try:
            self.status.setText('Loading effect. Plugin initialization can take several seconds.')
            self.status.repaint()
            try:
                self.rack.add(path)
            except RuntimeError as exc:
                name, accepted = QInputDialog.getText(self, 'Plugin bundle', str(exc)+'\nPlugin name (for multi-plugin bundles)')
                if not accepted or not name.strip():
                    return
                self.rack.add(path, name.strip())
            self.pending = None
            self.refresh()
            self.status.setText('Effect loaded. Select a parameter or bind a gesture knob.')
        except Exception as exc:
            self.status.setText('Could not load effect: '+str(exc))

    def remove(self):
        index = self.effects.currentRow()
        if index >= 0 and self.stopped():
            self.rack.remove(index)
            self.pending = None
            self.refresh()

    def move(self, direction):
        index = self.effects.currentRow()
        target = index+direction
        if 0 <= target < len(self.rack.slots) and index >= 0 and self.stopped():
            self.rack.move(index, target)
            self.pending = None
            self.refresh()
            self.effects.setCurrentRow(target)

    def bypass(self):
        index = self.effects.currentRow()
        if index >= 0:
            slot = self.rack.slots[index]
            slot['bypass'] = not slot['bypass']
            self.refresh()

    def select_effect(self, index):
        self.parameter.clear()
        if 0 <= index < len(self.rack.slots):
            self.parameter.addItems(sorted(self.rack.slots[index]['parameters']))

    def select_parameter(self, name):
        index = self.effects.currentRow()
        if index >= 0 and name in self.rack.slots[index]['parameters']:
            self.value.blockSignals(True)
            self.value.setValue(round(self.rack.slots[index]['parameters'][name]*1000))
            self.value.blockSignals(False)

    def set_value(self, value):
        if self.rack.set_parameter(self.effects.currentRow(), self.parameter.currentText(), value/1000):
            self.status.setText(f'{self.parameter.currentText()}: {value/10:.1f}% normalized')

    def bind(self):
        index, name = self.effects.currentRow(), self.parameter.currentText()
        if index >= 0 and name:
            self.rack.bindings[str(self.gesture_knob.currentIndex()+1)] = {'slot': index, 'parameter': name}
            self.status.setText('Bound. Choose '+self.gesture_knob.currentText()+' as a movement target in Gesture mapping.')

    def restore(self):
        if self.pending is not None and self.stopped():
            try:
                self.rack.restore(self.pending)
                self.pending = None
                self.refresh()
                self.status.setText('Saved rack restored.')
            except Exception as exc:
                self.status.setText('Rack restore failed; existing rack retained: '+str(exc))

    def restart(self):
        if self.stopped():
            try:
                self.rack.restart()
                self.status.setText('Isolated rack restarted. Pipeline delay: 42.7 ms, plus plugin and device latency.')
            except Exception as exc:
                self.status.setText(str(exc))

    def open_editor(self):
        index = self.effects.currentRow()
        if index < 0 or not self.stopped():
            return
        self.owner.arm.setChecked(False)
        self.owner.motion_dialog.stop()
        self.editor_error = ''
        self.rack.editor_pending = True
        def execute():
            try:
                self.rack.show_editor(index)
            except Exception as exc:
                self.editor_error = str(exc)
            finally:
                self.rack.editor_pending = False
        self.editor_task = threading.Thread(target=execute, daemon=True)
        self.editor_task.start()
        self.status.setText('Native editor opened in the plugin worker. Close it before starting audio. '
                            'Exposed parameter changes are retained; opaque plugin state is not yet saved.')

    def learn(self):
        index, name = self.effects.currentRow(), self.parameter.currentText()
        if index < 0 or not name or not self.owner.camera:
            self.status.setText('Start the camera and select a loaded plugin parameter first.')
            return
        self.owner.arm.setChecked(False)
        self.owner.motion_dialog.stop()
        self.learn_binding = (index, name, str(self.gesture_knob.currentIndex()+1))
        self.learner = GestureLearner()
        self.status.setText('Learning for 10 seconds. Move one hand up/down, left/right, or change thumb-index spread. '
                            'Gestures stay disarmed after learning.')

    def capture_learn(self, controls):
        if self.learner is None:
            return False
        axis = self.learner.feed(controls)
        if axis == 'timeout':
            self.cancel_learn()
        elif axis:
            index, name, knob = self.learn_binding
            if index < len(self.rack.slots) and name in self.rack.slots[index]['parameters']:
                self.rack.bindings[knob] = {'slot': index, 'parameter': name}
                self.owner.mappings[axis].setCurrentText('Plugin knob '+knob)
                self.owner.precision.reset()
                self.status.setText(f'Learned {axis} -> Plugin knob {knob} -> {name}. Arm gestures to perform.')
            self.learner = None
        return True

    def cancel_learn(self):
        self.learner = None
        self.status.setText('Gesture Learn ended. Gestures remain disarmed.')

    def poll(self):
        if self.learner and time.monotonic() >= self.learner.deadline:
            self.cancel_learn()
        if self.editor_task and not self.editor_task.is_alive():
            self.editor_task = None
            self.refresh()
            self.status.setText(self.editor_error or 'Editor closed. Exposed parameters updated.')
        if self.rack.error:
            self.status.setText('Plugin worker stopped; delayed dry fallback active. Stop audio and restart rack. '+self.rack.error)
