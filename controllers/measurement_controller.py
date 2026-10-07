"""MeasurementController: state machine coordinating device worker, DB, and GUI.

States: IDLE -> READY -> RUNNING -> COMPLETING -> IDLE (or ERROR)

Database writes are handled by the worker thread; the controller only
forwards signals between the worker and GUI, keeping the event loop free.
"""

import logging
from datetime import datetime
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal, Slot, QThread

from models.database import Session
from models.measurement import MeasurementSession, MeasurementPoint
from models.baseline import ProductBaseline
from utils.datasheet_writer import save_session_to_datasheet

logger = logging.getLogger(__name__)


class MeasurementState(Enum):
    IDLE = auto()
    READY = auto()
    RUNNING = auto()
    COMPLETING = auto()
    ERROR = auto()


class MeasurementController(QObject):
    """Orchestrates the measurement workflow."""

    # Signals for GUI
    point_data_ready = Signal(int, float, object)  # index, height, width (width may be None)
    session_completed = Signal(dict)                    # session summary
    state_changed = Signal(str)                         # new state name
    log_message = Signal(str, int)                      # log

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._state = MeasurementState.IDLE
        self._current_session_id: int | None = None
        self._thread: QThread | None = None
        self._worker = None
        self._use_simulation = True  # Default to simulation for dev

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> MeasurementState:
        return self._state

    @property
    def is_idle(self) -> bool:
        return self._state == MeasurementState.IDLE

    @property
    def use_simulation(self) -> bool:
        return self._use_simulation

    @use_simulation.setter
    def use_simulation(self, value: bool):
        self._use_simulation = value

    def _set_state(self, new_state: MeasurementState):
        old_state = self._state
        self._state = new_state
        self.state_changed.emit(new_state.name)
        logger.debug(f"状态变更: {old_state.name} -> {new_state.name}")

    # ------------------------------------------------------------------
    # Session preparation
    # ------------------------------------------------------------------

    def prepare_session(self, batch_number: str, spec_name: str,
                        inspection_sequence: str = "") -> int | None:
        """Validate inputs and create a MeasurementSession in the DB.

        Runs on the main thread but is a single lightweight query+insert;
        the heavy per-point writes happen on the worker thread.

        Returns:
            Session ID if successful, None on validation failure.
        """
        # Validate
        if not batch_number.strip():
            self.log_message.emit("请输入批号", logging.WARNING)
            return None
        if not spec_name.strip():
            self.log_message.emit("请输入树脂规格要求", logging.WARNING)
            return None

        session_db = Session()
        try:
            # Look up spec limits
            baseline = session_db.query(ProductBaseline).filter_by(
                spec_name=spec_name.strip()
            ).first()

            # Create session
            measurement_session = MeasurementSession(
                batch_number=batch_number.strip(),
                spec_name=spec_name.strip(),
                inspection_sequence=inspection_sequence.strip() if inspection_sequence else "",
                height_upper_limit=baseline.height_upper_limit if baseline else None,
                width_upper_limit=baseline.width_upper_limit if baseline else None,
                point_count=0,
                started_at=datetime.now(),
            )
            session_db.add(measurement_session)
            session_db.commit()

            session_id = measurement_session.id
            self._current_session_id = session_id

            if baseline:
                width_note = (f"{baseline.width_upper_limit}"
                              if baseline.width_check_enabled else "不检查")
                self.log_message.emit(
                    f"测量任务 #{session_id} 已创建: 批号={batch_number}, "
                    f"树脂规格要求={spec_name}, "
                    f"高度上限={baseline.height_upper_limit} mm, "
                    f"宽度上限={width_note}",
                    logging.INFO
                )
            else:
                self.log_message.emit(
                    f"测量任务 #{session_id} 已创建: 批号={batch_number}, "
                    f"树脂规格要求={spec_name}, 无规格上限值",
                    logging.INFO
                )

            self._set_state(MeasurementState.READY)
            return session_id

        except Exception as e:
            session_db.rollback()
            logger.exception(f"创建测量任务失败: {e}")
            self.log_message.emit(f"创建测量任务失败: {e}", logging.ERROR)
            return None
        finally:
            session_db.close()

    # ------------------------------------------------------------------
    # Start acquisition
    # ------------------------------------------------------------------

    def start_acquisition(self):
        """Launch the measurement worker on a background thread."""
        if self._state not in (MeasurementState.READY, MeasurementState.IDLE):
            self.log_message.emit("测量已在进行中", logging.WARNING)
            return

        if self._current_session_id is None:
            self.log_message.emit("未准备测量任务", logging.WARNING)
            return

        # Select worker type
        if self._use_simulation:
            from workers.simulation_worker import SimulationWorker
            self._worker = SimulationWorker()
        else:
            from workers.device_worker import DeviceWorker
            self._worker = DeviceWorker()

        # Create thread
        self._thread = QThread()

        # Prepare extraction config
        extraction_cfg = self._settings.get_extraction_config()
        ethernet_cfg = self._settings.get_ethernet_config()

        # Move worker to thread
        self._worker.moveToThread(self._thread)

        # Store parameters on the worker so run() can be parameterless.
        # This is necessary because we must connect QThread.started
        # directly to worker.run (signal-to-slot), NOT through a lambda.
        # A lambda would execute on the main thread due to Qt's
        # AutoConnection cross-thread queuing, blocking the UI.
        self._worker._session_id = self._current_session_id
        self._worker._extraction_config = extraction_cfg
        self._worker._ethernet_config = ethernet_cfg

        # Connect worker signals — point_acquired is forwarded to UI only
        # (DB writes happen on the worker thread via _handle_point)
        self._worker.point_acquired.connect(self._on_point_acquired)
        self._worker.measurement_finished.connect(self._on_measurement_finished)
        self._worker.measurement_completed.connect(self._on_measurement_completed)
        self._worker.connection_established.connect(
            lambda: self.log_message.emit("设备已连接", logging.INFO)
        )
        self._worker.connection_lost.connect(
            lambda: self.log_message.emit("设备已断开", logging.INFO)
        )
        self._worker.error_occurred.connect(self._on_error)
        self._worker.log_message.connect(self.log_message.emit)

        # Thread lifecycle — connect started directly to worker.run.
        # Since both the QThread's internal thread and the worker
        # (moved via moveToThread) share the same thread affinity,
        # Qt uses DirectConnection → run() executes on the WORKER thread.
        self._thread.started.connect(self._worker.run)
        self._worker.measurement_finished.connect(self._thread.quit)
        self._worker.measurement_finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda: setattr(self, '_thread', None))

        # Start
        self._set_state(MeasurementState.RUNNING)
        self._thread.start()
        self.log_message.emit(
            f"开始测量 ({'仿真模式' if self._use_simulation else '实机模式'})",
            logging.INFO
        )

    # ------------------------------------------------------------------
    # Stop acquisition
    # ------------------------------------------------------------------

    def request_stop(self):
        """Request graceful stop of the measurement."""
        if self._worker is not None:
            self._worker.request_stop()
            self.log_message.emit("正在停止测量...", logging.INFO)

    # ------------------------------------------------------------------
    # Point handling  (main thread — lightweight, no DB work)
    # ------------------------------------------------------------------

    @Slot(int, float, object)
    def _on_point_acquired(self, point_index: int, height: float, width):
        """Forward a measurement point to the GUI.

        DB storage is handled by the worker on its thread.
        """
        self.point_data_ready.emit(point_index, height, width)

    # ------------------------------------------------------------------
    # Completion  (main thread — lightweight, no DB work)
    # ------------------------------------------------------------------

    @Slot()
    def _on_measurement_finished(self):
        """The worker thread loop has exited — begin completion."""
        self._set_state(MeasurementState.COMPLETING)

    @Slot(dict)
    def _on_measurement_completed(self, summary: dict):
        """Handle measurement completion — summary already computed by worker."""
        point_count = summary.get("point_count", 0)
        max_height = summary.get("max_height_value", "N/A")
        max_width = summary.get("max_width_value", "N/A")
        judgment = summary.get("judgment", "N/A")

        self.log_message.emit(
            f"测量完成: 共 {point_count} 个点位, "
            f"高度最大值={max_height}, 宽度最大值={max_width}, 判定={judgment}",
            logging.INFO
        )

        self.session_completed.emit(summary)
        self._set_state(MeasurementState.IDLE)

        # Auto-save to local datasheets folder (non-blocking, lightweight DB read)
        self._save_datasheet(summary)

    # ------------------------------------------------------------------
    # Datasheet auto-save
    # ------------------------------------------------------------------

    def _save_datasheet(self, summary: dict):
        """Persist completed session data to the local datasheets folder.

        The CSV is written under ``datasheets/YYYY/MM/{OK|NG}/<batch>.csv``,
        routed by the session-level judgment.
        Failure to save does **not** affect the measurement workflow — errors
        are logged and silently ignored.
        """
        try:
            session_id = summary.get("id")
            if session_id is None:
                return

            points = self.get_session_points(session_id)
            if not points:
                logger.debug("Session #%d has no points — skipping datasheet save",
                             session_id)
                return

            from datetime import datetime
            filepath = save_session_to_datasheet(summary, points, datetime.now())
            if filepath:
                self.log_message.emit(
                    f"测量数据已自动保存到: {filepath}",
                    logging.INFO,
                )
        except Exception:
            logger.exception("自动保存数据表失败 (session #%s)",
                             summary.get("id"))

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_error(self, error_message: str):
        """Handle error from the worker."""
        self.log_message.emit(f"错误: {error_message}", logging.ERROR)
        self._set_state(MeasurementState.ERROR)
        # Auto-reset to IDLE after error
        self._set_state(MeasurementState.IDLE)

    # ------------------------------------------------------------------
    # Point editing (from table)  — on-demand, not in hot path
    # ------------------------------------------------------------------

    def update_point_value(self, session_id: int, point_index: int,
                           field: str, new_value: float) -> dict | None:
        """Update a measurement point's height or width value (from table edit).

        Args:
            field: "height" or "width".

        Recalculates session max values and judgment after the edit.
        Returns updated session summary dict.
        """
        session_db = Session()
        try:
            point = session_db.query(MeasurementPoint).filter_by(
                session_id=session_id, point_index=point_index
            ).first()

            if point is None:
                return None

            if field == "height":
                point.height_value = new_value
            elif field == "width":
                point.width_value = new_value
            else:
                return None
            session_db.commit()

            # Recalculate session max values and judgment
            session = session_db.query(MeasurementSession).get(session_id)
            if session is None:
                return None

            from sqlalchemy import func
            max_height = session_db.query(
                func.max(MeasurementPoint.height_value)
            ).filter_by(session_id=session_id).scalar()
            max_width = session_db.query(
                func.max(MeasurementPoint.width_value)
            ).filter_by(session_id=session_id).scalar()

            if max_height is not None:
                session.max_height_value = round(max_height, 6)
            if max_width is not None:
                session.max_width_value = round(max_width, 6)

            session.compute_judgment()
            session_db.commit()

            return session.to_summary_dict()

        except Exception as e:
            session_db.rollback()
            logger.exception(f"更新点位 {point_index} 失败: {e}")
            return None
        finally:
            session_db.close()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_session_points(self, session_id: int) -> list[dict]:
        """Get all measurement points for a session."""
        session_db = Session()
        try:
            points = session_db.query(MeasurementPoint).filter_by(
                session_id=session_id
            ).order_by(MeasurementPoint.point_index).all()
            return [p.to_dict() for p in points]
        finally:
            session_db.close()

    def get_all_sessions(self) -> list[dict]:
        """Get all measurement sessions."""
        session_db = Session()
        try:
            sessions = session_db.query(MeasurementSession).order_by(
                MeasurementSession.started_at.desc()
            ).all()
            return [s.to_summary_dict() for s in sessions]
        finally:
            session_db.close()
