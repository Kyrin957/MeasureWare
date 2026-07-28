"""DeviceWorker: measurement acquisition loop running on a QThread.

Communicates with LJ-X8000 via LJXAwrap, polls GetProfile in a loop,
extracts scalar values from each profile, and emits signals for GUI updates.

DB writes are performed on the worker thread with batch commits so the
GUI event loop is never blocked by I/O.
"""

import ctypes
import logging
import time
from datetime import datetime
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

import LJXAwrap
from controllers.device_controller import DeviceController
from models.database import Session
from models.measurement import MeasurementSession, MeasurementPoint
from utils.profile_processor import extract_max_z, extract_avg_z

logger = logging.getLogger(__name__)

# Commit to DB after this many points to balance IO vs main-thread latency
BATCH_COMMIT_SIZE = 20


class DeviceWorker(QObject):
    """Acquisition loop worker — runs on a dedicated QThread."""

    # Signals emitted to the main thread
    point_acquired = Signal(int, float)  # point_index, value_mm
    measurement_finished = Signal()             # thread lifecycle
    measurement_completed = Signal(dict)        # carries summary dict
    connection_established = Signal()           # Ethernet connection opened
    connection_lost = Signal()                  # connection dropped
    error_occurred = Signal(str)                # error message
    log_message = Signal(str, int)              # log message, level

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = Event()
        self._device = DeviceController(device_id=0)
        self._session_id: int = 0
        self._extraction_config: dict = {}
        self._ethernet_config = None
        self._reset_state()

    # ------------------------------------------------------------------
    # Per-run state
    # ------------------------------------------------------------------

    def _reset_state(self):
        """Clear batch buffer and running stats before each run."""
        self._batch_buffer: list[MeasurementPoint] = []
        self._max_value = -float("inf")
        self._max_index = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @Slot()
    def request_stop(self):
        """Request graceful stop of the acquisition loop."""
        self._stop_event.set()
        logger.debug("设备工作线程收到停止请求")

    @Slot()
    def run(self):
        """Acquisition loop entry point — called on worker thread via signal.

        Parameterless so it can be connected directly to QThread.started
        (which avoids the lambda → main-thread proxy problem).
        Set ``_session_id``, ``_extraction_config``, ``_ethernet_config``
        on the instance before ``QThread.start()``.
        """
        self._stop_event.clear()
        self._reset_state()

        session_db = Session()
        try:
            self._do_acquisition(session_db)
        except Exception as e:
            logger.exception(f"采集循环发生异常: {e}")
            self.error_occurred.emit(f"采集出错: {e}")
        finally:
            session_db.close()
            # Always try to clean up device
            try:
                self._device.stop_measurement()
            except Exception:
                pass
            try:
                self._device.close_connection()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # DB helpers  (run on worker thread)
    # ------------------------------------------------------------------

    def _flush_buffer(self, session_db):
        """Batch-commit accumulated points to DB."""
        if not self._batch_buffer:
            return
        try:
            session_db.add_all(self._batch_buffer)
            session_db.commit()
            self._batch_buffer.clear()
        except Exception as e:
            session_db.rollback()
            logger.exception(f"批量写入点位数据失败: {e}")

    def _handle_point(self, point_index: int, value: float, session_db):
        """Record one measurement point.

        Tracks max value in memory, buffers for batch DB insert,
        and emits the cross-thread signal for GUI updates.
        """
        # Track max value (no DB query needed)
        if value > self._max_value:
            self._max_value = value
            self._max_index = point_index

        # Buffer for batch insert
        point = MeasurementPoint(
            session_id=self._session_id,
            point_index=point_index,
            measured_value=value,
            created_at=datetime.now(),
        )
        self._batch_buffer.append(point)

        if len(self._batch_buffer) >= BATCH_COMMIT_SIZE:
            self._flush_buffer(session_db)

        # Notify GUI (cross-thread queued signal)
        self.point_acquired.emit(point_index, value)

    def _finalize(self, session_db, acquired_count: int) -> dict:
        """Flush remaining points, update session record, return summary."""
        self._flush_buffer(session_db)

        summary = {"id": self._session_id, "point_count": acquired_count}
        session = session_db.query(MeasurementSession).get(self._session_id)
        if session:
            session.point_count = acquired_count
            if self._max_value > -float("inf"):
                session.max_measured_value = round(self._max_value, 6)
            session.compute_judgment()
            session.completed_at = datetime.now()
            session_db.commit()
            summary = session.to_summary_dict()
            summary["max_point_index"] = self._max_index

        return summary

    # ------------------------------------------------------------------
    # Core acquisition
    # ------------------------------------------------------------------

    def _do_acquisition(self, session_db):
        """Core acquisition loop."""

        # ---- 1. Open connection ----
        res = self._device.open_connection(self._ethernet_config)
        if res != 0:
            self.error_occurred.emit(f"连接失败: 0x{res:08X}")
            return
        self.connection_established.emit()

        # ---- 2. Clear controller memory ----
        self._device.clear_memory()

        # ---- 3. Start measurement ----
        res = self._device.start_measurement()
        if res != 0:
            self.error_occurred.emit(f"启动测量失败: 0x{res:08X}")
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
            f"开始采集: 模式={mode}, "
            f"ROI=[{roi_start}, {roi_end}]",
            logging.INFO
        )

        while not self._stop_event.is_set():
            # Poll for latest profile
            res = self._device.get_profile(req, rsp, profinfo, profdata, data_size)

            if res != 0:
                consecutive_errors += 1
                logger.warning(f"获取轮廓数据错误: 0x{res:08X} "
                               f"({consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                    self.error_occurred.emit(
                        f"连续错误过多 ({consecutive_errors})，正在中止。"
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
                z_val = extract_max_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end
                )
            elif mode == "avg":
                z_val = extract_avg_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end
                )
            else:
                z_val = extract_max_z(
                    profdata, data_count, header_size,
                    roi_start, roi_end
                )

            if z_val is None:
                # All values invalid in this profile — skip
                logger.debug(f"轮廓 {current_profile_no}: 所有值无效，跳过")
                continue

            acquired_count += 1
            self._handle_point(acquired_count, z_val, session_db)

            # Small yield to avoid hammering the CPU
            time.sleep(0.001)

        # ---- 6. Finalize ----
        if self._stop_event.is_set():
            self.log_message.emit(
                f"用户停止测量，共采集 {acquired_count} 个点位。",
                logging.INFO
            )
        else:
            self.log_message.emit(
                f"测量完成，共采集 {acquired_count} 个点位。",
                logging.INFO
            )

        summary = self._finalize(session_db, acquired_count)
        self.measurement_finished.emit()
        self.measurement_completed.emit(summary)
