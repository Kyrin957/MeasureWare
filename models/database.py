"""Database engine, session factory, and initialization."""

from sqlalchemy import create_engine, text
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

    # Migrate legacy schema (baseline+tolerance → upper limits, add width)
    _migrate_schema()

    # Seed default device config if none exists
    session = Session()
    try:
        if session.query(DeviceConfig).count() == 0:
            default_cfg = DeviceConfig()
            session.add(default_cfg)
            session.commit()
    finally:
        session.close()


def _table_columns(table_name: str) -> list[str]:
    """Return the column names of a table, or [] if it does not exist."""
    with engine.connect() as conn:
        result = conn.exec_driver_sql(f"PRAGMA table_info({table_name})")
        return [row[1] for row in result]


def _migrate_schema():
    """Migrate legacy tables to the height/width upper-limit schema.

    Legacy layout (baseline + tolerances, height only):
      product_baselines:     product_name, baseline_value, tolerance_upper, tolerance_lower
      measurement_sessions:  product_name, baseline_value, tolerance_upper, tolerance_lower, max_measured_value
      measurement_points:    measured_value

    New layout (upper limits only, height + width):
      product_baselines:     spec_name, height_upper_limit, width_upper_limit
      measurement_sessions:  spec_name, height_upper_limit, width_upper_limit, max_height_value, max_width_value
      measurement_points:    height_value, width_value

    Legacy upper bounds are converted as ``baseline_value + tolerance_upper``
    so historical limits stay meaningful. Width limits default to 0
    (= width not checked). Every step is idempotent.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        with engine.begin() as conn:
            # ---- measurement_points ----
            cols = _table_columns("measurement_points")
            if "x_position" in cols:  # legacy column removed long ago
                conn.execute(text("ALTER TABLE measurement_points DROP COLUMN x_position"))
                cols.remove("x_position")
            if "measured_value" in cols and "height_value" not in cols:
                conn.execute(text(
                    "ALTER TABLE measurement_points RENAME COLUMN measured_value TO height_value"))
                logger.info("已重命名 measurement_points.measured_value → height_value")
            if "width_value" not in cols and cols:
                conn.execute(text("ALTER TABLE measurement_points ADD COLUMN width_value FLOAT"))
                logger.info("已添加 measurement_points.width_value 列")

            # ---- measurement_sessions ----
            cols = _table_columns("measurement_sessions")
            if "product_name" in cols and "spec_name" not in cols:
                conn.execute(text(
                    "ALTER TABLE measurement_sessions RENAME COLUMN product_name TO spec_name"))
                logger.info("已重命名 measurement_sessions.product_name → spec_name")
            if "max_measured_value" in cols and "max_height_value" not in cols:
                conn.execute(text(
                    "ALTER TABLE measurement_sessions RENAME COLUMN max_measured_value TO max_height_value"))
                logger.info("已重命名 measurement_sessions.max_measured_value → max_height_value")
            if "height_upper_limit" not in cols and cols:
                conn.execute(text(
                    "ALTER TABLE measurement_sessions ADD COLUMN height_upper_limit FLOAT"))
                if "baseline_value" in cols:
                    # Convert legacy baseline + upper tolerance to an upper limit
                    conn.execute(text(
                        "UPDATE measurement_sessions SET height_upper_limit = "
                        "COALESCE(baseline_value, 0) + COALESCE(tolerance_upper, 0)"))
                logger.info("已添加 measurement_sessions.height_upper_limit 列")
            if "width_upper_limit" not in cols and cols:
                conn.execute(text(
                    "ALTER TABLE measurement_sessions ADD COLUMN width_upper_limit FLOAT DEFAULT 0"))
                logger.info("已添加 measurement_sessions.width_upper_limit 列")
            if "max_width_value" not in cols and cols:
                conn.execute(text(
                    "ALTER TABLE measurement_sessions ADD COLUMN max_width_value FLOAT"))
                logger.info("已添加 measurement_sessions.max_width_value 列")
            for legacy in ("baseline_value", "tolerance_upper", "tolerance_lower"):
                if legacy in _table_columns("measurement_sessions"):
                    conn.execute(text(
                        f"ALTER TABLE measurement_sessions DROP COLUMN {legacy}"))
                    logger.info(f"已删除 measurement_sessions.{legacy} 列")

            # ---- product_baselines ----
            cols = _table_columns("product_baselines")
            if "product_name" in cols and "spec_name" not in cols:
                conn.execute(text(
                    "ALTER TABLE product_baselines RENAME COLUMN product_name TO spec_name"))
                logger.info("已重命名 product_baselines.product_name → spec_name")
            if "height_upper_limit" not in cols and cols:
                conn.execute(text(
                    "ALTER TABLE product_baselines ADD COLUMN height_upper_limit FLOAT"))
                if "baseline_value" in cols:
                    # Convert legacy baseline + upper tolerance to an upper limit
                    conn.execute(text(
                        "UPDATE product_baselines SET height_upper_limit = "
                        "COALESCE(baseline_value, 0) + COALESCE(tolerance_upper, 0)"))
                logger.info("已添加 product_baselines.height_upper_limit 列")
            if "width_upper_limit" not in cols and cols:
                conn.execute(text(
                    "ALTER TABLE product_baselines ADD COLUMN width_upper_limit FLOAT DEFAULT 0"))
                logger.info("已添加 product_baselines.width_upper_limit 列")
            for legacy in ("baseline_value", "tolerance_upper", "tolerance_lower"):
                if legacy in _table_columns("product_baselines"):
                    conn.execute(text(
                        f"ALTER TABLE product_baselines DROP COLUMN {legacy}"))
                    logger.info(f"已删除 product_baselines.{legacy} 列")

    except Exception as e:
        # Not fatal — table may not exist yet (first run)
        logger.debug(f"数据库结构迁移跳过: {e}")
