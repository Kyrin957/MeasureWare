"""MeasurementSession and MeasurementPoint ORM models."""

from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, DateTime,
                        ForeignKey, Index)
from sqlalchemy.orm import relationship
from models.database import Base


class MeasurementSession(Base):
    """One measurement session = one product inspection."""

    __tablename__ = "measurement_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(String(128), nullable=False)
    product_name = Column(String(128), nullable=False)
    inspection_sequence = Column(String(64), default="")

    # Snapshot of baseline at measurement time
    baseline_value = Column(Float, nullable=True)
    tolerance_upper = Column(Float, nullable=True)
    tolerance_lower = Column(Float, nullable=True)

    # Computed results
    max_measured_value = Column(Float, nullable=True)
    judgment = Column(String(8), default="--")  # OK / NG / --

    point_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    points = relationship("MeasurementPoint", back_populates="session",
                          cascade="all, delete-orphan",
                          order_by="MeasurementPoint.point_index")

    def compute_judgment(self):
        """Recompute judgment based on max value and baseline tolerances."""
        if self.max_measured_value is None or self.baseline_value is None:
            self.judgment = "--"
            return

        diff = self.max_measured_value - self.baseline_value

        tol_upper = self.tolerance_upper or 0.0
        tol_lower = self.tolerance_lower or 0.0

        if -tol_lower <= diff <= tol_upper:
            self.judgment = "OK"
        else:
            self.judgment = "NG"

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "batch_number": self.batch_number,
            "product_name": self.product_name,
            "inspection_sequence": self.inspection_sequence,
            "baseline_value": self.baseline_value,
            "tolerance_upper": self.tolerance_upper,
            "tolerance_lower": self.tolerance_lower,
            "max_measured_value": self.max_measured_value,
            "judgment": self.judgment,
            "point_count": self.point_count,
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
        }


class MeasurementPoint(Base):
    """Individual measurement point within a session."""

    __tablename__ = "measurement_points"
    __table_args__ = (
        Index("idx_session_point", "session_id", "point_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("measurement_sessions.id"),
                        nullable=False)
    point_index = Column(Integer, nullable=False)
    x_position = Column(Float, nullable=True)
    measured_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("MeasurementSession", back_populates="points")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "point_index": self.point_index,
            "x_position": self.x_position,
            "measured_value": self.measured_value,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }

    def __repr__(self):
        return (f"<MeasurementPoint(idx={self.point_index}, "
                f"value={self.measured_value})>")
