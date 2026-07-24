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

        for pt in points:
            rows.append({
                "批号": session_info.get("batch_number", ""),
                "品名": session_info.get("product_name", ""),
                "检测序号": session_info.get("inspection_sequence", ""),
                "点位序号": pt.get("point_index", ""),
                "X位置(mm)": pt.get("x_position", ""),
                "测量值(mm)": pt.get("measured_value", ""),
                "最大值(mm)": session_info.get("max_measured_value", ""),
                "基准值(mm)": session_info.get("baseline_value", ""),
                "判定": session_info.get("judgment", ""),
                "测量时间": session_info.get("started_at", ""),
            })

    if not rows:
        logger.warning("No data to export")
        return

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(rows)} rows to {filepath}")
