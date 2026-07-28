"""BaselineDialog: CRUD management for product baseline values."""

import logging

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QTableView, QHeaderView, QPushButton,
                               QMessageBox, QDialogButtonBox,
                               QAbstractItemView)
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex,
                            Signal, Slot)

from controllers.baseline_controller import BaselineController

logger = logging.getLogger(__name__)


class BaselineTableModel(QAbstractTableModel):
    """Table model for ProductBaseline CRUD in dialog."""

    COLUMNS = ["品名", "基准值 (mm)", "上公差 (mm)", "下公差 (mm)"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baselines: list[dict] = []  # Each has id, product_name, baseline_value, tolerance_upper, tolerance_lower
        self._dirty = False  # Track if user has made changes

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._baselines)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        item = self._baselines[row]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                return item.get("product_name", "")
            elif col == 1:
                return f"{item.get('baseline_value', 0):.3f}"
            elif col == 2:
                return f"{item.get('tolerance_upper', 0):.3f}"
            elif col == 3:
                return f"{item.get('tolerance_lower', 0):.3f}"

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()

        try:
            if col == 0:
                self._baselines[row]["product_name"] = str(value).strip()
            elif col in (1, 2, 3):
                field = {1: "baseline_value", 2: "tolerance_upper", 3: "tolerance_lower"}[col]
                self._baselines[row][field] = float(value)
        except (ValueError, TypeError):
            return False

        self._dirty = True
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        flags |= Qt.ItemFlag.ItemIsEditable  # All cells editable
        return flags

    # ---- Public API ----

    def load_baselines(self, baselines: list[dict]):
        """Replace all rows."""
        self.beginResetModel()
        self._baselines = [{
            "id": b.get("id"),
            "product_name": b.get("product_name", ""),
            "baseline_value": b.get("baseline_value", 0),
            "tolerance_upper": b.get("tolerance_upper", 0),
            "tolerance_lower": b.get("tolerance_lower", 0),
        } for b in baselines]
        self._dirty = False
        self.endResetModel()

    def add_row(self):
        """Append an empty row for the user to fill."""
        row = len(self._baselines)
        self.beginInsertRows(QModelIndex(), row, row)
        self._baselines.append({
            "id": None,
            "product_name": "",
            "baseline_value": 0.0,
            "tolerance_upper": 0.0,
            "tolerance_lower": 0.0,
        })
        self._dirty = True
        self.endInsertRows()

    def remove_row(self, row: int):
        """Remove a row by index."""
        if 0 <= row < len(self._baselines):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._baselines.pop(row)
            self._dirty = True
            self.endRemoveRows()

    def get_baselines(self) -> list[dict]:
        """Get the current baseline data."""
        return list(self._baselines)

    @property
    def is_dirty(self) -> bool:
        return self._dirty


class BaselineDialog(QDialog):
    """Modal dialog for managing product baseline values."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("基准值管理")
        self.setMinimumSize(550, 400)
        self.resize(600, 450)

        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self._add_btn = QPushButton("＋ 新增")
        self._add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(self._add_btn)

        self._delete_btn = QPushButton("－ 删除")
        self._delete_btn.clicked.connect(self._on_delete)
        toolbar.addWidget(self._delete_btn)

        toolbar.addStretch()

        # help_label = QPushButton("?")
        # help_label.setFixedWidth(30)
        # help_label.setToolTip("双击单元格可编辑\n品名为空的行在保存时会被忽略")
        # toolbar.addWidget(help_label)

        layout.addLayout(toolbar)

        # Table
        self._model = BaselineTableModel(self)
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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table_view)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        layout.addWidget(button_box)

    def _load_data(self):
        baselines = BaselineController.get_all()
        self._model.load_baselines(baselines)

    @Slot()
    def _on_add(self):
        self._model.add_row()
        # Scroll to the new row and start editing
        last_row = self._model.rowCount() - 1
        self._table_view.scrollToBottom()
        self._table_view.edit(self._model.index(last_row, 0))

    @Slot()
    def _on_delete(self):
        selected = self._table_view.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的行")
            return

        row = selected[0].row()
        item = self._model.get_baselines()[row]
        name = item.get("product_name", "") or "(空)"

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除品名 '{name}' 的基准值吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._model.remove_row(row)

    @Slot()
    def _on_save(self):
        """Validate and save all baselines."""
        baselines = self._model.get_baselines()

        # Filter out rows with empty product name
        valid = [b for b in baselines if b.get("product_name", "").strip()]
        empty_count = len(baselines) - len(valid)

        if not valid:
            QMessageBox.warning(self, "验证失败", "没有有效的基准值记录（品名不能为空）")
            return

        # Check for duplicate names
        names = [b["product_name"] for b in valid]
        if len(names) != len(set(names)):
            QMessageBox.warning(self, "验证失败", "品名存在重复，请检查")
            return

        success, msg = BaselineController.save_all(valid)

        if success:
            if empty_count > 0:
                msg += f"\n(已忽略 {empty_count} 条空品名的记录)"
            QMessageBox.information(self, "保存", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "保存失败", msg)

    @Slot()
    def reject(self):
        """Handle dialog close — ask if there are unsaved changes."""
        if self._model.is_dirty:
            reply = QMessageBox.question(
                self, "未保存的更改",
                "有未保存的更改，确定要关闭吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        super().reject()
