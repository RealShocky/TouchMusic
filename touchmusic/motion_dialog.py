"""Motion Score recording, event editing and explicit automation playback."""
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QFileDialog)
from .motion_score import MotionScore


class MotionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.score = MotionScore()
        self.replaying = False
        layout = QVBoxLayout(self)
        hint = QLabel('Record movement targets and deliberate pose actions against the audio beat clock. '
                      'Playback can change effects, loops, voices and MIDI. Camera gestures are disarmed for replay. '
                      'Timing uses the UI timer, not sample-accurate DAW automation. Recording replaces the current score.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Beat (zero-based)', 'Kind', 'Target', 'Value (0..1)'])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for title, callback in [('Record', lambda: self.start('Recording')), ('Play', lambda: self.start('Playing')),
                                ('Stop', self.stop), ('Apply edits', self.apply_edits),
                                ('Delete selected', self.delete), ('Export', self.export), ('Import', self.import_score)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('Stopped. Scores are saved inside performances; loading never starts playback.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def refresh(self):
        self.table.setRowCount(len(self.score.events))
        for row, event in enumerate(self.score.events):
            for column, value in enumerate((event['beat'], event['kind'], event['target'], event.get('value', ''))):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def start(self, mode):
        if (not self.owner.engine.stream and not self.owner.engine.external) or self.owner.rehearse.isChecked():
            self.status.setText('Start audio and leave rehearsal mode before recording or playing a score.')
            return
        if self.owner.plugin_dialog.learner or self.owner.engine.rack.editor_open:
            self.status.setText('Finish Gesture Learn and close native editors first.')
            return
        if mode == 'Playing':
            self.owner.arm.setChecked(False)
        self.score.start(mode, self.owner.engine.clock.frame)
        self.status.setText(mode)

    def stop(self):
        self.score.stop()
        self.owner.midi.panic()
        self.owner.engine.instrument.panic()
        self.refresh()
        self.status.setText('Stopped. MIDI notes released.')

    def tick(self):
        if self.score.mode == 'Stopped':
            return
        if (not self.owner.engine.stream and not self.owner.engine.external):
            self.stop()
            return
        clock = self.owner.engine.clock
        due = self.score.advance(clock.frame, clock.period)
        self.replaying = True
        try:
            for event in due:
                if event['kind'] == 'level':
                    self.owner.gesture_level(event['target'], event['value'])
                else:
                    self.owner.gesture_action(event['target'], 'Motion Score')
        finally:
            self.replaying = False
        self.status.setText(f'{self.score.mode} | beat {self.score.beat:.2f} | {len(self.score.events)} events')

    def capture(self, kind, target, value=None):
        if not self.replaying and self.score.mode == 'Recording':
            clock = self.owner.engine.clock
            self.score.advance(clock.frame, clock.period)
            self.score.capture(kind, target, value)

    def checked_load(self, settings):
        from .ui import EFFECT_TARGETS, ACTIONS, SCENE_PREFIX
        MotionScore.validate(settings)
        for event in settings['events']:
            allowed = EFFECT_TARGETS if event['kind'] == 'level' else [*ACTIONS,
                        *[SCENE_PREFIX+name for name in self.owner.saved_presets]]
            if event['target'] not in allowed:
                raise ValueError('Unknown Motion Score target: '+event['target'])
        self.score.load(settings)
        self.refresh()

    def apply_edits(self):
        try:
            events = []
            for row in range(self.table.rowCount()):
                beat, kind, target, value = [self.table.item(row, col).text() for col in range(4)]
                event = {'beat': float(beat), 'kind': kind, 'target': target}
                if kind == 'level':
                    event['value'] = float(value)
                events.append(event)
            self.checked_load({'version': 1, 'events': sorted(events, key=lambda e: e['beat'])})
            self.status.setText('Edits applied. Playback is stopped.')
        except Exception as exc:
            self.status.setText('Edits rejected: '+str(exc))

    def delete(self):
        for row in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(row)
        self.apply_edits()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export Motion Score', '', 'Motion Score (*.json)')
        if path:
            try:
                from pathlib import Path
                Path(path).write_text(json.dumps(self.score.settings(), indent=2), encoding='utf-8')
            except Exception as exc:
                self.status.setText(str(exc))

    def import_score(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import Motion Score', '', 'Motion Score (*.json)')
        if path:
            try:
                from pathlib import Path
                if Path(path).stat().st_size > 2*1024*1024:
                    raise ValueError('Motion Score file exceeds 2 MiB.')
                self.checked_load(json.loads(Path(path).read_text(encoding='utf-8')))
                self.status.setText('Imported. Review events, then Play explicitly.')
            except Exception as exc:
                self.status.setText(str(exc))
