"""Configure named gesture macro slots using supported performance actions."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from .macros import MACRO_ACTIONS


class MacroDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle('Gesture macros')
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        hint = QLabel('One pose can trigger up to eight actions in order. Actions run immediately; loop and chord '
                      'commands follow the current timing setting. Voice preparation can add delay. Save before testing.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.slot = QComboBox()
        self.slot.addItems(MACRO_ACTIONS)
        layout.addWidget(self.slot)
        self.actions = []
        for index in range(8):
            row = QHBoxLayout()
            row.addWidget(QLabel(f'{index+1}.'))
            combo = QComboBox()
            row.addWidget(combo, 1)
            self.actions.append(combo)
            layout.addLayout(row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        for text, callback in [('Save macro', self.save), ('Test saved macro', self.test), ('Done', self.accept)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            layout.addWidget(button)
        self.slot.currentTextChanged.connect(self.load_slot)

    def refresh(self):
        choices = ['None', *sorted(self.owner.macro_bank.allowed)]
        for combo in self.actions:
            combo.clear()
            combo.addItems(choices)
        self.load_slot()

    def load_slot(self, *_):
        values = self.owner.macro_bank.definitions.get(self.slot.currentText(), [])
        for index, combo in enumerate(self.actions):
            combo.setCurrentText(values[index] if index < len(values) else 'None')

    def save(self):
        try:
            self.owner.macro_bank.set(self.slot.currentText(),
                [combo.currentText() for combo in self.actions if combo.currentText() != 'None'])
            self.owner.save_settings()
            self.status.setText('Saved. Assign this macro slot in Gesture mapping.')
        except Exception as exc:
            self.status.setText(str(exc))

    def test(self):
        self.owner.gesture_action(self.slot.currentText())
        self.status.setText(self.owner.gesture_preview.text())
