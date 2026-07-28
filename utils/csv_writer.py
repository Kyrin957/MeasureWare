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

        baseline = session_info.get("baseline_value")
        tol_upper = session_info.get("tolerance_upper")
        tol_lower = session_info.get("tolerance_lower")

        for pt in points:
            measured = pt.get("measured_value")

            # Deviation from baseline
            deviation = None
            if measured is not None and baseline is not None:
                deviation = round(measured - baseline, 3)

            rows.append({
                "批号": session_info.get("batch_number", ""),
                "品名": session_info.get("product_name", ""),
                "检测序号": session_info.get("inspection_sequence", ""),
                "点位序号": pt.get("point_index", ""),
                "测量值(mm)": (
                    round(measured, 3) if measured is not None else ""
                ),
                "最大值(mm)": session_info.get("max_measured_value", ""),
                "基准值(mm)": (
                    round(baseline, 3) if baseline is not None else ""
                ),
                "上公差(mm)": (
                    round(tol_upper, 3) if tol_upper is not None else ""
                ),
                "下公差(mm)": (
                    round(tol_lower, 3) if tol_lower is not None else ""
                ),
                "偏差(mm)": deviation if deviation is not None else "",
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
