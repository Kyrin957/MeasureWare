"""LogPanel: QPlainTextEdit widget for scrolling log display."""

import logging
from datetime import datetime

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Slot
from PySide6.QtGui import QFont, QTextCursor

from config.logging_config import relay_to_file

# Map Python log levels to display strings
_LEVEL_NAMES = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class LogPanel(QWidget):
    """Scrollable, read-only log display widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("日志")
        title.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(title)

        # Text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 9))
        self._text_edit.setMaximumBlockCount(5000)
        self._text_edit.setMinimumHeight(100)
        layout.addWidget(self._text_edit)

    @Slot(str, int)
    def append_log(self, message: str, level: int):
        """Append a log message with uniform time + level formatting.

        All messages — whether from the Python logging system or from
        direct ``log_message.emit`` calls — are formatted here so the
        GUI display is always consistent::

            2024-01-01 12:00:00 [INFO   ] 消息内容

        Args:
            message: Raw log message text (unformatted).
            level: Python logging level (DEBUG=10, INFO=20, WARNING=30, ERROR=40).
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_name = _LEVEL_NAMES.get(level, "UNKNOWN")
        formatted = f"{timestamp} [{level_name:<7s}] {message}"

        self._text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self._text_edit.insertPlainText(formatted + "\n")
        # Auto-scroll to bottom
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Relay to file so GUI-displayed messages are also persisted
        relay_to_file(message, level)
