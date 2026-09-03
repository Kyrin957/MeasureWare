"""JobInfoPanel: operator info entry + control buttons."""

import logging

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QLineEdit, QPushButton,
                               QComboBox, QGroupBox, QFileDialog,
                               QMessageBox)
from PySide6.QtCore import Signal, Slot

from controllers.baseline_controller import BaselineController

logger = logging.getLogger(__name__)


class JobInfoPanel(QGroupBox):
    """Top panel for entering job info and controlling measurement."""

    # Signals
    start_requested = Signal(str, str, str)  # batch, product, seq
    stop_requested = Signal()
    export_requested = Signal(str)                 # filepath
    log_message = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__("作业信息", parent)
        self._setup_ui()
        self._refresh_product_list()
        self._update_button_states(is_idle=True)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Row 1: Input fields
        input_row = QHBoxLayout()

        # Batch number
        input_row.addWidget(QLabel("批号:"))
        self._batch_edit = QLineEdit()
        self._batch_edit.setPlaceholderText("输入批号...")
        self._batch_edit.setMinimumWidth(120)
        input_row.addWidget(self._batch_edit)

        # Resin specification requirement
        input_row.addWidget(QLabel("树脂规格要求:"))
        self._product_combo = QComboBox()
        self._product_combo.setEditable(True)
        self._product_combo.setPlaceholderText("选择或输入树脂规格要求...")
        self._product_combo.setMinimumWidth(150)
        input_row.addWidget(self._product_combo)

        # Inspection sequence
        input_row.addWidget(QLabel("检测序号:"))
        self._seq_edit = QLineEdit()
        self._seq_edit.setPlaceholderText("可选")
        self._seq_edit.setMaximumWidth(80)
        input_row.addWidget(self._seq_edit)

        main_layout.addLayout(input_row)

        # Row 2: Buttons
        button_row = QHBoxLayout()

        self._start_btn = QPushButton("▶  开始测量")
        self._start_btn.setMinimumHeight(36)
        self._start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-weight: bold; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self._start_btn.clicked.connect(self._on_start_clicked)
        button_row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■  停止")
        self._stop_btn.setMinimumHeight(36)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; "
            "font-weight: bold; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        button_row.addWidget(self._stop_btn)

        button_row.addStretch()

        # self._export_btn = QPushButton("📄  导出CSV")
        # self._export_btn.setMinimumHeight(36)
        # self._export_btn.clicked.connect(self._on_export_clicked)
        # button_row.addWidget(self._export_btn)

        # self._status_label = QLabel("状态: 就绪")
        # self._status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        # button_row.addWidget(self._status_label)

        main_layout.addLayout(button_row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def _on_start_clicked(self):
        batch = self._batch_edit.text().strip()
        product = self._product_combo.currentText().strip()
        seq = self._seq_edit.text().strip()
        if not batch:
            QMessageBox.warning(self, "输入验证", "请输入批号")
            return
        if not product:
            QMessageBox.warning(self, "输入验证", "请输入树脂规格要求")
            return

        self.start_requested.emit(batch, product, seq)

    @Slot()
    def _on_stop_clicked(self):
        self.stop_requested.emit()

    @Slot()
    def _on_export_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "measurement_data.csv",
            "CSV 文件 (*.csv)"
        )
        if filepath:
            self.export_requested.emit(filepath)

    @Slot(str)
    def on_state_changed(self, state_name: str):
        """Update UI based on measurement state."""
        is_idle = state_name in ("IDLE", "ERROR")
        self._update_button_states(is_idle)

    def _update_button_states(self, is_idle: bool):
        self._start_btn.setEnabled(is_idle)
        self._stop_btn.setEnabled(not is_idle)
        self._batch_edit.setEnabled(is_idle)
        self._product_combo.setEnabled(is_idle)
        self._seq_edit.setEnabled(is_idle)

    # ------------------------------------------------------------------
    # Product list
    # ------------------------------------------------------------------

    def _refresh_product_list(self):
        """Reload spec names from the baseline table."""
        current = self._product_combo.currentText()
        self._product_combo.clear()
        baselines = BaselineController.get_all()
        for b in baselines:
            self._product_combo.addItem(b["spec_name"])
        if current:
            idx = self._product_combo.findText(current)
            if idx >= 0:
                self._product_combo.setCurrentIndex(idx)
            else:
                self._product_combo.setCurrentText(current)

    def refresh_product_list(self):
        """Public method to refresh the product combo."""
        self._refresh_product_list()
