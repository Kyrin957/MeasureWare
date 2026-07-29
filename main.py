"""Application entry point."""

import os
import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from models.database import init_db
from config.logging_config import setup_logging
from config.app_settings import AppSettings

logger = logging.getLogger(__name__)


def _get_app_dir() -> str:
    """Return the directory containing application resources.

    When frozen (PyInstaller), resources are extracted to sys._MEIPASS.
    In development mode, they live alongside this source file.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller one-file mode: resources extracted to temp dir
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Resin MeasureWare")
    app.setOrganizationName("MeasureWare")

    # Set window icon
    app_dir = _get_app_dir()
    icon_path = os.path.join(app_dir, "assets", "favicon.ico")
    if os.path.exists(icon_path):
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    # Load stylesheet
    style_path = os.path.join(app_dir, "resources", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # Setup logging FIRST — must happen before any logger calls
    log_emitter = setup_logging()

    # Initialize database
    init_db()
    logger.info("数据库初始化完成")

    # Load settings
    settings = AppSettings()

    # Create and show main window (lazy import to avoid circular deps)
    from views.main_window import MainWindow

    window = MainWindow(settings, log_emitter)
    window.show()

    logger.info("应用程序已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
