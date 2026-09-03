"""MeasurementTableWidget: editable table of measurement points.

Columns: Point Index | Height (mm) | Width (mm)
Both value columns are editable.
"""

import logging

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                               QTableView, QHeaderView, QAbstractItemView)
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex,
                            Signal, Slot)
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


class MeasurementTableModel(QAbstractTableModel):
    """Table model for measurement point data.

    Columns: Point Index | Height (mm) | Width (mm)
    Columns 1 (Height) and 2 (Width) are editable.
    """

    COLUMNS = ["点位序号", "高度 (mm)", "宽度 (mm)"]

    # field names per column, used for edit notifications
    FIELD_BY_COL = {1: "height", 2: "width"}

    point_edited = Signal(int, str, float)  # point_index, field, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[dict] = []  # [{point_index, height_value, width_value}, ...]

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._points)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        point = self._points[row]

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return point["point_index"]
            elif col == 1:
                return f"{point['height_value']:.3f}"
            elif col == 2:
                width = point.get("width_value")
                return f"{width:.3f}" if width is not None else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == 1:
                val = point.get("height_value", 0)
                if val < 0:
                    return QColor("#F44336")
            elif col == 2:
                val = point.get("width_value")
                if val is not None and val < 0:
                    return QColor("#F44336")

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        col = index.column()
        if col not in self.FIELD_BY_COL:
            return False  # Only value columns are editable

        try:
            new_value = float(value)
        except (ValueError, TypeError):
            return False

        row = index.row()
        field = self.FIELD_BY_COL[col]
        self._points[row][f"{field}_value"] = new_value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

        point_index = self._points[row]["point_index"]
        self.point_edited.emit(point_index, field, new_value)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        if index.column() in self.FIELD_BY_COL:  # Value columns
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    # ---- Public API ----

    def append_point(self, point_index: int, height_value: float,
                     width_value=None):
        """Append a new point row."""
        row = len(self._points)
        self.beginInsertRows(QModelIndex(), row, row)
        self._points.append({
            "point_index": point_index,
            "height_value": height_value,
            "width_value": width_value,
        })
        self.endInsertRows()

    def load_points(self, points: list[dict]):
        """Replace all rows with the given point list."""
        self.beginResetModel()
        self._points = [{
            "point_index": p.get("point_index", 0),
            "height_value": p.get("height_value", 0),
            "width_value": p.get("width_value"),
        } for p in points]
        self.endResetModel()

    def clear(self):
        """Remove all rows."""
        self.beginResetModel()
        self._points.clear()
        self.endResetModel()

    def get_points(self) -> list[dict]:
        """Return all point data."""
        return list(self._points)

    def find_max(self) -> dict:
        """Find the max height/width values and their point indices.

        Returns:
            {"height": (max_value, point_index) or (None, 0),
             "width":  (max_value, point_index) or (None, 0)}
        """
        result = {"height": (None, 0), "width": (None, 0)}

        if self._points:
            h_point = max(self._points, key=lambda p: p["height_value"])
            result["height"] = (h_point["height_value"], h_point["point_index"])

            widths = [p for p in self._points if p.get("width_value") is not None]
            if widths:
                w_point = max(widths, key=lambda p: p["width_value"])
                result["width"] = (w_point["width_value"], w_point["point_index"])

        return result


class MeasurementTableWidget(QWidget):
    """Table view widget for measurement data."""

    SCROLL_THROTTLE = 50          # scroll to bottom at most every N points
    SCROLL_EARLY_LIMIT = 100      # always scroll for the first N points

    point_edited = Signal(int, str, float)  # point_index, field, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._point_count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("测量数据表")
        title.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(title)

        # Table
        self._model = MeasurementTableModel(self)
        self._model.point_edited.connect(self.point_edited.emit)

        self._table_view = QTableView()
        self._table_view.setModel(self._model)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table_view.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked
        )

        # Header sizing
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table_view)

    # ---- Public API ----

    @Slot(int, float, object)
    def add_point(self, point_index: int, height: float, width):
        """Append a new measurement point row."""
        self._model.append_point(point_index, height, width)
        self._point_count += 1
        # Throttle scroll — constant layout recalculation is expensive
        if (self._point_count <= self.SCROLL_EARLY_LIMIT
                or self._point_count % self.SCROLL_THROTTLE == 0):
            self._table_view.scrollToBottom()

    def load_points(self, points: list[dict]):
        """Load points from a list of dicts."""
        self._model.load_points(points)

    def clear(self):
        """Clear all rows."""
        self._model.clear()
        self._point_count = 0

    def get_model(self) -> MeasurementTableModel:
        return self._model
