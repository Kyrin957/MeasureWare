"""Save measurement session data to local datasheets folder.

Directory hierarchy: datasheets/YYYY/MM/<batch_number>.csv

Each CSV includes per-point measured values along with baseline, upper/lower
tolerances, and deviation — all rounded to 3 decimal places.
"""

import os
import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def _get_datasheet_root() -> str:
    """Return the absolute path to the datasheets root directory.

    In development mode, datasheets live under the project root.
    When frozen (PyInstaller), datasheets live in the exe's working directory.

    Directory hierarchy::

        datasheets/
            YYYY/
                MM/
                    batch_xxx.csv
    """
    import sys

    if getattr(sys, "frozen", False):
        # Exe mode: use current working directory (where exe is launched)
        return os.path.join(os.getcwd(), "datasheets")
    else:
        # Dev mode: project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, "datasheets")


def _build_filepath(batch_number: str, completed_at: datetime) -> str:
    """Build the absolute file path for a datasheet CSV.

    Creates intermediate directories (year/month) as needed.

    All measurements of the same batch share one file — no suffix is
    appended; later writes append rows.
    """
    base = _get_datasheet_root()
    year_dir = completed_at.strftime("%Y")
    month_dir = completed_at.strftime("%m")
    dir_path = os.path.join(base, year_dir, month_dir)
    os.makedirs(dir_path, exist_ok=True)

    # Sanitize batch number for use as a filename
    safe = "".join(c for c in batch_number if c.isalnum() or c in "._- ")
    safe = safe.strip().replace(" ", "_") or "unknown_batch"

    return os.path.join(dir_path, f"{safe}.csv")


def save_session_to_datasheet(
    session_summary: dict,
    points: list[dict],
    completed_at: datetime | None = None,
) -> str | None:
    """Save a completed measurement session to the local datasheets folder.

    Parameters
    ----------
    session_summary : dict
        Return value of ``MeasurementSession.to_summary_dict()``.
        Expected keys: ``batch_number``, ``baseline_value``,
        ``tolerance_upper``, ``tolerance_lower``, ``judgment``.
    points : list[dict]
        List of ``MeasurementPoint.to_dict()`` dicts, each with
        ``point_index`` and ``measured_value``.
    completed_at : datetime, optional
        Timestamp used for folder hierarchy and filename disambiguation.
        Defaults to ``datetime.now()``.

    Returns
    -------
    str | None
        Absolute path to the saved CSV, or ``None`` on failure.
    """
    if completed_at is None:
        completed_at = datetime.now()

    try:
        batch_number = session_summary.get("batch_number", "unknown_batch")
        filepath = _build_filepath(batch_number, completed_at)

        # ---- Session-level fields (same for every row) ----
        product_name = session_summary.get("product_name", "")
        inspection_seq = session_summary.get("inspection_sequence", "")
        baseline = session_summary.get("baseline_value")
        tol_upper = session_summary.get("tolerance_upper")
        tol_lower = session_summary.get("tolerance_lower")
        max_val = session_summary.get("max_measured_value")
        judgment = session_summary.get("judgment", "--")
        started_at = session_summary.get("started_at", "")

        rows = []
        for pt in points:
            measured = pt.get("measured_value")

            # Deviation from baseline
            deviation = None
            if measured is not None and baseline is not None:
                deviation = round(measured - baseline, 3)

            rows.append({
                "批号": batch_number,
                "品名": product_name,
                "检测序号": inspection_seq,
                "点位序号": pt.get("point_index", ""),
                "测量值(mm)": (
                    round(measured, 3) if measured is not None else ""
                ),
                "最大值(mm)": (
                    round(max_val, 3) if max_val is not None else ""
                ),
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
                "判定": judgment,
                "测量时间": started_at,
            })

        if not rows:
            logger.warning("没有点位数据可保存到 %s", filepath)
            return None

        df = pd.DataFrame(rows)

        # Same batch → same file: create new or append without duplicating header
        file_exists = os.path.exists(filepath)
        df.to_csv(
            filepath,
            index=False,
            encoding="utf-8-sig",
            mode="a" if file_exists else "w",
            header=not file_exists,
        )

        action = "追加到" if file_exists else "保存到"
        logger.info("测量数据已%s: %s", action, filepath)
        return filepath

    except Exception:
        logger.exception("保存测量数据到本地失败")
        return None
