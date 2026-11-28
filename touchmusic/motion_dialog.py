"""Motion Score recording, event editing and explicit automation playback."""
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QFileDialog)
from .motion_score import MotionScore


class MotionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.score = MotionScore()
        self.replaying = False
        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        layout = QVBoxLayout(self)
        hint = QLabel('Record movement targets and deliberate pose actions against the audio beat clock. '
                      'Playback can change effects, loops, voices and MIDI. Camera gestures are disarmed for replay. '
                      'DSP and supported note/chord controls follow the audio sample clock. Voice, macro and external MIDI actions '
                      'use a 10 ms GUI relay. Native parameter processing still follows worker block timing. Recording replaces the score.')
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
        if mode == 'Playing':
            self.owner.engine.motion.start(self.score.settings(), self.routes())
        else:
            self.owner.engine.motion.stop()
        self.score.start(mode, self.owner.engine.clock.frame)
        self.status.setText(mode)

    def stop(self):
        self.owner.engine.motion.stop()
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
        if self.score.mode == 'Playing':
            transport = self.owner.engine.motion
            self.replaying = True
            try:
                for event, handled, frame in transport.drain():
                    if handled:
                        self.owner.gesture_preview.setText(f'Motion Score frame {frame}: '+event['target'])
                    elif event['kind'] == 'level':
                        self.owner.gesture_level(event['target'], event['value'])
                    else:
                        self.owner.gesture_action(event['target'], 'Motion Score')
            finally:
                self.replaying = False
            self.score.beat = transport.beat
            self.sync_controls()
            if (transport.active_token == transport.token and not transport.running
                    and transport.pending is None and transport.messages.empty()):
                self.score.stop()
            self.status.setText(transport.error or f'{self.score.mode} | beat {self.score.beat:.3f} | audio-clock scheduling')
        else:
            clock = self.owner.engine.clock
            self.score.advance(clock.frame, clock.period)
            self.status.setText(f'Recording | beat {self.score.beat:.3f} | {len(self.score.events)} events')

    def sync_controls(self):
        params = self.owner.engine.params.copy()
        for key, slider in self.owner.sliders.items():
            if key not in params:
                continue
            divisor = 1000 if key == 'delaytime' else 1 if key in ('pitch', 'formant') else 100
            value = round(params[key]*divisor)
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
            label = self.owner.value_labels.get(key)
            if label is not None:
                label.setText(f'{value} ms' if key == 'delaytime' else f'{value:+d} st'
                              if key in ('pitch', 'formant') else f'{value}%')
        for index, loop in enumerate(self.owner.engine.loops):
            slider = self.owner.pad_levels[index]
            slider.blockSignals(True)
            slider.setValue(round(loop.gain*100))
            slider.blockSignals(False)
        from PySide6.QtWidgets import QComboBox, QCheckBox
        for key, control in self.owner.music_controls.items():
            if key not in params:
                continue
            value = params[key]
            control.blockSignals(True)
            if isinstance(control, QCheckBox):
                control.setChecked(bool(value))
            elif isinstance(control, QComboBox):
                if key in ('key', 'chord'):
                    control.setCurrentIndex(int(value))
                elif key == 'capture_bars':
                    control.setCurrentIndex(control.findData(value))
                else:
                    control.setCurrentText(str(value))
            else:
                control.setValue(round(value*100 if key == 'overdub_feedback' else value))
            control.blockSignals(False)
        for slider, gain in ((self.owner.track_volume, self.owner.engine.track.gain),
                             (self.owner.instrument_dialog.level, self.owner.engine.instrument.gain)):
            slider.blockSignals(True)
            slider.setValue(round(gain*100))
            slider.blockSignals(False)
        tune = round(params['tune']*100)
        self.owner.tune_button.blockSignals(True)
        self.owner.tune_button.setChecked(bool(tune))
        self.owner.tune_button.setText('Auto-Tune On' if tune else 'Auto-Tune Off')
        self.owner.tune_button.blockSignals(False)
        if tune:
            self.owner.last_tune = tune

    def routes(self):
        from .ui import EFFECT_TARGETS, TARGET_KEYS, MUSIC_TARGETS, INSTRUMENT_NOTES
        from PySide6.QtWidgets import QComboBox
        routes = {'_notes': INSTRUMENT_NOTES, '_velocity': self.owner.midi_dialog.velocity.value(),
                  '_length': self.owner.midi_dialog.length.value()/1000}
        for target in EFFECT_TARGETS:
            key = TARGET_KEYS.get(target, target.lower())
            slider = self.owner.sliders.get(key)
            if slider is not None:
                routes[target] = {'key': key, 'minimum': slider.minimum(), 'maximum': slider.maximum(),
                                  'divisor': 1000 if key == 'delaytime' else 1 if key in ('pitch', 'formant') else 100}
            elif target in MUSIC_TARGETS:
                key = MUSIC_TARGETS[target]
                control = self.owner.music_controls[key]
                if isinstance(control, QComboBox):
                    choices = [control.itemData(i) if key == 'capture_bars' else i for i in range(control.count())]
                    routes[target] = {'key': key, 'choices': choices}
                else:
                    routes[target] = {'key': key, 'minimum': control.minimum(), 'maximum': control.maximum(),
                                      'divisor': 100 if key == 'overdub_feedback' else 1}
        return routes

    def capture(self, kind, target, value=None):
        if not self.replaying and self.score.mode == 'Recording':
            clock = self.owner.engine.clock
            self.score.advance(clock.frame, clock.period)
            self.score.capture(kind, target, value)

    def checked_load(self, settings):
        from .text_labels import score_labels
        settings = score_labels(settings)
        from .ui import EFFECT_TARGETS, ACTIONS, SCENE_PREFIX
        MotionScore.validate(settings)
        for event in settings['events']:
            allowed = EFFECT_TARGETS if event['kind'] == 'level' else [*ACTIONS,
                        *[SCENE_PREFIX+name for name in self.owner.saved_presets]]
            if event['target'] not in allowed:
                raise ValueError('Unknown Motion Score target: '+event['target'])
        self.owner.engine.motion.stop()
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
