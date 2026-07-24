"""MeasurementTableWidget: editable table of measurement points."""

import logging

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                               QTableView, QHeaderView, QAbstractItemView)
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex,
                            Signal, Slot)
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


class MeasurementTableModel(QAbstractTableModel):
    """Table model for measurement point data.

    Columns: Point Index | X Position (mm) | Measured Value (mm)
    Column 2 (Measured Value) is editable.
    """

    COLUMNS = ["点位序号", "X位置 (mm)", "测量值 (mm)"]

    point_edited = Signal(int, float)  # point_index, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[dict] = []  # [{point_index, x_position, measured_value}, ...]

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
                x = point.get("x_position")
                return f"{x:.4f}" if x is not None else "--"
            elif col == 2:
                return f"{point['measured_value']:.4f}"

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == 2:
                val = point.get("measured_value", 0)
                if val < 0:
                    return QColor("#F44336")

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        if index.column() != 2:
            return False  # Only column 2 is editable

        try:
            new_value = float(value)
        except (ValueError, TypeError):
            return False

        row = index.row()
        self._points[row]["measured_value"] = new_value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

        point_index = self._points[row]["point_index"]
        self.point_edited.emit(point_index, new_value)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        if index.column() == 2:  # Measured value column
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    # ---- Public API ----

    def append_point(self, point_index: int, x_position: float, measured_value: float):
        """Append a new point row."""
        row = len(self._points)
        self.beginInsertRows(QModelIndex(), row, row)
        self._points.append({
            "point_index": point_index,
            "x_position": x_position,
            "measured_value": measured_value,
        })
        self.endInsertRows()

    def load_points(self, points: list[dict]):
        """Replace all rows with the given point list."""
        self.beginResetModel()
        self._points = [{
            "point_index": p.get("point_index", 0),
            "x_position": p.get("x_position"),
            "measured_value": p.get("measured_value", 0),
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

    def find_max(self) -> tuple:
        """Find the max value and its point index.

        Returns:
            (max_value, point_index) or (None, 0) if empty.
        """
        if not self._points:
            return (None, 0)
        max_point = max(self._points, key=lambda p: p["measured_value"])
        return (max_point["measured_value"], max_point["point_index"])


class MeasurementTableWidget(QWidget):
    """Table view widget for measurement data."""

    point_edited = Signal(int, float)  # point_index, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
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
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table_view)

    # ---- Public API ----

    @Slot(int, float, float)
    def add_point(self, point_index: int, value: float, x_position: float):
        """Append a new measurement point row."""
        self._model.append_point(point_index, x_position, value)
        # Auto-scroll to bottom
        self._table_view.scrollToBottom()

    def load_points(self, points: list[dict]):
        """Load points from a list of dicts."""
        self._model.load_points(points)

    def clear(self):
        """Clear all rows."""
        self._model.clear()

    def get_model(self) -> MeasurementTableModel:
        return self._model
