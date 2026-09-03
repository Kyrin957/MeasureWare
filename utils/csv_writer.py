"""CSV export using pandas for Excel compatibility with Chinese characters."""

import os
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def export_sessions_to_csv(sessions_data: list[dict], filepath: str):
    """Export measurement session data to CSV.

    Args:
        sessions_data: List of dicts with session summary + points details.
        filepath: Target CSV file path.
    """
    rows = []
    for session in sessions_data:
        session_info = session.get("session", {})
        points = session.get("points", [])

        height_limit = session_info.get("height_upper_limit")
        width_limit = session_info.get("width_upper_limit")
        max_height = session_info.get("max_height_value")
        max_width = session_info.get("max_width_value")
        width_enabled = bool(width_limit and width_limit > 0)

        for pt in points:
            height = pt.get("height_value")
            width = pt.get("width_value")

            rows.append({
                "批号": session_info.get("batch_number", ""),
                "树脂规格要求": session_info.get("spec_name", ""),
                "检测序号": session_info.get("inspection_sequence", ""),
                "点位序号": pt.get("point_index", ""),
                "高度(mm)": (
                    round(height, 3) if height is not None else ""
                ),
                "宽度(mm)": (
                    round(width, 3) if width is not None else ""
                ),
                "高度最大值(mm)": (
                    round(max_height, 3) if max_height is not None else ""
                ),
                "宽度最大值(mm)": (
                    round(max_width, 3) if max_width is not None else ""
                ),
                "高度上限(mm)": (
                    round(height_limit, 3) if height_limit is not None else ""
                ),
                "宽度上限(mm)": (
                    round(width_limit, 3) if width_limit is not None else ""
                ),
                "宽度检查": "是" if width_enabled else "否",
                "判定": session_info.get("judgment", ""),
                "测量时间": session_info.get("started_at", ""),
            })

    if not rows:
        logger.warning("没有可导出的数据")
        return

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"已导出 {len(rows)} 行数据到 {filepath}")
