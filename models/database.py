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

    # Seed default device config if none exists
    session = Session()
    try:
        if session.query(DeviceConfig).count() == 0:
            default_cfg = DeviceConfig()
            session.add(default_cfg)
            session.commit()
    finally:
        session.close()
