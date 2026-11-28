"""Installed effects, isolated scans and reviewed publisher downloads."""
import json
from pathlib import Path
import threading
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QTextEdit, QFileDialog, QLineEdit)
from .plugin_catalog import CATALOG, DOWNLOADS, download_plugin
from .plugin_scan import discover, standard_folders, scan_plugin, fingerprint, save_scan
from .plugin_process import PluginProcess


class PluginCenter(QDialog):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.owner, self.data = parent, Path(data)
        self.setWindowTitle('Plugin Center')
        self.resize(850, 650)
        self.reports = {}
        self.task = None
        self.result = None
        self.clients = []
        self.cancelled = False
        layout = QVBoxLayout(self)
        hint = QLabel('Discovery reads paths only. Scan before loading an effect. A failed scan quarantines '
                      'that entry until a successful rescan. Instruments are catalogued for future hosting.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        installed, catalog = QWidget(), QWidget()
        tabs.addTab(installed, 'Installed effects')
        tabs.addTab(catalog, 'Publisher catalog')
        pane = QVBoxLayout(installed)
        self.installed = QListWidget()
        self.installed.currentRowChanged.connect(self.describe)
        pane.addWidget(self.installed)
        row = QHBoxLayout()
        for title, callback in [('Discover', self.refresh), ('Add folder', self.add_folder),
                                ('Scan selected', self.scan), ('Load into FX rack', self.load)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        pane.addLayout(row)
        self.version = QLineEdit()
        self.version.setPlaceholderText('Exact publisher version for scan report, if known')
        pane.addWidget(self.version)
        pane = QVBoxLayout(catalog)
        self.catalog = QListWidget()
        for name, purpose, license_name, url in CATALOG:
            item = QListWidgetItem(f'{name} | {purpose} | {license_name} | compatibility unverified')
            item.setData(Qt.UserRole, (name, url))
            self.catalog.addItem(item)
        pane.addWidget(self.catalog)
        for title, callback in [('Open official publisher', self.publisher),
                                ('Download reviewed archive', self.download)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            pane.addWidget(button)
        pane.addWidget(QLabel('Reviewed archives: TDR Nova 2.2.3, SnapTune 2.4.0, LyraTune 0.6.7.\n'
                             'Downloads are saved, never executed. No third-party binaries are bundled.'))
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report)
        self.status = QLabel('Ready. No native plugins are loaded by discovery.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)
        QTimer.singleShot(0, self.refresh)

    def selected(self):
        item = self.installed.currentItem()
        return item.data(Qt.UserRole) if item else None

    def refresh(self):
        if self.task or self.cancelled:
            return
        paths = [*standard_folders(), *self.owner.settings.get('plugin_folders', [])]
        self.run(lambda: ('discovery', discover(paths)), 'Discovering installed VST3 paths...')

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Add VST3 search folder')
        if path:
            folders = self.owner.settings.setdefault('plugin_folders', [])
            if path not in folders:
                folders.append(path)
            self.refresh()

    def run(self, operation, message):
        if self.task:
            self.status.setText('Wait for the current operation to finish.')
            return
        self.status.setText(message)
        self.result = None
        def execute():
            try:
                self.result = operation()
            except Exception as exc:
                self.result = ('error', str(exc))
        self.task = threading.Thread(target=execute, daemon=True)
        self.task.start()

    def scan(self):
        path = self.selected()
        if not path or self.task:
            return
        version = self.version.text().strip() or 'Unknown'
        def factory():
            if self.cancelled:
                raise RuntimeError('Scan cancelled.')
            client = PluginProcess()
            self.clients.append(client)
            if self.cancelled:
                client.close()
                raise RuntimeError('Scan cancelled.')
            return client
        self.run(lambda: ('scan', scan_plugin(path, version, factory)),
                 'Testing in a separate process. Loading and processing have timeouts...')

    def describe(self, *_):
        path = self.selected()
        if not path:
            return
        report = self.reports.get(path)
        if report is None:
            try:
                cached = self.data/'plugin-scans'/(fingerprint(path)+'.json')
                if cached.is_file() and cached.stat().st_size < 65536:
                    parsed = json.loads(cached.read_text(encoding='utf-8'))
                    if isinstance(parsed, dict):
                        report = parsed
                        self.reports[path] = report
            except (OSError, ValueError):
                pass
        self.report.setPlainText(json.dumps(report, indent=2) if report else path+'\nNot scanned.')

    def load(self):
        path = self.selected()
        if not path or not self.owner.plugin_dialog.stopped() or self.task:
            return
        report = self.reports.get(path, {})
        try:
            valid = (report.get('status') == 'Passed smoke test'
                     and report.get('binary_sha256') == fingerprint(path))
        except (OSError, ValueError):
            valid = False
        if not valid:
            self.status.setText('Scan this binary successfully before loading it from Plugin Center.')
            return
        self.owner.plugin_dialog.add(path)
        self.status.setText(self.owner.plugin_dialog.status.text())

    def publisher(self):
        item = self.catalog.currentItem()
        if item:
            QDesktopServices.openUrl(QUrl(item.data(Qt.UserRole)[1]))

    def download(self):
        item = self.catalog.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)[0]
        if name not in DOWNLOADS:
            self.status.setText('Use Open official publisher for this plugin. No reviewed archive is pinned yet.')
            return
        self.run(lambda: ('download', str(download_plugin(name, self.data/'plugin-downloads'))),
                 'Downloading official archive and checking the pinned SHA-256...')

    def poll(self):
        if not self.task or self.task.is_alive():
            return
        kind, value = self.result
        self.task = None
        if kind == 'discovery':
            self.installed.clear()
            for path in value:
                item = QListWidgetItem(Path(path).name+' | '+path)
                item.setData(Qt.UserRole, path)
                self.installed.addItem(item)
            self.status.setText(f'{len(value)} VST3 paths discovered. Select one and scan.')
        elif kind == 'scan':
            self.clients.clear()
            self.reports[value['path']] = value
            self.report.setPlainText(json.dumps(value, indent=2))
            self.status.setText(value['status'] + ': ' + value.get('error', 'Automated smoke test only.'))
            if value.get('binary_sha256'):
                try:
                    save_scan(self.data/'plugin-scans'/(value['binary_sha256']+'.json'), value)
                except OSError as exc:
                    self.status.setText('Scan finished, but the report could not be saved: '+str(exc))
        elif kind == 'download':
            self.status.setText('Verified archive saved. Extract/install manually, then Discover: '+value)
        else:
            self.status.setText(value)

    def shutdown(self):
        self.cancelled = True
        self.timer.stop()
        for client in self.clients:
            client.kill()
