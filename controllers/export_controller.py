"""ExportController: CSV export of measurement data."""

import logging

from models.database import Session
from models.measurement import MeasurementSession, MeasurementPoint
from utils.csv_writer import export_sessions_to_csv

logger = logging.getLogger(__name__)


class ExportController:
    """Handles CSV export of measurement sessions."""

    @staticmethod
    def export_session(session_id: int, filepath: str) -> bool:
        """Export a single session's data to CSV."""
        session_db = Session()
        try:
            session = session_db.query(MeasurementSession).get(session_id)
            if session is None:
                logger.error(f"Session #{session_id} not found")
                return False

            points = session_db.query(MeasurementPoint).filter_by(
                session_id=session_id
            ).order_by(MeasurementPoint.point_index).all()

            sessions_data = [{
                "session": session.to_summary_dict(),
                "points": [p.to_dict() for p in points],
            }]

            export_sessions_to_csv(sessions_data, filepath)
            return True
        except Exception as e:
            logger.exception(f"Export session #{session_id} failed: {e}")
            return False
        finally:
            session_db.close()

    @staticmethod
    def export_all(filepath: str) -> bool:
        """Export all sessions to CSV."""
        session_db = Session()
        try:
            sessions = session_db.query(MeasurementSession).order_by(
                MeasurementSession.started_at.desc()
            ).all()

            sessions_data = []
            for session in sessions:
                points = session_db.query(MeasurementPoint).filter_by(
                    session_id=session.id
                ).order_by(MeasurementPoint.point_index).all()
                sessions_data.append({
                    "session": session.to_summary_dict(),
                    "points": [p.to_dict() for p in points],
                })

            export_sessions_to_csv(sessions_data, filepath)
            return True
        except Exception as e:
            logger.exception(f"Export all sessions failed: {e}")
            return False
        finally:
            session_db.close()
