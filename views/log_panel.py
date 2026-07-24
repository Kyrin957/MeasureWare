"""LogPanel: QPlainTextEdit widget for scrolling log display."""

import logging

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Slot
from PySide6.QtGui import QFont, QTextCursor


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
        """Append a log message. Called via Qt signal from the logging handler.

        Args:
            message: Formatted log message.
            level: Python logging level (DEBUG=10, INFO=20, WARNING=30, ERROR=40).
        """
        # Scroll to end before inserting
        self._text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self._text_edit.insertPlainText(message + "\n")
        # Auto-scroll to bottom
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
