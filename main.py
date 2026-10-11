"""Application entry point. Run with: python main.py"""
import sys

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from config import APP_NAME
from core.buddy import AadyaBuddy


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Warning: macOS menu bar tray isn't available in this session.")
    buddy = AadyaBuddy()
    # Keep a Python reference alive for the lifetime of the Qt event loop.
    app._aadya_buddy = buddy
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
