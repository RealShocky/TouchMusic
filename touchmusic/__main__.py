import sys


def main():
    import argparse
    import traceback
    from .runtime import VERSION
    parser = argparse.ArgumentParser(description='TouchMusic live vocal and gesture instrument')
    parser.add_argument('--version', action='version', version='TouchMusic ' + VERSION)
    parser.add_argument('--load-engine', action='store_true', help='load the singing engine when the window opens')
    parser.add_argument('--setup-ai', action='store_true', help='install the optional singing engine and pinned upstream source')
    parser.add_argument('--cpu', action='store_true', help='use CPU wheels for --setup-ai')
    args = parser.parse_args()
    if args.setup_ai:
        from .setup_runtime import setup_ai
        setup_ai(cpu=args.cpu)
        return
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
        QMessageBox.critical(None, 'TouchMusic could not start', f'See {DATA / "touchmusic.log"} for details.')
        raise
    window.show()
    print('TouchMusic window initialized', flush=True)
    if args.load_engine:
        QTimer.singleShot(0, window.load_model)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
