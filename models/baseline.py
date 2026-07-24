"""ProductBaseline ORM model — baseline/tolerance values per product."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from models.database import Base


class ProductBaseline(Base):
    """Baseline reference value and tolerance for a specific product."""

    __tablename__ = "product_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(128), unique=True, nullable=False)
    baseline_value = Column(Float, nullable=False, default=0.0)
    tolerance_upper = Column(Float, nullable=False, default=0.0)
    tolerance_lower = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_name": self.product_name,
            "baseline_value": self.baseline_value,
            "tolerance_upper": self.tolerance_upper,
            "tolerance_lower": self.tolerance_lower,
        }

    def __repr__(self):
        return (f"<ProductBaseline(name={self.product_name}, "
                f"baseline={self.baseline_value})>")
