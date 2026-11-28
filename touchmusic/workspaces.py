"""A navigable desktop shell around the existing performance workspaces."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QStackedWidget, QScrollArea


class Workspaces(QWidget):
    def __init__(self, parent, performance, pages):
        super().__init__(parent)
        self.names = ['Perform', *[name for name, _ in pages]]
        self.stack = QStackedWidget()
        self.navigation = QListWidget()
        self.navigation.setObjectName('workspaceNavigation')
        self.navigation.setFixedWidth(170)
        self.navigation.setStyleSheet('QListWidget { background: #101719; border: 0; padding: 8px; } '
            'QListWidget::item { padding: 12px 9px; border-radius: 5px; margin-bottom: 4px; } '
            'QListWidget::item:selected { background: #24483f; color: #b6f5dc; }')
        sidebar = QVBoxLayout()
        brand = QLabel('TOUCHMUSIC\nLIVE STUDIO')
        brand.setStyleSheet('font-size: 16px; font-weight: 700; color: #a3e8d1; padding: 16px 12px;')
        sidebar.addWidget(brand)
        sidebar.addWidget(self.navigation, 1)
        self.stack.addWidget(performance)
        self.widgets = {'Perform': performance}
        for name, dialog in pages:
            dialog.setParent(self)
            dialog.setWindowFlags(Qt.Widget)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            container = QWidget()
            page = QVBoxLayout(container)
            page.setContentsMargins(24, 18, 24, 18)
            title = QLabel(name)
            title.setStyleSheet('font-size: 28px; font-weight: 700; color: #a3e8d1; padding-bottom: 8px;')
            page.addWidget(title)
            page.addWidget(dialog, 1)
            scroll.setWidget(container)
            self.stack.addWidget(scroll)
            self.widgets[name] = dialog
            dialog.finished.connect(lambda _: self.open('Perform'))
        for name in self.names:
            self.navigation.addItem(name)
        self.navigation.currentRowChanged.connect(self.select)
        self.navigation.setCurrentRow(0)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(sidebar)
        layout.addWidget(self.stack, 1)

    def select(self, index):
        if 0 <= index < len(self.names):
            self.stack.setCurrentIndex(index)
            widget = self.widgets[self.names[index]]
            if callable(getattr(widget, 'refresh', None)):
                widget.refresh()
            widget.show()

    def open(self, name):
        self.navigation.setCurrentRow(self.names.index(name))
        self.widgets[name].show()
