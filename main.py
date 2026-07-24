"""Application entry point."""

import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from models.database import init_db
from config.logging_config import setup_logging
from config.app_settings import AppSettings

logger = logging.getLogger(__name__)


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Resin MeasureWare")
    app.setOrganizationName("MeasureWare")

    # Load stylesheet
    import os
    style_path = os.path.join(os.path.dirname(__file__), "resources", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Setup logging (returns emitter for GUI connection)
    log_emitter = setup_logging()

    # Load settings
    settings = AppSettings()

    # Create and show main window (lazy import to avoid circular deps)
    from views.main_window import MainWindow

    window = MainWindow(settings, log_emitter)
    window.show()

    logger.info("Application started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
