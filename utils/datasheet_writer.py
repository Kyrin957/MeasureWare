"""Save measurement session data to local datasheets folder.

Directory hierarchy: datasheets/YYYY/MM/{OK|NG}/<batch_number>.csv

Each completed product measurement is routed to the ``OK`` or ``NG`` folder
based on the session-level ``judgment`` (the overall result of one product).
Any judgment other than ``OK`` (i.e. ``NG`` and the undecided ``--``) goes to
the ``NG`` folder.

Each CSV includes per-point height/width values along with the height/width
upper limits and max values — all rounded to 3 decimal places.
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
                    OK/
                        batch_xxx.csv
                    NG/
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


def _judgment_folder(judgment: str | None) -> str:
    """Map a session-level judgment to its result sub-folder name.

    Only ``OK`` goes to the ``OK`` folder. Every other value — ``NG`` and the
    undecided ``--`` (missing baseline or missing width data) — is routed to
    the ``NG`` folder so that nothing escapes operator confirmation.
    """
    return "OK" if judgment == "OK" else "NG"


def _build_filepath(
    batch_number: str,
    completed_at: datetime,
    judgment: str | None = None,
) -> str:
    """Build the absolute file path for a datasheet CSV.

    Creates intermediate directories (year/month/OK|NG) as needed.

    The ``judgment`` of one completed product decides whether the file lands
    under ``OK/`` or ``NG/``. All measurements of the same batch share one file
    — no suffix is appended; later writes append rows.
    """
    base = _get_datasheet_root()
    year_dir = completed_at.strftime("%Y")
    month_dir = completed_at.strftime("%m")
    dir_path = os.path.join(
        base, year_dir, month_dir, _judgment_folder(judgment)
    )
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

    The file is routed to ``datasheets/YYYY/MM/OK/<batch>.csv`` or
    ``datasheets/YYYY/MM/NG/<batch>.csv`` according to the session-level
    ``judgment``.

    Parameters
    ----------
    session_summary : dict
        Return value of ``MeasurementSession.to_summary_dict()``.
        Expected keys: ``batch_number``, ``spec_name``,
        ``height_upper_limit``, ``width_upper_limit``, ``judgment``.
    points : list[dict]
        List of ``MeasurementPoint.to_dict()`` dicts, each with
        ``point_index``, ``height_value`` and ``width_value``.
    completed_at : datetime, optional
        Timestamp used for the YYYY/MM folder hierarchy.
        Defaults to ``datetime.now()``.

    Returns
    -------
    str | None
        Absolute path to the saved CSV, or ``None`` on failure.
    """
    if completed_at is None:
        completed_at = datetime.now()

    try:
        # ---- Session-level fields (same for every row) ----
        judgment = session_summary.get("judgment", "--")

        batch_number = session_summary.get("batch_number", "unknown_batch")
        filepath = _build_filepath(batch_number, completed_at, judgment)

        spec_name = session_summary.get("spec_name", "")
        inspection_seq = session_summary.get("inspection_sequence", "")
        height_limit = session_summary.get("height_upper_limit")
        width_limit = session_summary.get("width_upper_limit")
        max_height = session_summary.get("max_height_value")
        max_width = session_summary.get("max_width_value")
        width_enabled = bool(width_limit and width_limit > 0)
        started_at = session_summary.get("started_at", "")

        rows = []
        for pt in points:
            height = pt.get("height_value")
            width = pt.get("width_value")

            rows.append({
                "批号": batch_number,
                "树脂规格要求": spec_name,
                "检测序号": inspection_seq,
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
