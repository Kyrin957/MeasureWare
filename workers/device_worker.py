"""DeviceWorker: measurement acquisition loop running on a QThread.

Communicates with LJ-X8000 via LJXAwrap, polls GetProfile in a loop,
extracts scalar values from each profile, and emits signals for GUI updates.
"""

import ctypes
import logging
import time
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

import LJXAwrap
from controllers.device_controller import DeviceController
from utils.profile_processor import extract_max_z, extract_avg_z

logger = logging.getLogger(__name__)


class DeviceWorker(QObject):
    """Acquisition loop worker — runs on a dedicated QThread."""

    # Signals emitted to the main thread
    point_acquired = Signal(int, float, float)  # point_index, value_mm, x_position_mm
    measurement_finished = Signal()             # acquisition complete
    connection_established = Signal()           # Ethernet connection opened
    connection_lost = Signal()                  # connection dropped
    error_occurred = Signal(str)                # error message
    log_message = Signal(str, int)              # log message, level

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = Event()
        self._device = DeviceController(device_id=0)
        self._session_id: int = 0
        self._target_count: int = 200
        self._extraction_config: dict = {}
        self._ethernet_config = None

    @Slot()
    def request_stop(self):
        """Request graceful stop of the acquisition loop."""
        self._stop_event.set()
        logger.debug("Stop requested for device worker")

    @Slot(int, int, dict, object)
    def run(self, session_id: int, target_count: int,
            extraction_config: dict, ethernet_config):
        """Main acquisition loop entry point.

        Args:
            session_id: MeasurementSession database ID.
            target_count: Target number of points to acquire.
            extraction_config: Dict with 'mode', 'roi_start', 'roi_end'.
            ethernet_config: LJX8IF_ETHERNET_CONFIG ctypes struct.
        """
        self._stop_event.clear()
        self._session_id = session_id
        self._target_count = target_count
        self._extraction_config = extraction_config
        self._ethernet_config = ethernet_config

        try:
            self._do_acquisition()
        except Exception as e:
            logger.exception(f"Unexpected error in acquisition loop: {e}")
            self.error_occurred.emit(f"Acquisition error: {e}")
        finally:
            # Always try to clean up
            try:
                self._device.stop_measurement()
            except Exception:
                pass
            try:
                self._device.close_connection()
            except Exception:
                pass

    def _do_acquisition(self):
        """Core acquisition loop."""

        # ---- 1. Open connection ----
        res = self._device.open_connection(self._ethernet_config)
        if res != 0:
            self.error_occurred.emit(f"Failed to connect: 0x{res:08X}")
            return
        self.connection_established.emit()

        # ---- 2. Clear controller memory ----
        self._device.clear_memory()

        # ---- 3. Start measurement ----
        res = self._device.start_measurement()
        if res != 0:
            self.error_occurred.emit(f"Failed to start measurement: 0x{res:08X}")
            self._device.close_connection()
            return

        # ---- 4. Prepare profile request buffers ----
        # Standard LJ-X8000 profile has 3200 X points; luminance depends on config
        xpoint_count = 3200
        with_luminance = 0  # We only need height data

        req = DeviceController.create_get_profile_request()
        rsp = LJXAwrap.LJX8IF_GET_PROFILE_RESPONSE()
        profinfo = LJXAwrap.LJX8IF_PROFILE_INFO()

        data_size = DeviceController.calculate_profile_buffer_size(
            xpoint_count, with_luminance
        )
        data_num_ints = data_size // ctypes.sizeof(ctypes.c_int)
        profdata = (ctypes.c_int * data_num_ints)()

        header_size = ctypes.sizeof(LJXAwrap.LJX8IF_PROFILE_HEADER)

        # ---- 5. Acquisition loop ----
        acquired_count = 0
        last_profile_no = 0xFFFFFFFF  # Sentinel to force first read
        consecutive_errors = 0
        max_consecutive_errors = 10

        mode = self._extraction_config.get("mode", "max")
        roi_start = self._extraction_config.get("roi_start", 0)
        roi_end = self._extraction_config.get("roi_end", 3199)

        self.log_message.emit(
            f"Starting acquisition: target={self._target_count}, mode={mode}, "
            f"ROI=[{roi_start}, {roi_end}]",
            logging.INFO
        )

        while acquired_count < self._target_count and not self._stop_event.is_set():
            # Poll for latest profile
            res = self._device.get_profile(req, rsp, profinfo, profdata, data_size)

            if res != 0:
                consecutive_errors += 1
                logger.warning(f"GetProfile error: 0x{res:08X} "
                               f"({consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                    self.error_occurred.emit(
                        f"Too many consecutive errors ({consecutive_errors}). Aborting."
                    )
                    break
                time.sleep(0.01)
                continue

            consecutive_errors = 0

            # Check if we got a new profile
            current_profile_no = rsp.dwCurrentProfileNo
            if current_profile_no == last_profile_no:
                # No new profile yet — brief sleep
                time.sleep(0.005)
                continue

            last_profile_no = current_profile_no

            # Extract scalar value from profile
            x_start = profinfo.lXStart
            x_pitch = profinfo.lXPitch
            data_count = profinfo.wProfileDataCount

            if mode == "max":
                z_val, x_val = extract_max_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end, x_start, x_pitch
                )
            elif mode == "avg":
                z_val, x_val = extract_avg_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end, x_start, x_pitch
                )
            else:
                z_val, x_val = extract_max_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end, x_start, x_pitch
                )

            if z_val is None:
                # All values invalid in this profile — skip
                logger.debug(f"Profile {current_profile_no}: all values invalid, skipping")
                continue

            acquired_count += 1
            self.point_acquired.emit(acquired_count, z_val, x_val if x_val else 0.0)

            # Small yield to avoid hammering the CPU
            time.sleep(0.001)

        # ---- 6. Cleanup ----
        self._device.stop_measurement()
        self._device.close_connection()

        if self._stop_event.is_set():
            self.log_message.emit(
                f"Measurement stopped by user. Acquired {acquired_count}/{self._target_count} points.",
                logging.INFO
            )
        else:
            self.log_message.emit(
                f"Measurement complete. Acquired {acquired_count} points.",
                logging.INFO
            )

        self.measurement_finished.emit()
