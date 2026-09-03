"""MeasurementSession and MeasurementPoint ORM models."""

from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, DateTime,
                        ForeignKey, Index)
from sqlalchemy.orm import relationship
from models.database import Base


class MeasurementSession(Base):
    """One measurement session = one product inspection.

    Height and width are captured per point; the final judgment is the
    logical AND of the height result and (when enabled) the width result.
    """

    __tablename__ = "measurement_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(String(128), nullable=False)
    spec_name = Column(String(128), nullable=False)
    inspection_sequence = Column(String(64), default="")

    # Snapshot of spec limits at measurement time
    height_upper_limit = Column(Float, nullable=True)
    width_upper_limit = Column(Float, nullable=True)

    # Computed results
    max_height_value = Column(Float, nullable=True)
    max_width_value = Column(Float, nullable=True)
    judgment = Column(String(8), default="--")  # OK / NG / --

    point_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    points = relationship("MeasurementPoint", back_populates="session",
                          cascade="all, delete-orphan",
                          order_by="MeasurementPoint.point_index")

    @property
    def width_check_enabled(self) -> bool:
        """Width inspection is disabled when the limit is zero/None."""
        return bool(self.width_upper_limit and self.width_upper_limit > 0)

    def compute_judgment(self):
        """Recompute judgment: height AND width (width only when enabled).

        - Height: OK when max height <= height upper limit.
        - Width:  checked only when width_upper_limit > 0;
                  OK when max width <= width upper limit.
        - Final:  OK only when every enabled check passes.
        """
        if self.max_height_value is None or self.height_upper_limit is None:
            self.judgment = "--"
            return

        height_ok = self.max_height_value <= self.height_upper_limit

        if not self.width_check_enabled:
            self.judgment = "OK" if height_ok else "NG"
            return

        if self.max_width_value is None:
            # Width check required but no width data available
            self.judgment = "--"
            return

        width_ok = self.max_width_value <= self.width_upper_limit
        self.judgment = "OK" if (height_ok and width_ok) else "NG"

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "batch_number": self.batch_number,
            "spec_name": self.spec_name,
            "inspection_sequence": self.inspection_sequence,
            "height_upper_limit": self.height_upper_limit,
            "width_upper_limit": self.width_upper_limit,
            "max_height_value": self.max_height_value,
            "max_width_value": self.max_width_value,
            "judgment": self.judgment,
            "point_count": self.point_count,
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
        }


class MeasurementPoint(Base):
    """Individual measurement point within a session.

    Each point carries the height value always, and the width value when
    the device provides it (width is ``None`` when not measured).
    """

    __tablename__ = "measurement_points"
    __table_args__ = (
        Index("idx_session_point", "session_id", "point_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("measurement_sessions.id"),
                        nullable=False)
    point_index = Column(Integer, nullable=False)
    height_value = Column(Float, nullable=False)
    width_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("MeasurementSession", back_populates="points")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "point_index": self.point_index,
            "height_value": self.height_value,
            "width_value": self.width_value,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }

    def __repr__(self):
        return (f"<MeasurementPoint(idx={self.point_index}, "
                f"height={self.height_value}, width={self.width_value})>")
