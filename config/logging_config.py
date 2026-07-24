"""Dual-handler logging: rotating file + Qt signal for GUI display."""

import logging
import os
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal


class QtLogSignalEmitter(QObject):
    """Emits log records as Qt signals for the GUI log panel."""
    log_message = Signal(str, int)  # message, level


_emitter: QtLogSignalEmitter | None = None


def get_log_emitter() -> QtLogSignalEmitter | None:
    return _emitter


class SignalHandler(logging.Handler):
    """Logging handler that forwards records to a Qt signal."""

    def emit(self, record: logging.LogRecord):
        if _emitter is not None:
            msg = self.format(record)
            _emitter.log_message.emit(msg, record.levelno)


def setup_logging(log_dir: str = "logs",
                  max_bytes: int = 5 * 1024 * 1024,
                  backup_count: int = 3) -> QtLogSignalEmitter:
    """Configure dual-handler logging (file + Qt signal).

    Returns the QtLogSignalEmitter for connecting to the LogPanel.
    """
    global _emitter

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Format
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    # Qt signal handler
    _emitter = QtLogSignalEmitter()
    signal_handler = SignalHandler()
    signal_handler.setLevel(logging.INFO)
    signal_handler.setFormatter(fmt)
    root_logger.addHandler(signal_handler)

    logging.getLogger(__name__).info("Logging system initialized")
    return _emitter
