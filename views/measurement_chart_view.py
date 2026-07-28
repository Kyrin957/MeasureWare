"""MeasurementChartView: real-time line chart with max-value marker."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Slot
from PySide6.QtCharts import (QChart, QChartView, QLineSeries,
                              QScatterSeries, QValueAxis)
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtCore import Qt


class MeasurementChartView(QWidget):
    """Real-time measurement line chart using QtCharts."""

    MAX_POINTS_DISPLAY = 2000  # Max visible points before we start trimming

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._all_values = []  # Store (index, value) for max tracking
        self._min_y = float("inf")
        self._max_y = -float("inf")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("实时测量曲线")
        title.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(title)

        # Create chart
        self._chart = QChart()
        self._chart.setTitle("")
        self._chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self._chart.legend().setVisible(True)
        self._chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        # Line series for measurement values
        self._line_series = QLineSeries()
        self._line_series.setName("测量值")
        pen = QPen(QColor("#2196F3"))
        pen.setWidth(2)
        self._line_series.setPen(pen)
        self._chart.addSeries(self._line_series)

        # Scatter series for max value marker
        self._max_scatter = QScatterSeries()
        self._max_scatter.setName("最大值")
        self._max_scatter.setMarkerSize(12)
        self._max_scatter.setColor(QColor("#F44336"))
        self._max_scatter.setBorderColor(QColor("#B71C1C"))
        self._chart.addSeries(self._max_scatter)

        # Axes
        self._axis_x = QValueAxis()
        self._axis_x.setTitleText("点位序号")
        self._axis_x.setLabelFormat("%d")
        self._axis_x.setRange(0, 200)
        self._axis_x.setTickCount(11)
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("测量值 (mm)")
        self._axis_y.setLabelFormat("%.3f")
        self._axis_y.setRange(0, 10)
        self._axis_y.setTickCount(11)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)

        self._line_series.attachAxis(self._axis_x)
        self._line_series.attachAxis(self._axis_y)
        self._max_scatter.attachAxis(self._axis_x)
        self._max_scatter.attachAxis(self._axis_y)

        # Chart view
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self._chart_view)

        # Track value range incrementally — avoids O(n) scan on every point
        self._min_y = float("inf")
        self._max_y = -float("inf")

    @Slot(int, float)
    def add_point(self, point_index: int, value: float):
        """Add a new measurement point to the chart."""
        self._all_values.append((point_index, value))

        # Update running min/max (O(1) instead of O(n) scan)
        if value < self._min_y:
            self._min_y = value
        if value > self._max_y:
            self._max_y = value

        # Append to line series
        self._line_series.append(float(point_index), value)

        # Trim old points if too many
        if self._line_series.count() > self.MAX_POINTS_DISPLAY:
            self._line_series.removePoints(0, 500)

        # Adjust X axis range
        if point_index > self._axis_x.max():
            self._axis_x.setRange(0, point_index + 50)

        # Adjust Y axis range if the new point pushes beyond current bounds
        y_lo = self._axis_y.min()
        y_hi = self._axis_y.max()
        if value < y_lo or value > y_hi:
            margin = max((self._max_y - self._min_y) * 0.1, 0.1)
            self._axis_y.setRange(
                max(0, self._min_y - margin),
                self._max_y + margin
            )

    @Slot(float, float)
    def mark_max(self, max_value: float, max_index: int):
        """Mark the maximum value point on the chart."""
        self._max_scatter.clear()
        if max_value is not None and max_index > 0:
            self._max_scatter.append(float(max_index), max_value)

    @Slot()
    def reset(self):
        """Clear the chart for a new measurement."""
        self._line_series.clear()
        self._max_scatter.clear()
        self._all_values.clear()
        self._axis_x.setRange(0, 200)
        self._axis_y.setRange(0, 10)
        self._min_y = float("inf")
        self._max_y = -float("inf")
