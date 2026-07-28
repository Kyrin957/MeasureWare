"""MainWindow: top-level QMainWindow composing all panels and menus."""

import logging

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QMenuBar, QMenu, QStatusBar,
                               QMessageBox, QLabel)
from PySide6.QtCore import Qt, Slot

from controllers.measurement_controller import MeasurementController
from controllers.export_controller import ExportController
from views.job_info_panel import JobInfoPanel
from views.measurement_chart_view import MeasurementChartView
from views.measurement_table_view import MeasurementTableWidget
from views.result_panel import ResultPanel
from views.log_panel import LogPanel
from views.settings_dialog import SettingsDialog
from views.baseline_dialog import BaselineDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, settings, log_emitter, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._log_emitter = log_emitter

        # Create controller
        self._measurement_ctrl = MeasurementController(settings)
        self._measurement_ctrl.use_simulation = True  # Default simulation mode

        self._setup_ui()
        self._connect_signals()
        self._connect_logging()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("树脂测量数据监测")
        self.resize(1280, 900)
        self.setMinimumSize(1024, 700)

        # ---- Central Widget ----
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # ---- Job Info Panel (top) ----
        self._job_panel = JobInfoPanel()
        root_layout.addWidget(self._job_panel)

        # ---- Middle area: Chart + Result ----
        middle_row = QHBoxLayout()

        self._chart_view = MeasurementChartView()
        middle_row.addWidget(self._chart_view, 3)

        self._result_panel = ResultPanel()
        middle_row.addWidget(self._result_panel, 1)

        root_layout.addLayout(middle_row, 2)

        # ---- Bottom: Table + Log (horizontal splitter) ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._table_widget = MeasurementTableWidget()
        splitter.addWidget(self._table_widget)

        self._log_panel = LogPanel()
        splitter.addWidget(self._log_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        root_layout.addWidget(splitter, 1)

        # ---- Menu Bar ----
        self._setup_menus()

        # ---- Status Bar ----
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("就绪")
        self._statusbar.addPermanentWidget(self._status_label)
        self._mode_label = QLabel("模式: 仿真")
        self._statusbar.addPermanentWidget(self._mode_label)

    def _setup_menus(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导出当前CSV", self._on_export_current)
        file_menu.addAction("导出全部CSV", self._on_export_all)
        file_menu.addSeparator()
        file_menu.addAction("退出(&X)", self.close)

        # Settings menu
        settings_menu = menubar.addMenu("设置(&S)")

        comm_action = settings_menu.addAction("通讯设置", self._on_open_settings)
        baseline_action = settings_menu.addAction("基准值管理", self._on_open_baselines)

        settings_menu.addSeparator()

        # Simulation toggle
        self._sim_action = settings_menu.addAction(
            "✓ 仿真模式 (点此切换实机模式)", self._on_toggle_simulation
        )

        # Help menu
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于...", self._on_about)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        """Connect all signals between panels and controller."""

        # Job panel → controller
        self._job_panel.start_requested.connect(self._on_start_measurement)
        self._job_panel.stop_requested.connect(self._measurement_ctrl.request_stop)
        self._job_panel.export_requested.connect(self._on_export)

        # Controller → panels
        self._measurement_ctrl.point_data_ready.connect(self._chart_view.add_point)
        self._measurement_ctrl.point_data_ready.connect(self._table_widget.add_point)
        self._measurement_ctrl.state_changed.connect(self._job_panel.on_state_changed)
        self._measurement_ctrl.state_changed.connect(self._on_state_changed)
        self._measurement_ctrl.log_message.connect(self._log_panel.append_log)
        self._measurement_ctrl.session_completed.connect(
            self._result_panel.on_session_completed
        )
        self._measurement_ctrl.session_completed.connect(
            self._on_session_completed_chart
        )

        # Table edit → controller
        self._table_widget.point_edited.connect(self._on_point_edited)

    def _connect_logging(self):
        """Connect the logging signal emitter to the log panel."""
        if self._log_emitter is not None:
            self._log_emitter.log_message.connect(self._log_panel.append_log)

    # ------------------------------------------------------------------
    # Measurement flow slots
    # ------------------------------------------------------------------

    @Slot(str, str, str)
    def _on_start_measurement(self, batch: str, product: str, seq: str):
        """Handle start measurement request from job panel."""
        # Clear previous data
        self._chart_view.reset()
        self._table_widget.clear()
        self._result_panel.reset()

        # Prepare session
        session_id = self._measurement_ctrl.prepare_session(
            batch, product, seq
        )
        if session_id is None:
            return  # Validation failed, message already logged

        # Start acquisition
        self._measurement_ctrl.start_acquisition()

    @Slot(dict)
    def _on_session_completed_chart(self, summary: dict):
        """Update chart with max value marker."""
        max_val = summary.get("max_measured_value")
        if max_val is not None:
            # max_point_index is tracked in-memory by the worker — no DB query needed
            max_idx = summary.get("max_point_index", 0)
            self._chart_view.mark_max(max_val, max_idx)

    @Slot(str)
    def _on_state_changed(self, state_name: str):
        """Update status bar on state change."""
        if state_name == "RUNNING":
            self._status_label.setText("测量中...")
            self._status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        elif state_name in ("IDLE", "READY"):
            self._status_label.setText("就绪")
            self._status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif state_name == "ERROR":
            self._status_label.setText("错误")
            self._status_label.setStyleSheet("color: #FF9800; font-weight: bold;")

    # ------------------------------------------------------------------
    # Point editing
    # ------------------------------------------------------------------

    @Slot(int, float)
    def _on_point_edited(self, point_index: int, new_value: float):
        """Handle manual edit of a measurement point value."""
        session_id = self._measurement_ctrl._current_session_id
        if session_id is None:
            return

        summary = self._measurement_ctrl.update_point_value(
            session_id, point_index, new_value
        )
        if summary:
            self._result_panel.on_session_completed(summary)

            # Update max marker on chart
            max_val = summary.get("max_measured_value")
            if max_val is not None:
                max_idx = 0
                # Find max index from current model
                model = self._table_widget.get_model()
                found_max, found_idx = model.find_max()
                if found_max is not None:
                    max_idx = found_idx
                self._chart_view.mark_max(max_val, max_idx)

            self._log_panel.append_log(
                f"点位 {point_index} 已手动修改为 {new_value:.3f} mm, "
                f"判定更新为 {summary.get('judgment', '--')}",
                logging.INFO
            )

    # ------------------------------------------------------------------
    # Export slots
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_export(self, filepath: str):
        """Export current session to CSV."""
        session_id = self._measurement_ctrl._current_session_id
        if session_id is None:
            QMessageBox.warning(self, "导出失败", "没有可导出的测量数据")
            return

        success = ExportController.export_session(session_id, filepath)
        if success:
            logger.info(f"已导出测量任务 #{session_id} 到 {filepath}")
            self._log_panel.append_log(f"已导出数据到: {filepath}", logging.INFO)
        else:
            QMessageBox.warning(self, "导出失败", "CSV导出失败，请查看日志")

    @Slot()
    def _on_export_current(self):
        """Menu: export current session."""
        from PySide6.QtWidgets import QFileDialog
        session_id = self._measurement_ctrl._current_session_id
        if session_id is None:
            QMessageBox.warning(self, "导出失败", "没有可导出的测量数据")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出当前测量数据", "measurement_data.csv", "CSV 文件 (*.csv)"
        )
        if filepath:
            self._on_export(filepath)

    @Slot()
    def _on_export_all(self):
        """Menu: export all sessions."""
        from PySide6.QtWidgets import QFileDialog

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出全部测量数据", "all_measurements.csv", "CSV 文件 (*.csv)"
        )
        if filepath:
            success = ExportController.export_all(filepath)
            if success:
                logger.info(f"已导出全部测量任务到 {filepath}")
                self._log_panel.append_log(f"已导出全部数据到: {filepath}", logging.INFO)
            else:
                QMessageBox.warning(self, "导出失败", "CSV导出失败，请查看日志")

    # ------------------------------------------------------------------
    # Settings & dialogs
    # ------------------------------------------------------------------

    @Slot()
    def _on_open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self._log_panel.append_log("通讯设置已更新", logging.INFO)

    @Slot()
    def _on_open_baselines(self):
        """Open baseline management dialog."""
        dialog = BaselineDialog(self)
        if dialog.exec() == BaselineDialog.DialogCode.Accepted:
            self._job_panel.refresh_product_list()
            self._log_panel.append_log("品名基准值已更新", logging.INFO)

    @Slot()
    def _on_toggle_simulation(self):
        """Toggle between simulation and real device mode."""
        self._measurement_ctrl.use_simulation = not self._measurement_ctrl.use_simulation
        if self._measurement_ctrl.use_simulation:
            self._sim_action.setText("✓ 仿真模式 (点此切换实机模式)")
            self._mode_label.setText("模式: 仿真")
        else:
            self._sim_action.setText("✓ 实机模式 (点此切换仿真模式)")
            self._mode_label.setText("模式: 实机")
        self._log_panel.append_log(
            f"切换到{'仿真' if self._measurement_ctrl.use_simulation else '实机'}模式",
            logging.INFO
        )

    @Slot()
    def _on_about(self):
        QMessageBox.about(
            self, "关于 MeasureWare",
            "<h3>MeasureWare</h3>"
            "<p>封止树脂测量数据监测软件 v1.0</p>"
            "<p>基于 Python + PySide6 开发</p>"
            "<p>适用于基恩士 LJ-X8000 系列线激光测量仪</p>"
            "<hr>"
            "<p>通信库: LJXAwrap.py (Keyence Corp.)</p>"
        )
