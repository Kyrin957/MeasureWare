"""ResultPanel: displays max value, baseline, and OK/NG judgment."""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Slot


class ResultPanel(QFrame):
    """Panel showing measurement result: max value, baseline, OK/NG."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        outer_layout = QVBoxLayout(self)

        title = QLabel("判定结果")
        title.setStyleSheet("font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(title)

        # Values row
        values_layout = QHBoxLayout()

        # Max value
        max_group = QVBoxLayout()
        max_label = QLabel("最大值")
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setStyleSheet("color: gray; font-size: 10px;")
        self._max_value_label = QLabel("--")
        self._max_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._max_value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        max_group.addWidget(max_label)
        max_group.addWidget(self._max_value_label)
        values_layout.addLayout(max_group)

        # Baseline
        baseline_group = QVBoxLayout()
        baseline_label = QLabel("基准值")
        baseline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baseline_label.setStyleSheet("color: gray; font-size: 10px;")
        self._baseline_value_label = QLabel("--")
        self._baseline_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._baseline_value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        baseline_group.addWidget(baseline_label)
        baseline_group.addWidget(self._baseline_value_label)
        values_layout.addLayout(baseline_group)

        outer_layout.addLayout(values_layout)

        # Judgment indicator
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
        # self._info_label = QLabel("")
        # self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self._info_label.setStyleSheet("color: gray; font-size: 10px;")
        # outer_layout.addWidget(self._info_label)

    @Slot(dict)
    def on_session_completed(self, summary: dict):
        """Update display with session results."""
        max_val = summary.get("max_measured_value")
        baseline_val = summary.get("baseline_value")
        judgment = summary.get("judgment", "--")
        point_count = summary.get("point_count", 0)

        # Update max value
        if max_val is not None:
            self._max_value_label.setText(f"{max_val:.4f} mm")
        else:
            self._max_value_label.setText("N/A")

        # Update baseline
        if baseline_val is not None:
            self._baseline_value_label.setText(f"{baseline_val:.4f} mm")
        else:
            self._baseline_value_label.setText("未设置")

        # Update judgment with color
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

        # self._info_label.setText(f"共 {point_count} 个点位")

    @Slot()
    def reset(self):
        """Reset display to default state."""
        self._max_value_label.setText("--")
        self._baseline_value_label.setText("--")
        self._judgment_label.setText("--")
        self._judgment_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; "
            "border-radius: 8px; padding: 8px; "
            "background-color: #E0E0E0; color: #666;"
        )
        self._info_label.setText("")
