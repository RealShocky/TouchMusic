"""Keep one Qt application alive across desktop integration tests."""
import os
import pytest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


@pytest.fixture(scope='session', autouse=True)
def qt_application():
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    yield application
    application.processEvents()
