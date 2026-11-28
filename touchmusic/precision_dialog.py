"""Camera movement calibration and deliberately adjustable gesture timing."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QCheckBox, QPushButton


class PrecisionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Gesture precision')
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        hint = QLabel('Calibrate while moving both hands through a comfortable range. Calibration disarms gestures. '
                      'Deadband ignores small changes; sensitivity expands your movement around the midpoint.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        grid = QGridLayout()
        self.controls = {}
        for row, (key, label, low, high, default, suffix) in enumerate([
            ('hold_ms', 'Pose hold', 100, 1500, 250, ' ms'),
            ('smoothing_ms', 'Movement smoothing', 10, 500, 90, ' ms'),
            ('deadband', 'Movement deadband', 0, 15, 2, '%'),
            ('sensitivity', 'Movement sensitivity', 50, 200, 100, '%'),
            ('pinch_ms', 'Pinch cooldown', 200, 2000, 600, ' ms'),
        ]):
            spin = QSpinBox()
            spin.setRange(low, high)
            spin.setValue(default)
            spin.setSuffix(suffix)
            spin.setAccessibleName(label)
            self.controls[key] = spin
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(spin, row, 1)
        layout.addLayout(grid)
        self.freeze = QCheckBox('Freeze continuous movements (finger and pinch actions stay active)')
        layout.addWidget(self.freeze)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        for label, callback in [('Calibrate movement for 5 seconds', parent.start_calibration),
                                ('Reset calibration', self.reset_ranges), ('Done', self.accept)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button)
        for spin in self.controls.values():
            spin.valueChanged.connect(parent.update_precision)
        self.freeze.toggled.connect(lambda _: parent.precision.reset())
        self.finished.connect(parent.save_settings)

    def settings(self):
        return {**{key: spin.value() for key, spin in self.controls.items()},
                'ranges': dict(self.parent().precision.ranges)}

    def apply_settings(self, settings):
        if not isinstance(settings, dict):
            return
        for key, spin in self.controls.items():
            value = settings.get(key)
            if type(value) is int:
                spin.setValue(value)
        ranges = settings.get('ranges', {})
        if isinstance(ranges, dict):
            self.parent().precision.ranges = dict(ranges)
        self.parent().update_precision()

    def reset_ranges(self):
        self.parent().precision.ranges = {}
        self.parent().precision.reset()
        self.status.setText('Calibration reset. Full camera movement range is active.')
