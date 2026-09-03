"""BaselineDialog: CRUD management for resin specification limits."""

import logging

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QTableView, QHeaderView, QPushButton,
                               QMessageBox, QDialogButtonBox,
                               QAbstractItemView, QLabel)
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex,
                            Signal, Slot)

from controllers.baseline_controller import BaselineController

logger = logging.getLogger(__name__)


class BaselineTableModel(QAbstractTableModel):
    """Table model for ProductBaseline CRUD in dialog."""

    COLUMNS = ["树脂规格要求", "高度上限 (mm)", "宽度上限 (mm)"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baselines: list[dict] = []  # Each has id, spec_name, height_upper_limit, width_upper_limit
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

        if role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return item.get("spec_name", "")
            elif col == 1:
                return f"{item.get('height_upper_limit', 0):.3f}"
            elif col == 2:
                return f"{item.get('width_upper_limit', 0):.3f}"

        elif role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.get("spec_name", "")
            elif col == 1:
                return f"{item.get('height_upper_limit', 0):.3f}"
            elif col == 2:
                width_limit = item.get("width_upper_limit", 0)
                return f"{width_limit:.3f}" if width_limit > 0 else "0 (不检查)"

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
                self._baselines[row]["spec_name"] = str(value).strip()
            elif col in (1, 2):
                field = {1: "height_upper_limit", 2: "width_upper_limit"}[col]
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
            "spec_name": b.get("spec_name", ""),
            "height_upper_limit": b.get("height_upper_limit", 0),
            "width_upper_limit": b.get("width_upper_limit", 0),
        } for b in baselines]
        self._dirty = False
        self.endResetModel()

    def add_row(self):
        """Append an empty row for the user to fill."""
        row = len(self._baselines)
        self.beginInsertRows(QModelIndex(), row, row)
        self._baselines.append({
            "id": None,
            "spec_name": "",
            "height_upper_limit": 0.0,
            "width_upper_limit": 0.0,
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
    """Modal dialog for managing resin specification limits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("树脂规格要求管理")
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

        layout.addWidget(self._table_view)

        # Hint
        hint = QLabel("提示: 宽度上限设为 0 表示该规格不检查宽度")
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

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
        name = item.get("spec_name", "") or "(空)"

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除树脂规格要求 '{name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._model.remove_row(row)

    @Slot()
    def _on_save(self):
        """Validate and save all baselines."""
        baselines = self._model.get_baselines()

        # Filter out rows with empty spec name
        valid = [b for b in baselines if b.get("spec_name", "").strip()]
        empty_count = len(baselines) - len(valid)

        if not valid:
            QMessageBox.warning(self, "验证失败", "没有有效的规格记录（树脂规格要求不能为空）")
            return

        # Check for duplicate names
        names = [b["spec_name"] for b in valid]
        if len(names) != len(set(names)):
            QMessageBox.warning(self, "验证失败", "树脂规格要求存在重复，请检查")
            return

        # Limits must not be negative; height limit must be positive
        for b in valid:
            if b.get("height_upper_limit", 0) <= 0:
                QMessageBox.warning(
                    self, "验证失败",
                    f"'{b['spec_name']}' 的高度上限必须大于 0"
                )
                return
            if b.get("width_upper_limit", 0) < 0:
                QMessageBox.warning(
                    self, "验证失败",
                    f"'{b['spec_name']}' 的宽度上限不能为负数"
                )
                return

        success, msg = BaselineController.save_all(valid)

        if success:
            if empty_count > 0:
                msg += f"\n(已忽略 {empty_count} 条规格要求为空的记录)"
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
