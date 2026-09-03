"""ProductBaseline ORM model — upper-limit specs per resin specification.

Each resin specification (树脂规格要求) carries two upper limits:
- ``height_upper_limit``: max allowed height (mm)
- ``width_upper_limit``  : max allowed width (mm); 0 means width is not checked
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from models.database import Base


class ProductBaseline(Base):
    """Upper-limit specification for a resin specification requirement."""

    __tablename__ = "product_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spec_name = Column(String(128), unique=True, nullable=False)
    height_upper_limit = Column(Float, nullable=False, default=0.0)
    width_upper_limit = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @property
    def width_check_enabled(self) -> bool:
        """Width inspection is disabled when the limit is set to zero."""
        return bool(self.width_upper_limit and self.width_upper_limit > 0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "spec_name": self.spec_name,
            "height_upper_limit": self.height_upper_limit,
            "width_upper_limit": self.width_upper_limit,
        }

    def __repr__(self):
        return (f"<ProductBaseline(spec={self.spec_name}, "
                f"height_limit={self.height_upper_limit}, "
                f"width_limit={self.width_upper_limit})>")
