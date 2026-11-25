import sys


def main():
    import traceback
    from .library import DATA
    log = open(DATA / 'touchmusic.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = log
    sys.stderr = log
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from .ui import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName('TouchMusic')
    try:
        window = MainWindow()
    except Exception:
        traceback.print_exc()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, 'TouchMusic could not start', 'See data/touchmusic.log for details.')
        raise
    window.show()
    print('TouchMusic window initialized', flush=True)
    if '--load-engine' in sys.argv:
        QTimer.singleShot(0, window.load_model)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
