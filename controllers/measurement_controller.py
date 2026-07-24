"""MeasurementController: state machine coordinating device worker, DB, and GUI.

States: IDLE -> READY -> RUNNING -> COMPLETING -> IDLE (or ERROR)
"""

import logging
from datetime import datetime
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal, Slot, QThread

from models.database import Session
from models.measurement import MeasurementSession, MeasurementPoint
from models.baseline import ProductBaseline

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
    point_data_ready = Signal(int, float, float)       # index, value, x_pos
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
        logger.debug(f"State: {old_state.name} -> {new_state.name}")

    # ------------------------------------------------------------------
    # Session preparation
    # ------------------------------------------------------------------

    def prepare_session(self, batch_number: str, product_name: str,
                        inspection_sequence: str = "",
                        target_count: int = 200) -> int | None:
        """Validate inputs and create a MeasurementSession in the DB.

        Returns:
            Session ID if successful, None on validation failure.
        """
        # Validate
        if not batch_number.strip():
            self.log_message.emit("请输入批号 (Batch number is required)", logging.WARNING)
            return None
        if not product_name.strip():
            self.log_message.emit("请输入品名 (Product name is required)", logging.WARNING)
            return None

        session_db = Session()
        try:
            # Look up baseline
            baseline = session_db.query(ProductBaseline).filter_by(
                product_name=product_name.strip()
            ).first()

            # Create session
            measurement_session = MeasurementSession(
                batch_number=batch_number.strip(),
                product_name=product_name.strip(),
                inspection_sequence=inspection_sequence.strip() if inspection_sequence else "",
                baseline_value=baseline.baseline_value if baseline else None,
                tolerance_upper=baseline.tolerance_upper if baseline else None,
                tolerance_lower=baseline.tolerance_lower if baseline else None,
                point_count=0,
                started_at=datetime.now(),
            )
            session_db.add(measurement_session)
            session_db.commit()

            session_id = measurement_session.id
            self._current_session_id = session_id

            self.log_message.emit(
                f"Session #{session_id} created: batch={batch_number}, "
                f"product={product_name}"
                + (f", baseline={baseline.baseline_value}" if baseline else ", no baseline"),
                logging.INFO
            )

            self._set_state(MeasurementState.READY)
            return session_id

        except Exception as e:
            session_db.rollback()
            logger.exception(f"Failed to create session: {e}")
            self.log_message.emit(f"创建测量任务失败: {e}", logging.ERROR)
            return None
        finally:
            session_db.close()

    # ------------------------------------------------------------------
    # Start acquisition
    # ------------------------------------------------------------------

    def start_acquisition(self, target_count: int = 200):
        """Launch the measurement worker on a background thread."""
        if self._state not in (MeasurementState.READY, MeasurementState.IDLE):
            self.log_message.emit("Measurement already in progress", logging.WARNING)
            return

        if self._current_session_id is None:
            self.log_message.emit("No session prepared", logging.WARNING)
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

        # Connect worker signals
        self._worker.point_acquired.connect(self._on_point_acquired)
        self._worker.measurement_finished.connect(self._on_measurement_finished)
        self._worker.connection_established.connect(
            lambda: self.log_message.emit("设备已连接", logging.INFO)
        )
        self._worker.connection_lost.connect(
            lambda: self.log_message.emit("设备已断开", logging.INFO)
        )
        self._worker.error_occurred.connect(self._on_error)
        self._worker.log_message.connect(self.log_message.emit)

        # Thread lifecycle
        self._thread.started.connect(
            lambda: self._worker.run(
                self._current_session_id, target_count,
                extraction_cfg, ethernet_cfg
            )
        )
        self._worker.measurement_finished.connect(self._thread.quit)
        self._worker.measurement_finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda: setattr(self, '_thread', None))

        # Start
        self._set_state(MeasurementState.RUNNING)
        self._thread.start()
        self.log_message.emit(
            f"开始测量: 目标 {target_count} 个点位 "
            f"({'仿真模式' if self._use_simulation else '实机模式'})",
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
    # Point handling
    # ------------------------------------------------------------------

    @Slot(int, float, float)
    def _on_point_acquired(self, point_index: int, value: float, x_position: float):
        """Handle a new measurement point from the worker."""
        # Store to DB
        session_db = Session()
        try:
            point = MeasurementPoint(
                session_id=self._current_session_id,
                point_index=point_index,
                x_position=x_position,
                measured_value=value,
                created_at=datetime.now(),
            )
            session_db.add(point)
            session_db.commit()
        except Exception as e:
            session_db.rollback()
            logger.exception(f"Failed to store point {point_index}: {e}")
        finally:
            session_db.close()

        # Forward to GUI
        self.point_data_ready.emit(point_index, value, x_position)

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    @Slot()
    def _on_measurement_finished(self):
        """Handle measurement completion — compute max, judgment."""
        self._set_state(MeasurementState.COMPLETING)

        session_db = Session()
        try:
            session = session_db.query(MeasurementSession).get(
                self._current_session_id
            )
            if session is None:
                logger.error(f"Session {self._current_session_id} not found")
                return

            # Count points
            point_count = session_db.query(MeasurementPoint).filter_by(
                session_id=self._current_session_id
            ).count()
            session.point_count = point_count

            # Compute max value
            from sqlalchemy import func
            max_result = session_db.query(
                func.max(MeasurementPoint.measured_value)
            ).filter_by(
                session_id=self._current_session_id
            ).scalar()

            if max_result is not None:
                session.max_measured_value = round(max_result, 6)

            # Compute judgment
            session.compute_judgment()
            session.completed_at = datetime.now()

            session_db.commit()

            summary = session.to_summary_dict()
            self.log_message.emit(
                f"测量完成: 共 {point_count} 个点位, "
                f"最大值={session.max_measured_value}, "
                f"判定={session.judgment}",
                logging.INFO
            )

            self.session_completed.emit(summary)

        except Exception as e:
            session_db.rollback()
            logger.exception(f"Failed to finalize session: {e}")
            self.log_message.emit(f"完成测量处理失败: {e}", logging.ERROR)
        finally:
            session_db.close()

        self._set_state(MeasurementState.IDLE)

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
    # Point editing (from table)
    # ------------------------------------------------------------------

    def update_point_value(self, session_id: int, point_index: int,
                           new_value: float) -> dict | None:
        """Update a measurement point's value (from table edit).

        Recalculates session max and judgment after the edit.
        Returns updated session summary dict.
        """
        session_db = Session()
        try:
            point = session_db.query(MeasurementPoint).filter_by(
                session_id=session_id, point_index=point_index
            ).first()

            if point is None:
                return None

            point.measured_value = new_value
            session_db.commit()

            # Recalculate session max and judgment
            session = session_db.query(MeasurementSession).get(session_id)
            if session is None:
                return None

            from sqlalchemy import func
            max_result = session_db.query(
                func.max(MeasurementPoint.measured_value)
            ).filter_by(session_id=session_id).scalar()

            if max_result is not None:
                session.max_measured_value = round(max_result, 6)

            session.compute_judgment()
            session_db.commit()

            return session.to_summary_dict()

        except Exception as e:
            session_db.rollback()
            logger.exception(f"Failed to update point {point_index}: {e}")
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
