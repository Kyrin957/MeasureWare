"""SimulationWorker: generates synthetic profile data for offline development.

Mimics the DeviceWorker interface using simulated data — no hardware required.

DB writes are performed on the worker thread with batch commits to avoid
blocking the GUI event loop.
"""

import logging
import random
import math
import time
from datetime import datetime
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from models.database import Session
from models.measurement import MeasurementSession, MeasurementPoint

logger = logging.getLogger(__name__)

# Commit to DB after this many points to balance IO vs main-thread latency
BATCH_COMMIT_SIZE = 20


class SimulationWorker(QObject):
    """Simulated measurement worker for offline development and testing."""

    point_acquired = Signal(int, float)  # point_index, value
    measurement_finished = Signal()                   # thread lifecycle
    measurement_completed = Signal(dict)              # carries summary dict
    connection_established = Signal()
    connection_lost = Signal()
    error_occurred = Signal(str)
    log_message = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = Event()
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
            self._do_simulation(session_db)
        except Exception as e:
            logger.exception(f"仿真出错: {e}")
            self.error_occurred.emit(f"仿真出错: {e}")
        finally:
            session_db.close()

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
    # Core simulation
    # ------------------------------------------------------------------

    def _do_simulation(self, session_db):
        """Generate synthetic measurement data."""
        # Simulate connection delay
        self.log_message.emit("仿真: 正在连接设备...", logging.INFO)
        time.sleep(0.3)
        self.connection_established.emit()

        self.log_message.emit("仿真: 正在启动测量...", logging.INFO)
        time.sleep(0.2)

        acquired_count = 0

        # Parameters for synthetic data — simulates a resin bump profile
        # Values oscillate with slight noise around 5.0mm, with occasional peaks
        base_value = 5.0  # mm

        self.log_message.emit(
            "仿真: 正在采集数据...", logging.INFO
        )

        while not self._stop_event.is_set():
            # Generate a measurement value with:
            # - Sine wave oscillation to simulate surface variation
            # - Random noise
            # - Occasional "defect" spike
            phase = acquired_count * 0.02 * math.pi  # gradual phase progression
            sine_component = 0.15 * math.sin(phase)
            noise = random.gauss(0, 0.02)

            # 5% chance of a larger deviation (simulates measurement variation)
            if random.random() < 0.05:
                spike = random.uniform(-0.3, 0.5)
            else:
                spike = 0.0

            value = base_value + sine_component + noise + spike
            value = round(max(0.1, value), 6)

            acquired_count += 1
            self._handle_point(acquired_count, value, session_db)

            # Simulate measurement interval (~0.5s per data point)
            time.sleep(0.5)

        # ---- Finalize ----
        self.log_message.emit(
            f"仿真: 采集完成，共 {acquired_count} 个点位。",
            logging.INFO
        )

        summary = self._finalize(session_db, acquired_count)

        self.connection_lost.emit()
        self.measurement_finished.emit()
        self.measurement_completed.emit(summary)
