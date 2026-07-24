"""BaselineController: CRUD operations for ProductBaseline records."""

import logging

from models.database import Session
from models.baseline import ProductBaseline

logger = logging.getLogger(__name__)


class BaselineController:
    """CRUD controller for product baseline values."""

    @staticmethod
    def get_all() -> list[dict]:
        """Return all product baselines as list of dicts."""
        session_db = Session()
        try:
            baselines = session_db.query(ProductBaseline).order_by(
                ProductBaseline.product_name
            ).all()
            return [b.to_dict() for b in baselines]
        finally:
            session_db.close()

    @staticmethod
    def get_by_product_name(product_name: str) -> dict | None:
        """Look up baseline by product name. Returns dict or None."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).filter_by(
                product_name=product_name.strip()
            ).first()
            return baseline.to_dict() if baseline else None
        finally:
            session_db.close()

    @staticmethod
    def create(product_name: str, baseline_value: float,
               tolerance_upper: float = 0.0,
               tolerance_lower: float = 0.0) -> tuple[bool, str]:
        """Create a new product baseline. Returns (success, message)."""
        session_db = Session()
        try:
            # Check for duplicate
            existing = session_db.query(ProductBaseline).filter_by(
                product_name=product_name.strip()
            ).first()
            if existing:
                return (False, f"品名 '{product_name}' 已存在")

            baseline = ProductBaseline(
                product_name=product_name.strip(),
                baseline_value=baseline_value,
                tolerance_upper=tolerance_upper,
                tolerance_lower=tolerance_lower,
            )
            session_db.add(baseline)
            session_db.commit()
            logger.info(f"Created baseline: {product_name} = {baseline_value}")
            return (True, f"已添加品名 '{product_name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"Create baseline failed: {e}")
            return (False, f"添加失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def update(baseline_id: int, **kwargs) -> tuple[bool, str]:
        """Update a product baseline. kwargs: product_name, baseline_value, etc."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).get(baseline_id)
            if baseline is None:
                return (False, f"基线记录 #{baseline_id} 不存在")

            # Check uniqueness if product name is being changed
            new_name = kwargs.get("product_name")
            if new_name and new_name != baseline.product_name:
                dup = session_db.query(ProductBaseline).filter_by(
                    product_name=new_name.strip()
                ).first()
                if dup:
                    return (False, f"品名 '{new_name}' 已存在")

            for key, value in kwargs.items():
                if hasattr(baseline, key) and key != "id":
                    setattr(baseline, key, value)

            session_db.commit()
            logger.info(f"Updated baseline #{baseline_id}")
            return (True, f"已更新品名 '{baseline.product_name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"Update baseline failed: {e}")
            return (False, f"更新失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def delete(baseline_id: int) -> tuple[bool, str]:
        """Delete a product baseline."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).get(baseline_id)
            if baseline is None:
                return (False, f"基线记录 #{baseline_id} 不存在")

            name = baseline.product_name
            session_db.delete(baseline)
            session_db.commit()
            logger.info(f"Deleted baseline: {name}")
            return (True, f"已删除品名 '{name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"Delete baseline failed: {e}")
            return (False, f"删除失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def save_all(baselines_data: list[dict]) -> tuple[bool, str]:
        """Batch save: replace all baselines with the given list.

        Each dict: {id or None, product_name, baseline_value, tolerance_upper, tolerance_lower}
        """
        session_db = Session()
        try:
            # Get existing IDs from the data
            submitted_ids = {
                item["id"] for item in baselines_data
                if item.get("id") is not None
            }

            # Delete baselines that are no longer in the list
            all_existing = session_db.query(ProductBaseline).all()
            for existing in all_existing:
                if existing.id not in submitted_ids:
                    session_db.delete(existing)

            # Update or create
            for item in baselines_data:
                if item.get("id"):
                    # Update existing
                    baseline = session_db.query(ProductBaseline).get(item["id"])
                    if baseline:
                        baseline.product_name = item["product_name"].strip()
                        baseline.baseline_value = item["baseline_value"]
                        baseline.tolerance_upper = item.get("tolerance_upper", 0.0)
                        baseline.tolerance_lower = item.get("tolerance_lower", 0.0)
                else:
                    # Create new
                    baseline = ProductBaseline(
                        product_name=item["product_name"].strip(),
                        baseline_value=item["baseline_value"],
                        tolerance_upper=item.get("tolerance_upper", 0.0),
                        tolerance_lower=item.get("tolerance_lower", 0.0),
                    )
                    session_db.add(baseline)

            session_db.commit()
            return (True, "基准值已保存")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"Batch save baselines failed: {e}")
            return (False, f"保存失败: {e}")
        finally:
            session_db.close()
