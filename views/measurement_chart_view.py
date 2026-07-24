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

    @Slot(int, float, float)
    def add_point(self, point_index: int, value: float, x_position: float):
        """Add a new measurement point to the chart."""
        self._all_values.append((point_index, value))

        # Append to line series
        self._line_series.append(float(point_index), value)

        # Trim old points if too many
        if self._line_series.count() > self.MAX_POINTS_DISPLAY:
            self._line_series.removePoints(0, 500)

        # Adjust X axis range
        if point_index > self._axis_x.max():
            self._axis_x.setRange(0, point_index + 50)

        # Adjust Y axis range if needed
        y_min, y_max = self._get_y_range()
        if value > self._axis_y.max() or value < self._axis_y.min():
            margin = max((y_max - y_min) * 0.1, 0.1)
            self._axis_y.setRange(
                max(0, y_min - margin),
                y_max + margin
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

    def _get_y_range(self) -> tuple:
        """Get the min/max Y values from stored data."""
        if not self._all_values:
            return (0.0, 10.0)
        values = [v for _, v in self._all_values]
        return (min(values), max(values))
