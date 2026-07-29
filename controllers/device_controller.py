"""TCP socket client for LJ-X8000 no-protocol (无协议) communication.

In no-protocol mode, the LJ-X8000 controller actively sends measurement values
as ASCII text strings over TCP.  The PC acts as a passive TCP client:
connect → receive → parse → repeat until stop.

This controller is designed to run on a worker thread (not the GUI thread).
All calls are synchronous and blocking.
"""

import logging
import re
import socket

logger = logging.getLogger(__name__)

# LJ-X8000 no-protocol output is lines like "+000.512" or "-000.512"
# terminated with CR+LF or LF.
_MEASUREMENT_PATTERN = re.compile(r"^[+-]\d+\.\d+$")


class DeviceController:
    """Thin synchronous wrapper around a TCP socket for LJ-X8000 no-protocol mode."""

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def open_connection(self, ip_address: str, port: int, timeout: float = 3.0) -> bool:
        """Open a TCP connection to the LJ-X8000 controller.

        Returns:
            True on success, False on failure.
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(timeout)

        try:
            self._socket.connect((ip_address, port))
            self._connected = True
            logger.info(f"已连接 LJ-X8000 (无协议模式): {ip_address}:{port}")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.error(f"TCP连接失败 [{ip_address}:{port}]: {e}")
            self._connected = False
            return False

    def close_connection(self) -> None:
        """Close the TCP connection gracefully."""
        self._connected = False
        try:
            if self._socket is not None:
                self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Socket may already be closed
        try:
            if self._socket is not None:
                self._socket.close()
        except OSError:
            pass
        logger.info("TCP连接已关闭")

    @property
    def is_connected(self) -> bool:
        return getattr(self, "_connected", False)

    # ------------------------------------------------------------------
    # Data reception
    # ------------------------------------------------------------------

    def receive_line(self, timeout: float = 1.0) -> str | None:
        """Read one line of data from the controller.

        Sets a short socket timeout so the call returns promptly when
        no data is available, allowing the stop-event to be checked.

        Args:
            timeout: Socket read timeout in seconds.

        Returns:
            The received line (stripped of trailing whitespace), or None
            if no data arrived within the timeout.
        """
        try:
            self._socket.settimeout(timeout)
            data = self._socket.recv(4096)
            if not data:
                # Connection closed by remote
                logger.warning("TCP连接被远程关闭")
                self._connected = False
                return None
            # Decode and return the first complete line
            text = data.decode("ascii", errors="replace").strip()
            return text if text else None
        except socket.timeout:
            return None
        except OSError as e:
            logger.error(f"接收数据出错: {e}")
            self._connected = False
            return None

    @staticmethod
    def parse_measurement(text: str) -> float | None:
        """Parse a no-protocol measurement string into a float value.

        Expected format: ``"±NNN.NNN"`` (signed float, e.g. ``"+000.512"``,
        ``"-012.345"``).

        Returns:
            Float value in mm, or None if the string does not match the
            expected measurement format.
        """
        text = text.strip()
        if not text:
            return None
        # Quick format check, then parse
        if _MEASUREMENT_PATTERN.match(text):
            try:
                value = float(text)
                return round(value, 6)
            except ValueError:
                return None
        # Fallback: try parsing any numeric-looking string
        try:
            value = float(text)
            return round(value, 6)
        except ValueError:
            return None
