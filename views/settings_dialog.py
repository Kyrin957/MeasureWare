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
        self._cmd_port_spin.setToolTip("LJ-X8000 无协议输出端口号")
        ip_form.addRow("数据端口:", self._cmd_port_spin)

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

    def _on_save(self):
        """Save settings to database."""
        octets = tuple(sb.value() for sb in self._ip_spinboxes)
        self._settings.save_all(
            ip_octets=octets,
            command_port=self._cmd_port_spin.value(),
        )
        QMessageBox.information(self, "保存", "设置已保存")
        self.accept()

    def _on_test_connection(self):
        """Test TCP connection to the LJ-X8000 controller."""
        import socket
        ip = f"{self._ip_spinboxes[0].value()}.{self._ip_spinboxes[1].value()}." \
             f"{self._ip_spinboxes[2].value()}.{self._ip_spinboxes[3].value()}"
        port = self._cmd_port_spin.value()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((ip, port))
            sock.close()
            QMessageBox.information(
                self, "测试连接",
                f"✓ TCP连接成功!\n\n{ip}:{port}"
            )
        except socket.timeout:
            QMessageBox.warning(
                self, "测试连接",
                f"✗ 连接超时\n\n{ip}:{port}\n请检查设备IP和端口设置。"
            )
        except ConnectionRefusedError:
            QMessageBox.warning(
                self, "测试连接",
                f"✗ 连接被拒绝\n\n{ip}:{port}\n请确认LJ-X8000已开启无协议输出。"
            )
        except OSError as e:
            QMessageBox.warning(
                self, "测试连接",
                f"✗ 连接失败\n\n{ip}:{port}\n错误: {e}"
            )
