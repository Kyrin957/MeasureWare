"""ResultPanel: displays height/width max values, limits, and OK/NG judgment.

The final judgment is the logical AND of the height result and the width
result (width is only checked when its upper limit is greater than zero).
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QFrame, QSizePolicy, QGroupBox,
                               QFormLayout)
from PySide6.QtCore import Qt, Slot


class ResultPanel(QFrame):
    """Panel showing height/width results and the combined OK/NG judgment."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        outer_layout = QVBoxLayout(self)

        title = QLabel("判定结果")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(title)

        # Height metric group
        (self._height_max_label, self._height_limit_label,
         self._height_chip) = self._build_metric_group("高度", "height")
        outer_layout.addWidget(self._height_group)

        # Width metric group
        (self._width_max_label, self._width_limit_label,
         self._width_chip) = self._build_metric_group("宽度", "width")
        outer_layout.addWidget(self._width_group)

        # Combined judgment indicator
        self._judgment_label = QLabel("--")
        self._judgment_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._judgment_label.setMinimumHeight(50)
        self._judgment_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; "
            "border-radius: 8px; padding: 8px; "
            "background-color: #E0E0E0;"
        )
        self._judgment_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        outer_layout.addWidget(self._judgment_label)

        # Point count
        self._info_label = QLabel("")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setStyleSheet("color: gray; font-size: 12px;")
        outer_layout.addWidget(self._info_label)

        outer_layout.addStretch()

    def _build_metric_group(self, title: str, attr: str):
        """Build one metric block (max value + limit + OK/NG chip).

        Stores the group box as ``_<attr>_group``.
        Returns (max_label, limit_label, chip_label).
        """
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        max_label = QLabel("--")
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addRow("最大值", max_label)

        limit_label = QLabel("--")
        limit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        limit_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addRow("上限值", limit_label)

        chip = QLabel("--")
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(
            "font-size: 14px; font-weight: bold; border-radius: 4px; "
            "padding: 2px; background-color: #E0E0E0; color: #666;"
        )
        layout.addRow("判定", chip)

        setattr(self, f"_{attr}_group", group)
        return (max_label, limit_label, chip)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chip(chip: QLabel, text: str, bg: str, fg: str):
        chip.setText(text)
        chip.setStyleSheet(
            "font-size: 14px; font-weight: bold; border-radius: 4px; "
            f"padding: 2px; background-color: {bg}; color: {fg};"
        )

    def _set_chip_verdict(self, chip: QLabel, ok: bool | None):
        """ok: True → OK, False → NG, None → undetermined."""
        if ok is True:
            self._chip(chip, "OK", "#4CAF50", "white")
        elif ok is False:
            self._chip(chip, "NG", "#F44336", "white")
        else:
            self._chip(chip, "--", "#E0E0E0", "#666")

    @staticmethod
    def _value_style(over_limit: bool) -> str:
        color = "#F44336" if over_limit else "#333333"
        return f"font-size: 16px; font-weight: bold; color: {color};"

    # ------------------------------------------------------------------
    # Public slots
    # ------------------------------------------------------------------

    @Slot(dict)
    def on_session_completed(self, summary: dict):
        """Update display with session results."""
        max_height = summary.get("max_height_value")
        height_limit = summary.get("height_upper_limit")
        max_width = summary.get("max_width_value")
        width_limit = summary.get("width_upper_limit")
        judgment = summary.get("judgment", "--")
        point_count = summary.get("point_count", 0)

        # ---- Height ----
        if max_height is not None:
            self._height_max_label.setText(f"{max_height:.3f} mm")
        else:
            self._height_max_label.setText("N/A")

        if height_limit is not None:
            self._height_limit_label.setText(f"≤ {height_limit:.3f} mm")
        else:
            self._height_limit_label.setText("未设置")

        if max_height is None or height_limit is None:
            height_ok = None
            self._height_max_label.setStyleSheet(self._value_style(False))
        else:
            height_ok = max_height <= height_limit
            self._height_max_label.setStyleSheet(self._value_style(not height_ok))
        self._set_chip_verdict(self._height_chip, height_ok)

        # ---- Width ----
        width_enabled = bool(width_limit and width_limit > 0)

        if max_width is not None:
            self._width_max_label.setText(f"{max_width:.3f} mm")
        else:
            self._width_max_label.setText("N/A")

        if width_enabled:
            self._width_limit_label.setText(f"≤ {width_limit:.3f} mm")
        else:
            self._width_limit_label.setText("不检查")

        if not width_enabled:
            width_ok = None
            self._width_max_label.setStyleSheet(self._value_style(False))
            self._chip(self._width_chip, "不检查", "#E0E0E0", "#666")
        elif max_width is None:
            width_ok = None
            self._width_max_label.setStyleSheet(self._value_style(False))
            self._set_chip_verdict(self._width_chip, None)
        else:
            width_ok = max_width <= width_limit
            self._width_max_label.setStyleSheet(self._value_style(not width_ok))
            self._set_chip_verdict(self._width_chip, width_ok)

        # ---- Combined judgment ----
        if judgment == "OK":
            self._judgment_label.setText("●  OK  合格")
            self._judgment_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; "
                "border-radius: 8px; padding: 8px; "
                "background-color: #4CAF50; color: white;"
            )
        elif judgment == "NG":
            self._judgment_label.setText("●  NG  不合格")
            self._judgment_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; "
                "border-radius: 8px; padding: 8px; "
                "background-color: #F44336; color: white;"
            )
        else:
            self._judgment_label.setText("--  未判定")
            self._judgment_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; "
                "border-radius: 8px; padding: 8px; "
                "background-color: #E0E0E0; color: #666;"
            )

        self._info_label.setText(f"共 {point_count} 个点位")

    @Slot()
    def reset(self):
        """Reset display to default state."""
        for max_label, limit_label, chip in (
            (self._height_max_label, self._height_limit_label, self._height_chip),
            (self._width_max_label, self._width_limit_label, self._width_chip),
        ):
            max_label.setText("--")
            max_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            limit_label.setText("--")
            self._set_chip_verdict(chip, None)

        self._judgment_label.setText("--")
        self._judgment_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; "
            "border-radius: 8px; padding: 8px; "
            "background-color: #E0E0E0; color: #666;"
        )
        self._info_label.setText("")
