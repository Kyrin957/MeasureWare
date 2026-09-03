"""BaselineController: CRUD operations for ProductBaseline records."""

import logging

from models.database import Session
from models.baseline import ProductBaseline

logger = logging.getLogger(__name__)


class BaselineController:
    """CRUD controller for resin specification limits."""

    @staticmethod
    def get_all() -> list[dict]:
        """Return all specification limits as list of dicts."""
        session_db = Session()
        try:
            baselines = session_db.query(ProductBaseline).order_by(
                ProductBaseline.spec_name
            ).all()
            return [b.to_dict() for b in baselines]
        finally:
            session_db.close()

    @staticmethod
    def get_by_spec_name(spec_name: str) -> dict | None:
        """Look up limits by spec name. Returns dict or None."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).filter_by(
                spec_name=spec_name.strip()
            ).first()
            return baseline.to_dict() if baseline else None
        finally:
            session_db.close()

    @staticmethod
    def create(spec_name: str, height_upper_limit: float,
               width_upper_limit: float = 0.0) -> tuple[bool, str]:
        """Create a new spec record. Returns (success, message)."""
        session_db = Session()
        try:
            # Check for duplicate
            existing = session_db.query(ProductBaseline).filter_by(
                spec_name=spec_name.strip()
            ).first()
            if existing:
                return (False, f"树脂规格要求 '{spec_name}' 已存在")

            baseline = ProductBaseline(
                spec_name=spec_name.strip(),
                height_upper_limit=height_upper_limit,
                width_upper_limit=width_upper_limit,
            )
            session_db.add(baseline)
            session_db.commit()
            logger.info(f"已创建规格要求: {spec_name} 高度上限={height_upper_limit} "
                        f"宽度上限={width_upper_limit}")
            return (True, f"已添加树脂规格要求 '{spec_name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"创建规格要求失败: {e}")
            return (False, f"添加失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def update(baseline_id: int, **kwargs) -> tuple[bool, str]:
        """Update a spec record. kwargs: spec_name, height_upper_limit, etc."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).get(baseline_id)
            if baseline is None:
                return (False, f"规格记录 #{baseline_id} 不存在")

            # Check uniqueness if spec name is being changed
            new_name = kwargs.get("spec_name")
            if new_name and new_name != baseline.spec_name:
                dup = session_db.query(ProductBaseline).filter_by(
                    spec_name=new_name.strip()
                ).first()
                if dup:
                    return (False, f"树脂规格要求 '{new_name}' 已存在")

            for key, value in kwargs.items():
                if hasattr(baseline, key) and key != "id":
                    setattr(baseline, key, value)

            session_db.commit()
            logger.info(f"已更新规格要求 #{baseline_id}")
            return (True, f"已更新树脂规格要求 '{baseline.spec_name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"更新规格要求失败: {e}")
            return (False, f"更新失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def delete(baseline_id: int) -> tuple[bool, str]:
        """Delete a spec record."""
        session_db = Session()
        try:
            baseline = session_db.query(ProductBaseline).get(baseline_id)
            if baseline is None:
                return (False, f"规格记录 #{baseline_id} 不存在")

            name = baseline.spec_name
            session_db.delete(baseline)
            session_db.commit()
            logger.info(f"已删除规格要求: {name}")
            return (True, f"已删除树脂规格要求 '{name}'")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"删除规格要求失败: {e}")
            return (False, f"删除失败: {e}")
        finally:
            session_db.close()

    @staticmethod
    def save_all(baselines_data: list[dict]) -> tuple[bool, str]:
        """Batch save: replace all spec records with the given list.

        Each dict: {id or None, spec_name, height_upper_limit, width_upper_limit}
        """
        session_db = Session()
        try:
            # Get existing IDs from the data
            submitted_ids = {
                item["id"] for item in baselines_data
                if item.get("id") is not None
            }

            # Delete records that are no longer in the list
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
                        baseline.spec_name = item["spec_name"].strip()
                        baseline.height_upper_limit = item["height_upper_limit"]
                        baseline.width_upper_limit = item.get("width_upper_limit", 0.0)
                else:
                    # Create new
                    baseline = ProductBaseline(
                        spec_name=item["spec_name"].strip(),
                        height_upper_limit=item["height_upper_limit"],
                        width_upper_limit=item.get("width_upper_limit", 0.0),
                    )
                    session_db.add(baseline)

            session_db.commit()
            return (True, "规格要求已保存")
        except Exception as e:
            session_db.rollback()
            logger.exception(f"批量保存规格要求失败: {e}")
            return (False, f"保存失败: {e}")
        finally:
            session_db.close()
