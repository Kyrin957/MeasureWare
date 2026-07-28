"""Dual-handler logging: daily file + Qt signal for GUI display."""

import datetime
import logging
import os

from PySide6.QtCore import QObject, Signal


class QtLogSignalEmitter(QObject):
    """Emits log records as Qt signals for the GUI log panel."""
    log_message = Signal(str, int)  # message, level


_emitter: QtLogSignalEmitter | None = None
_gui_logger: logging.Logger | None = None  # Relay logger for GUI-originated messages


def get_log_emitter() -> QtLogSignalEmitter | None:
    return _emitter


def relay_to_file(message: str, level: int) -> None:
    """Write a GUI-originated message to the log file.

    Uses a dedicated non-propagating logger so the message reaches the
    file handler directly without re-entering the SignalHandler (which
    would cause duplicate GUI entries).
    """
    if _gui_logger is not None:
        _gui_logger.log(level, message)


class SignalHandler(logging.Handler):
    """Logging handler that forwards records to a Qt signal."""

    def emit(self, record: logging.LogRecord):
        if _emitter is not None:
            # Include logger name so GUI display matches file log format
            msg = f"{record.name}: {record.getMessage()}"
            _emitter.log_message.emit(msg, record.levelno)


def setup_logging(log_dir: str = "logs") -> QtLogSignalEmitter:
    """Configure dual-handler logging (file + Qt signal).

    Log files are organized hierarchically by year/month, with daily files
    named YYYYMMDD.log.  Existing files are appended to; new files are
    created automatically.

    Returns the QtLogSignalEmitter for connecting to the LogPanel.
    """
    global _emitter, _gui_logger

    # Build date-based directory path: logs/YYYY/MM/
    today = datetime.date.today()
    month_dir = os.path.join(log_dir, today.strftime("%Y"), today.strftime("%m"))
    os.makedirs(month_dir, exist_ok=True)

    log_file = os.path.join(month_dir, f"{today.strftime('%Y%m%d')}.log")

    # Root logger — clear any pre-existing handlers first
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    # Format (includes logger name for traceability)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (append mode — daily file, no rotation needed)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    # Qt signal handler
    _emitter = QtLogSignalEmitter()
    signal_handler = SignalHandler()
    signal_handler.setLevel(logging.INFO)
    signal_handler.setFormatter(fmt)
    root_logger.addHandler(signal_handler)

    # --- GUI relay logger: writes GUI-originated messages to file ---
    # Non-propagating so messages don't reach the root SignalHandler,
    # avoiding duplicate GUI entries from the logging→signal→GUI loop.
    _gui_logger = logging.getLogger("GUI")
    _gui_logger.propagate = False
    _gui_logger.setLevel(logging.DEBUG)
    gui_file_handler = logging.FileHandler(log_file, encoding="utf-8")
    gui_file_handler.setLevel(logging.DEBUG)
    gui_file_handler.setFormatter(fmt)
    _gui_logger.addHandler(gui_file_handler)

    logging.getLogger(__name__).info("日志系统初始化完成")
    return _emitter
