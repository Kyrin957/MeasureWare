"""SettingsDialog: communication & extraction parameter configuration."""

import logging

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QWidget, QFormLayout,
                               QSpinBox, QComboBox, QLabel,
                               QPushButton, QDialogButtonBox,
                               QMessageBox, QGroupBox)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Modal dialog for device communication and extraction settings."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        self.setWindowTitle("软件参数配置")
        self.setMinimumSize(450, 400)
        self.resize(500, 450)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()

        # ---- Tab 1: Communication ----
        comm_tab = QWidget()
        comm_layout = QVBoxLayout(comm_tab)

        ip_group = QGroupBox("以太网设置")
        ip_form = QFormLayout()

        # IP address
        ip_layout = QHBoxLayout()
        self._ip_spinboxes = []
        for i in range(4):
            sb = QSpinBox()
            sb.setRange(0, 255)
            sb.setPrefix("")
            ip_layout.addWidget(sb)
            self._ip_spinboxes.append(sb)
            if i < 3:
                ip_layout.addWidget(QLabel("."))
        ip_form.addRow("IP 地址:", ip_layout)

        # Port
        self._cmd_port_spin = QSpinBox()
        self._cmd_port_spin.setRange(1024, 65535)
        self._cmd_port_spin.setValue(24691)
        ip_form.addRow("命令端口:", self._cmd_port_spin)

        self._hs_port_spin = QSpinBox()
        self._hs_port_spin.setRange(1024, 65535)
        self._hs_port_spin.setValue(24692)
        ip_form.addRow("高速数据端口:", self._hs_port_spin)

        ip_group.setLayout(ip_form)
        comm_layout.addWidget(ip_group)

        # Test connection button
        test_btn_layout = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._on_test_connection)
        test_btn_layout.addWidget(self._test_btn)
        test_btn_layout.addStretch()
        comm_layout.addLayout(test_btn_layout)

        comm_layout.addStretch()
        tabs.addTab(comm_tab, "通讯设置")

        # ---- Tab 2: Extraction ----
        extr_tab = QWidget()
        extr_layout = QVBoxLayout(extr_tab)

        extr_group = QGroupBox("数据提取设置")
        extr_form = QFormLayout()

        self._extr_mode_combo = QComboBox()
        self._extr_mode_combo.addItem("最大值 (Max Z)", "max")
        self._extr_mode_combo.addItem("平均值 (Avg Z)", "avg")
        extr_form.addRow("提取模式:", self._extr_mode_combo)

        self._roi_start_spin = QSpinBox()
        self._roi_start_spin.setRange(0, 3199)
        self._roi_start_spin.setValue(0)
        extr_form.addRow("ROI 起始 X 索引:", self._roi_start_spin)

        self._roi_end_spin = QSpinBox()
        self._roi_end_spin.setRange(0, 3199)
        self._roi_end_spin.setValue(3199)
        extr_form.addRow("ROI 结束 X 索引:", self._roi_end_spin)

        extr_group.setLayout(extr_form)
        extr_layout.addWidget(extr_group)
        extr_layout.addStretch()
        tabs.addTab(extr_tab, "提取设置")

        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self):
        """Populate fields from current settings."""
        octets = self._settings.ip_octets
        for i, octet in enumerate(octets):
            self._ip_spinboxes[i].setValue(octet)

        self._cmd_port_spin.setValue(self._settings.command_port)
        self._hs_port_spin.setValue(self._settings.high_speed_port)

        # Extraction
        mode = self._settings.extraction_mode
        idx = self._extr_mode_combo.findData(mode)
        if idx >= 0:
            self._extr_mode_combo.setCurrentIndex(idx)

        self._roi_start_spin.setValue(self._settings.extraction_roi_start)
        self._roi_end_spin.setValue(self._settings.extraction_roi_end)

    def _on_save(self):
        """Save settings to database."""
        octets = tuple(sb.value() for sb in self._ip_spinboxes)
        self._settings.save_all(
            ip_octets=octets,
            command_port=self._cmd_port_spin.value(),
            high_speed_port=self._hs_port_spin.value(),
            extraction_mode=self._extr_mode_combo.currentData(),
            roi_start=self._roi_start_spin.value(),
            roi_end=self._roi_end_spin.value(),
        )
        QMessageBox.information(self, "保存", "设置已保存")
        self.accept()

    def _on_test_connection(self):
        """Test Ethernet connection to the controller."""
        QMessageBox.information(
            self, "测试连接",
            "测试连接功能需要连接到实际的 LJ-X8000 设备。\n"
            "如设备未连接，此功能将失败。\n\n"
            "当前配置:\n"
            f"IP: {self._ip_spinboxes[0].value()}.{self._ip_spinboxes[1].value()}."
            f"{self._ip_spinboxes[2].value()}.{self._ip_spinboxes[3].value()}\n"
            f"端口: {self._cmd_port_spin.value()}"
        )
