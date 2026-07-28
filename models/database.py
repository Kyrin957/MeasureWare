"""Database engine, session factory, and initialization."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///measureware.db"

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables and seed default DeviceConfig if empty."""
    from models.settings_model import DeviceConfig  # noqa: F401
    from models.baseline import ProductBaseline  # noqa: F401
    from models.measurement import MeasurementSession, MeasurementPoint  # noqa: F401

    Base.metadata.create_all(engine)

    # Migrate: drop x_position column if it exists (removed from schema)
    # SQLite 3.35.0+ supports ALTER TABLE ... DROP COLUMN
    _migrate_drop_x_position()

    # Seed default device config if none exists
    session = Session()
    try:
        if session.query(DeviceConfig).count() == 0:
            default_cfg = DeviceConfig()
            session.add(default_cfg)
            session.commit()
    finally:
        session.close()


def _migrate_drop_x_position():
    """Drop the x_position column from measurement_points if it exists."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Check if the column exists by inspecting table info
        with engine.connect() as conn:
            result = conn.exec_driver_sql(
                "PRAGMA table_info(measurement_points)"
            )
            columns = [row[1] for row in result]

        if "x_position" in columns:
            with engine.connect() as conn:
                conn.exec_driver_sql(
                    "ALTER TABLE measurement_points DROP COLUMN x_position"
                )
                conn.commit()
            logger.info("已删除 measurement_points.x_position 列")
    except Exception as e:
        # Not fatal — table may not exist yet (first run)
        logger.debug(f"x_position 列迁移跳过: {e}")
