"""MeasurementChartView: real-time dual-axis line chart with max-value markers.

Height is plotted against the left axis (scale 0–2 mm) and width against the
right axis (scale 0–4 mm).  Both max values are marked with scatter points.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Slot
from PySide6.QtCharts import (QChart, QChartView, QLineSeries,
                              QScatterSeries, QValueAxis)
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtCore import Qt


class MeasurementChartView(QWidget):
    """Real-time height/width measurement chart using QtCharts."""

    MAX_POINTS_DISPLAY = 2000  # Max visible points before we start trimming

    HEIGHT_AXIS_MAX = 2.0      # Left axis full scale (mm)
    WIDTH_AXIS_MAX = 4.0       # Right axis full scale (mm)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

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

        # Line series — height (left axis)
        self._height_series = QLineSeries()
        self._height_series.setName("高度")
        pen = QPen(QColor("#2196F3"))
        pen.setWidth(2)
        self._height_series.setPen(pen)
        self._chart.addSeries(self._height_series)

        # Line series — width (right axis)
        self._width_series = QLineSeries()
        self._width_series.setName("宽度")
        pen = QPen(QColor("#FF9800"))
        pen.setWidth(2)
        self._width_series.setPen(pen)
        self._chart.addSeries(self._width_series)

        # Scatter series for max value markers
        self._max_height_scatter = QScatterSeries()
        self._max_height_scatter.setName("高度最大值")
        self._max_height_scatter.setMarkerSize(12)
        self._max_height_scatter.setColor(QColor("#F44336"))
        self._max_height_scatter.setBorderColor(QColor("#B71C1C"))
        self._chart.addSeries(self._max_height_scatter)

        self._max_width_scatter = QScatterSeries()
        self._max_width_scatter.setName("宽度最大值")
        self._max_width_scatter.setMarkerSize(12)
        self._max_width_scatter.setColor(QColor("#F44336"))
        self._max_width_scatter.setBorderColor(QColor("#B71C1C"))
        self._chart.addSeries(self._max_width_scatter)

        # Axes
        self._axis_x = QValueAxis()
        self._axis_x.setTitleText("点位序号")
        self._axis_x.setLabelFormat("%d")
        self._axis_x.setRange(0, 200)
        self._axis_x.setTickCount(11)
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        # Left axis — height scale
        self._axis_y_height = QValueAxis()
        self._axis_y_height.setTitleText("高度 (mm)")
        self._axis_y_height.setLabelFormat("%.2f")
        self._axis_y_height.setRange(0, self.HEIGHT_AXIS_MAX)
        self._axis_y_height.setTickCount(11)
        self._chart.addAxis(self._axis_y_height, Qt.AlignmentFlag.AlignLeft)

        # Right axis — width scale
        self._axis_y_width = QValueAxis()
        self._axis_y_width.setTitleText("宽度 (mm)")
        self._axis_y_width.setLabelFormat("%.2f")
        self._axis_y_width.setRange(0, self.WIDTH_AXIS_MAX)
        self._axis_y_width.setTickCount(11)
        self._chart.addAxis(self._axis_y_width, Qt.AlignmentFlag.AlignRight)

        # Attach series to their axes
        self._height_series.attachAxis(self._axis_x)
        self._height_series.attachAxis(self._axis_y_height)
        self._width_series.attachAxis(self._axis_x)
        self._width_series.attachAxis(self._axis_y_width)
        self._max_height_scatter.attachAxis(self._axis_x)
        self._max_height_scatter.attachAxis(self._axis_y_height)
        self._max_width_scatter.attachAxis(self._axis_x)
        self._max_width_scatter.attachAxis(self._axis_y_width)

        # Chart view
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self._chart_view)

    @Slot(int, float, object)
    def add_point(self, point_index: int, height: float, width):
        """Add a new measurement point (height + width) to the chart."""
        # Append to line series
        self._height_series.append(float(point_index), height)
        if width is not None:
            self._width_series.append(float(point_index), width)

        # Trim old points if too many
        if self._height_series.count() > self.MAX_POINTS_DISPLAY:
            self._height_series.removePoints(0, 500)
        if self._width_series.count() > self.MAX_POINTS_DISPLAY:
            self._width_series.removePoints(0, 500)

        # Adjust X axis range
        if point_index > self._axis_x.max():
            self._axis_x.setRange(0, point_index + 50)

        # Expand an axis only when a value exceeds its full scale —
        # an over-limit spike must stay visible on the chart.
        if height > self._axis_y_height.max():
            self._axis_y_height.setRange(0, height * 1.1)
        if width is not None and width > self._axis_y_width.max():
            self._axis_y_width.setRange(0, width * 1.1)

    @Slot(float, int, float, int)
    def mark_max(self, height_value: float, height_index: int,
                 width_value: float, width_index: int):
        """Mark the maximum height/width points on the chart."""
        self._max_height_scatter.clear()
        self._max_width_scatter.clear()
        if height_value is not None and height_index > 0:
            self._max_height_scatter.append(float(height_index), height_value)
        if width_value is not None and width_index > 0:
            self._max_width_scatter.append(float(width_index), width_value)

    @Slot()
    def reset(self):
        """Clear the chart for a new measurement."""
        self._height_series.clear()
        self._width_series.clear()
        self._max_height_scatter.clear()
        self._max_width_scatter.clear()
        self._axis_x.setRange(0, 200)
        self._axis_y_height.setRange(0, self.HEIGHT_AXIS_MAX)
        self._axis_y_width.setRange(0, self.WIDTH_AXIS_MAX)
