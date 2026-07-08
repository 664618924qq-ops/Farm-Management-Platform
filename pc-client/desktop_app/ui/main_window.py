from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QObject, QDate, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplashScreen,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.services.data_service import (
    DEFAULT_WATER_FACTORS,
    AcquisitionProfile,
    AcquisitionSettings,
    ConnectionTestResult,
    DesktopDataService,
    LastPacketSnapshot,
    PlatformSettings,
    PlatformRuntimeStatus,
    RuntimeSettings,
    SerialProfile,
    SerialSettings,
)


class DeviceConfigDialog(QDialog):
    def __init__(
        self,
        device: dict,
        protocol_options: list[str],
        connection_options: list[str],
        site_options: list[dict],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        is_new = not bool(device.get("id"))
        self.setWindowTitle("新增设备" if is_new else f"设备配置 - {device['device_code']}")
        self.setMinimumSize(560, 520)

        self.site_input = QComboBox()
        for site in site_options:
            self.site_input.addItem(f"{site['site_code']} / {site['site_name']}", site["id"])
        target_site_id = int(device.get("site_id", 0) or 0)
        for index in range(self.site_input.count()):
            if int(self.site_input.itemData(index)) == target_site_id:
                self.site_input.setCurrentIndex(index)
                break
        self.pond_input = QLineEdit(device.get("pond_code", ""))
        self.code_input = QLineEdit(device.get("device_code", ""))
        self.code_input.setReadOnly(not is_new)
        self.name_input = QLineEdit(device.get("device_name", ""))
        self.type_input = QLineEdit(device.get("device_type", ""))
        self.protocol_input = QComboBox()
        self.protocol_input.setEditable(True)
        self.protocol_input.addItems(protocol_options)
        self.protocol_input.setCurrentText(device.get("protocol_type", "custom"))
        self.connection_input = QComboBox()
        self.connection_input.setEditable(True)
        self.connection_input.addItems(connection_options)
        self.connection_input.setCurrentText(device.get("connection_type", "tcp"))
        self.sort_order_input = QSpinBox()
        self.sort_order_input.setRange(0, 9999)
        self.sort_order_input.setValue(int(device.get("sort_order", 0)))
        self.config_input = QTextEdit(device.get("config_json", ""))
        self.config_input.setPlaceholderText('{"host": "127.0.0.1", "port": 502, "slave": 1}')

        form = QFormLayout()
        form.addRow("所属站点", self.site_input)
        form.addRow("塘口编号", self.pond_input)
        form.addRow("设备编号", self.code_input)
        form.addRow("设备名称", self.name_input)
        form.addRow("设备型号", self.type_input)
        form.addRow("协议类型", self.protocol_input)
        form.addRow("连接方式", self.connection_input)
        form.addRow("排序号", self.sort_order_input)
        form.addRow("连接配置 JSON", self.config_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if self.site_input.currentData() in (None, "", 0):
            QMessageBox.warning(self, "保存失败", "请选择所属站点。")
            self.site_input.setFocus()
            return
        if not self.pond_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入塘口编号。")
            self.pond_input.setFocus()
            return
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入设备编号。")
            self.code_input.setFocus()
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入设备名称。")
            self.name_input.setFocus()
            return
        if not self.type_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入设备型号。")
            self.type_input.setFocus()
            return
        config_text = self.config_input.toPlainText().strip()
        if config_text:
            try:
                json.loads(config_text)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "保存失败", "连接配置必须是合法的 JSON。")
                self.config_input.setFocus()
                return
        super().accept()

    def get_payload(self) -> dict:
        return {
            "site_id": int(self.site_input.currentData()),
            "pond_code": self.pond_input.text().strip(),
            "device_code": self.code_input.text().strip(),
            "device_name": self.name_input.text().strip(),
            "device_type": self.type_input.text().strip(),
            "protocol_type": self.protocol_input.currentText().strip(),
            "connection_type": self.connection_input.currentText().strip(),
            "sort_order": self.sort_order_input.value(),
            "config_json": self.config_input.toPlainText().strip(),
        }


class SiteConfigDialog(QDialog):
    def __init__(self, site: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        is_new = not bool(site.get("id"))
        self.setWindowTitle("新增站点" if is_new else f"站点配置 - {site['site_code']}")
        self.setMinimumSize(520, 280)

        self.code_input = QLineEdit(site.get("site_code", ""))
        self.name_input = QLineEdit(site.get("site_name", ""))
        self.contact_name_input = QLineEdit(site.get("contact_name", ""))
        self.contact_phone_input = QLineEdit(site.get("contact_phone", ""))

        form = QFormLayout()
        form.addRow("站点编码", self.code_input)
        form.addRow("站点名称", self.name_input)
        form.addRow("联系人", self.contact_name_input)
        form.addRow("联系电话", self.contact_phone_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入站点编码。")
            self.code_input.setFocus()
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入站点名称。")
            self.name_input.setFocus()
            return
        super().accept()

    def get_payload(self) -> dict:
        return {
            "site_code": self.code_input.text().strip(),
            "site_name": self.name_input.text().strip(),
            "contact_name": self.contact_name_input.text().strip(),
            "contact_phone": self.contact_phone_input.text().strip(),
        }


class SerialConfigDialog(QDialog):
    def __init__(self, profile: SerialProfile | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        is_new = profile is None
        profile = profile or SerialProfile("新串口配置", "COM1", 9600, 8, "N", 1, 1, False)
        self.setWindowTitle("新增串口配置" if is_new else f"编辑串口配置 - {profile.profile_name}")
        self.setMinimumSize(520, 320)

        self.name_input = QLineEdit(profile.profile_name)
        self.port_combo = QComboBox()
        self.port_combo.addItems([f"COM{i}" for i in range(1, 21)])
        self.port_combo.setCurrentText(profile.port_name)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText(str(profile.baudrate))
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText(str(profile.data_bits))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O"])
        self.parity_combo.setCurrentText(profile.parity)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "2"])
        self.stop_bits_combo.setCurrentText(str(profile.stop_bits))
        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(1, 255)
        self.slave_spin.setValue(profile.slave_address)
        self.default_checkbox = QCheckBox("设为默认串口配置")
        self.default_checkbox.setChecked(profile.is_default)

        form = QFormLayout()
        form.addRow("配置名称", self.name_input)
        form.addRow("串口号", self.port_combo)
        form.addRow("波特率", self.baudrate_combo)
        form.addRow("数据位", self.data_bits_combo)
        form.addRow("校验位", self.parity_combo)
        form.addRow("停止位", self.stop_bits_combo)
        form.addRow("设备地址", self.slave_spin)
        form.addRow("", self.default_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入串口配置名称。")
            self.name_input.setFocus()
            return
        if not self.port_combo.currentText().strip():
            QMessageBox.warning(self, "保存失败", "请选择串口号。")
            self.port_combo.setFocus()
            return
        super().accept()

    def get_payload(self) -> dict:
        return {
            "profile_name": self.name_input.text().strip(),
            "port_name": self.port_combo.currentText().strip(),
            "baudrate": int(self.baudrate_combo.currentText()),
            "data_bits": int(self.data_bits_combo.currentText()),
            "parity": self.parity_combo.currentText().strip(),
            "stop_bits": int(self.stop_bits_combo.currentText()),
            "slave_address": self.slave_spin.value(),
            "is_default": self.default_checkbox.isChecked(),
        }


class AcquisitionProfileDialog(QDialog):
    def __init__(self, profile: AcquisitionProfile | None, serial_profile_names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        is_new = profile is None
        profile = profile or AcquisitionProfile("新设备模板", "modbus_tcp", "tcp", "", 5, "float32", "40001", False)
        self.setWindowTitle("新增采集模板" if is_new else f"采集模板配置 - {profile.profile_name}")
        self.setMinimumSize(600, 420)

        self.name_input = QLineEdit(profile.profile_name)
        self.protocol_input = QComboBox()
        self.protocol_input.addItems(["modbus_tcp", "modbus_rtu"])
        self.protocol_input.setCurrentText(profile.protocol_type)
        self.connection_combo = QComboBox()
        self.connection_combo.addItems(["tcp", "serial"])
        self.connection_combo.setCurrentText(profile.connection_type)
        self.serial_profile_combo = QComboBox()
        self.serial_profile_combo.addItem("", "")
        for name in serial_profile_names:
            self.serial_profile_combo.addItem(name, name)
        target_index = self.serial_profile_combo.findData(profile.serial_profile_name)
        if target_index >= 0:
            self.serial_profile_combo.setCurrentIndex(target_index)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 120)
        self.timeout_spin.setValue(profile.collect_timeout_seconds)
        self.default_checkbox = QCheckBox("设为新增设备默认模板")
        self.default_checkbox.setChecked(profile.is_default)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["uint16", "int16", "uint32", "int32", "float32"])
        self.data_type_combo.setCurrentText(profile.data_type)
        self.register_input = QLineEdit(profile.register_address)
        self.protocol_input.currentTextChanged.connect(self._sync_protocol_fields)

        form = QFormLayout()
        form.addRow("设备名称", self.name_input)
        form.addRow("协议类型", self.protocol_input)
        form.addRow("连接方式", self.connection_combo)
        form.addRow("绑定串口配置", self.serial_profile_combo)
        form.addRow("数据类型", self.data_type_combo)
        form.addRow("寄存器地址", self.register_input)
        form.addRow("采集超时", self.timeout_spin)
        form.addRow("", self.default_checkbox)
        self._sync_protocol_fields(self.protocol_input.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _sync_protocol_fields(self, protocol_type: str) -> None:
        is_rtu = protocol_type == "modbus_rtu"
        self.connection_combo.setCurrentText("serial" if is_rtu else "tcp")
        self.connection_combo.setEnabled(not is_rtu)
        self.serial_profile_combo.setEnabled(is_rtu)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入设备名称。")
            self.name_input.setFocus()
            return
        if not self.data_type_combo.currentText().strip():
            QMessageBox.warning(self, "保存失败", "请选择数据类型。")
            self.data_type_combo.setFocus()
            return
        if not self.register_input.text().strip():
            QMessageBox.warning(self, "保存失败", "请输入寄存器地址。")
            self.register_input.setFocus()
            return
        if not self.register_input.text().strip().isdigit():
            QMessageBox.warning(self, "保存失败", "寄存器地址必须为数字。")
            self.register_input.setFocus()
            return
        if self.protocol_input.currentText() == "modbus_rtu" and not str(self.serial_profile_combo.currentData() or "").strip():
            QMessageBox.warning(self, "保存失败", "Modbus RTU 设备必须绑定一个串口配置。")
            self.serial_profile_combo.setFocus()
            return
        super().accept()

    def get_payload(self) -> dict:
        return {
            "profile_name": self.name_input.text().strip(),
            "protocol_type": self.protocol_input.currentText().strip(),
            "connection_type": self.connection_combo.currentText().strip(),
            "serial_profile_name": str(self.serial_profile_combo.currentData() or ""),
            "data_type": self.data_type_combo.currentText().strip(),
            "register_address": self.register_input.text().strip(),
            "collect_timeout_seconds": self.timeout_spin.value(),
            "is_default": self.default_checkbox.isChecked(),
        }


class FactorCatalogDialog(QDialog):
    def __init__(self, factors: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("常规因子字典")
        self.setMinimumSize(760, 520)
        hint = QLabel("支持直接编辑表格内容；新增后的因子会自动出现在设备因子绑定的下拉框中。")
        hint.setStyleSheet("font-size: 13px; color: #486581;")
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["因子编码", "因子名称", "单位"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setRowCount(0)

        for factor in factors:
            self._append_row(factor)

        add_button = QPushButton("新增因子")
        remove_button = QPushButton("删除选中因子")
        add_button.clicked.connect(lambda: self._append_row())
        remove_button.clicked.connect(self._remove_current_row)

        toolbar = QHBoxLayout()
        toolbar.addWidget(add_button)
        toolbar.addWidget(remove_button)
        toolbar.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(toolbar)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def _append_row(self, factor: dict | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        factor = factor or {"code": "", "name": "", "unit": ""}
        self.table.setItem(row, 0, QTableWidgetItem(str(factor.get("code", ""))))
        self.table.setItem(row, 1, QTableWidgetItem(str(factor.get("name", ""))))
        self.table.setItem(row, 2, QTableWidgetItem(str(factor.get("unit", ""))))

    def _remove_current_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def accept(self) -> None:
        seen_codes: set[str] = set()
        for row in range(self.table.rowCount()):
            code = self.table.item(row, 0).text().strip() if self.table.item(row, 0) else ""
            name = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
            if not code or not name:
                QMessageBox.warning(self, "保存失败", "常规因子的编码和名称不能为空。")
                self.table.setCurrentCell(row, 0 if not code else 1)
                self.table.setFocus()
                return
            if code in seen_codes:
                QMessageBox.warning(self, "保存失败", f"检测到重复因子编码：{code}")
                self.table.setCurrentCell(row, 0)
                self.table.setFocus()
                return
            seen_codes.add(code)
        super().accept()

    def get_payload(self) -> list[dict]:
        rows: list[dict] = []
        for row in range(self.table.rowCount()):
            rows.append(
                {
                    "code": self.table.item(row, 0).text().strip() if self.table.item(row, 0) else "",
                    "name": self.table.item(row, 1).text().strip() if self.table.item(row, 1) else "",
                    "unit": self.table.item(row, 2).text().strip() if self.table.item(row, 2) else "",
                }
            )
        return rows


class MetricConfigDialog(QDialog):
    def __init__(self, device: dict, metrics: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"指标阈值配置 - {device['device_code']}")
        self.setMinimumSize(860, 420)
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(7)
        self.metrics_table.setHorizontalHeaderLabels(["ID", "指标编码", "指标名称", "单位", "下限", "上限", "寄存器"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        self.metrics_table.setRowCount(len(metrics))

        for row_index, metric in enumerate(metrics):
            readonly_values = [metric["id"], metric["metric_code"], metric["metric_name"], metric["metric_unit"]]
            for column_index, value in enumerate(readonly_values):
                item = QTableWidgetItem("" if value is None else str(value))
                if column_index < 4:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.metrics_table.setItem(row_index, column_index, item)

            lower_spin = QDoubleSpinBox()
            lower_spin.setRange(-9999.0, 9999.0)
            lower_spin.setDecimals(2)
            lower_spin.setSpecialValueText("未设置")
            lower_spin.setValue(metric["lower_limit"] if metric["lower_limit"] is not None else -9999.0)
            self.metrics_table.setCellWidget(row_index, 4, lower_spin)

            upper_spin = QDoubleSpinBox()
            upper_spin.setRange(-9999.0, 9999.0)
            upper_spin.setDecimals(2)
            upper_spin.setSpecialValueText("未设置")
            upper_spin.setValue(metric["upper_limit"] if metric["upper_limit"] is not None else -9999.0)
            self.metrics_table.setCellWidget(row_index, 5, upper_spin)
            self.metrics_table.setItem(row_index, 6, QTableWidgetItem(metric["register_address"]))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.metrics_table)
        layout.addWidget(buttons)

    def _spin_value(self, widget: QDoubleSpinBox) -> float | None:
        return None if widget.value() == -9999.0 else widget.value()

    def get_payload(self) -> list[dict]:
        payload: list[dict] = []
        for row_index in range(self.metrics_table.rowCount()):
            payload.append(
                {
                    "id": int(self.metrics_table.item(row_index, 0).text()),
                    "lower_limit": self._spin_value(self.metrics_table.cellWidget(row_index, 4)),
                    "upper_limit": self._spin_value(self.metrics_table.cellWidget(row_index, 5)),
                    "register_address": self.metrics_table.item(row_index, 6).text(),
                    "sort_order": row_index + 1,
                }
            )
        return payload


class FactorBindingDialog(QDialog):
    def __init__(self, device: dict, metrics: list[dict], factor_catalog: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"因子配置 - {device['device_code']}")
        self.setMinimumSize(920, 520)
        self.device = device
        self.factor_catalog = factor_catalog
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(5)
        self.metrics_table.setHorizontalHeaderLabels(["ID", "设备名称", "常规因子", "下限", "上限"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        self.metrics_table.setRowCount(0)

        for metric in metrics:
            self._append_row(metric)

        hint = QLabel(f"当前绑定设备: {device['device_name']} / {device['device_code']}。因子编码、名称、单位将自动关联常规因子字典，设备通信参数已由采集设置承接。")
        hint.setStyleSheet("font-size: 13px; color: #486581;")

        self.add_row_button = QPushButton("新增因子")
        self.remove_row_button = QPushButton("删除选中因子")
        self.add_row_button.clicked.connect(lambda: self._append_row())
        self.remove_row_button.clicked.connect(self._remove_current_row)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.add_row_button)
        toolbar.addWidget(self.remove_row_button)
        toolbar.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(toolbar)
        layout.addWidget(self.metrics_table)
        layout.addWidget(buttons)

    def _append_row(self, metric: dict | None = None) -> None:
        row = self.metrics_table.rowCount()
        self.metrics_table.insertRow(row)
        metric = metric or {}
        factor_combo = QComboBox()
        factor_combo.addItem("请选择因子", None)
        selected_index = 0
        for index, factor in enumerate(self.factor_catalog, start=1):
            factor_combo.addItem(f"{factor['name']} / {factor['code']}", factor)
            if factor["code"] == str(metric.get("metric_code", "")).strip():
                selected_index = index
        factor_combo.setCurrentIndex(selected_index)

        self.metrics_table.setItem(row, 0, QTableWidgetItem(str(metric.get("id", ""))))
        device_name_item = QTableWidgetItem(self.device["device_name"])
        device_name_item.setFlags(device_name_item.flags() & ~Qt.ItemIsEditable)
        self.metrics_table.setItem(row, 1, device_name_item)
        self.metrics_table.setCellWidget(row, 2, factor_combo)
        self.metrics_table.setItem(row, 3, QTableWidgetItem("" if metric.get("lower_limit") is None else str(metric.get("lower_limit"))))
        self.metrics_table.setItem(row, 4, QTableWidgetItem("" if metric.get("upper_limit") is None else str(metric.get("upper_limit"))))

    def _remove_current_row(self) -> None:
        row = self.metrics_table.currentRow()
        if row >= 0:
            self.metrics_table.removeRow(row)

    def accept(self) -> None:
        if self.metrics_table.rowCount() == 0:
            QMessageBox.warning(self, "保存失败", "请至少配置一个监测因子。")
            return
        seen_codes: set[str] = set()
        for row in range(self.metrics_table.rowCount()):
            combo = self.metrics_table.cellWidget(row, 2)
            factor = combo.currentData() if isinstance(combo, QComboBox) else None
            metric_code = str(factor.get("code", "")).strip() if factor else ""
            metric_name = str(factor.get("name", "")).strip() if factor else ""
            if not metric_code or not metric_name:
                QMessageBox.warning(self, "保存失败", "请先为每一行选择常规因子。")
                self.metrics_table.setCurrentCell(row, 2)
                self.metrics_table.setFocus()
                return
            if metric_code in seen_codes:
                QMessageBox.warning(self, "保存失败", f"检测到重复因子绑定：{metric_name}")
                self.metrics_table.setCurrentCell(row, 2)
                self.metrics_table.setFocus()
                return
            seen_codes.add(metric_code)
        super().accept()

    def get_payload(self) -> list[dict]:
        payload: list[dict] = []
        for row in range(self.metrics_table.rowCount()):
            combo = self.metrics_table.cellWidget(row, 2)
            factor = combo.currentData() if isinstance(combo, QComboBox) else None
            payload.append(
                {
                    "id": self.metrics_table.item(row, 0).text() if self.metrics_table.item(row, 0) else "",
                    "metric_code": str(factor.get("code", "")).strip() if factor else "",
                    "lower_limit": self.metrics_table.item(row, 3).text().strip() if self.metrics_table.item(row, 3) else "",
                    "upper_limit": self.metrics_table.item(row, 4).text().strip() if self.metrics_table.item(row, 4) else "",
                }
            )
        return payload


class DeviceTemplateDialog(QDialog):
    def __init__(self, target_device: dict, candidates: list[dict], title: str, tip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 220)
        self._candidates = candidates

        target_label = QLabel(f"目标设备: {target_device['device_code']} / {target_device['device_name']}")
        target_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #102a43;")
        tip_label = QLabel(tip)
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("font-size: 13px; color: #486581;")

        self.source_combo = QComboBox()
        for item in candidates:
            self.source_combo.addItem(
                f"{item['device_code']} / {item['device_name']} / {item['device_type']}",
                item["id"],
            )

        form = QFormLayout()
        form.addRow("模板来源", self.source_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(target_label)
        layout.addWidget(tip_label)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def selected_device_id(self) -> int | None:
        if self.source_combo.count() == 0:
            return None
        return int(self.source_combo.currentData())


class InfoCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.value_label = QLabel("0")
        self.title_label = QLabel(title)
        self.setObjectName("infoCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        self.title_label.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 600;")
        self.value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class LastPacketDialog(QDialog):
    def __init__(self, snapshot: LastPacketSnapshot, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("最后一帧报文")
        self.setMinimumSize(860, 420)

        summary = QLabel(
            f"目标 TCP：{snapshot.endpoint} | 网关：{snapshot.gateway_code} | ACK：{snapshot.ack_policy} | 等待：{snapshot.ack_timeout_seconds:g} 秒"
        )
        summary.setStyleSheet("font-size: 13px; color: #486581; font-weight: 600;")

        self.packet_text = QTextEdit()
        self.packet_text.setReadOnly(True)
        self.packet_text.setPlainText(snapshot.packet_text or "当前还没有发送过报文。")

        copy_button = QPushButton("复制报文")
        close_button = QPushButton("关闭")
        copy_button.clicked.connect(self.copy_packet)
        close_button.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addWidget(copy_button)
        actions.addStretch()
        actions.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(self.packet_text, 1)
        layout.addLayout(actions)

    def copy_packet(self) -> None:
        QApplication.clipboard().setText(self.packet_text.toPlainText())


class BackgroundTaskSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class BackgroundTask(QRunnable):
    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self.task = task
        self.signals = BackgroundTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.finished.emit(self.task())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = DesktopDataService()
        self.protocol_options = self.service.fetch_device_protocol_options()
        self.connection_options = self.service.fetch_device_connection_options()
        self.runtime_settings = self.service.fetch_runtime_settings()
        self.platform_settings = self.service.fetch_platform_settings()
        self.acquisition_settings = self.service.fetch_acquisition_settings()
        self.acquisition_profiles = self.service.fetch_acquisition_profiles()
        self.serial_settings = self.service.fetch_serial_settings()
        self.serial_profiles = self.service.fetch_serial_profiles()
        self.factor_catalog = self.service.fetch_factor_catalog()
        self.site_rows = self.service.fetch_sites()
        self.platform_runtime_status = self.service.fetch_platform_runtime_status()
        self.last_packet_snapshot = self.service.fetch_last_packet_snapshot()

        self.device_rows: list[dict] = []
        self.alert_rows: list[dict] = []
        self.query_result_rows: dict[str, list[dict]] = {"realtime": [], "minute": [], "hour": []}
        self.analysis_summary = self.service.fetch_analysis_summary()
        self.cards: dict[str, InfoCard] = {}
        self.collect_scope = "all"
        self.project_root = Path(__file__).resolve().parents[3]
        self.thread_pool = QThreadPool.globalInstance()
        self.background_tasks: list[BackgroundTask] = []
        self.auto_collect_running = False
        self.upload_running = False

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.run_auto_collect)

        self.nav_list = QListWidget()
        self.page_stack = QStackedWidget()
        self.settings_tabs = QTabWidget()
        self.device_settings_tabs = QTabWidget()
        self.query_tabs = QTabWidget()

        self.device_table = QTableWidget()
        self.latest_table = QTableWidget()
        self.alert_table = QTableWidget()
        self.upload_table = QTableWidget()
        self.query_table = QTableWidget()
        self.minute_query_table = QTableWidget()
        self.hour_query_table = QTableWidget()
        self.home_trend_table = QTableWidget()
        self.analysis_table = QTableWidget()
        self.analysis_threshold_table = QTableWidget()
        self.analysis_advice_text = QTextEdit()
        self.settings_device_table = QTableWidget()
        self.factor_table = QTableWidget()
        self.site_table = QTableWidget()
        self.serial_table = QTableWidget()
        self.acquisition_table = QTableWidget()

        self.refresh_button = QPushButton("刷新首页")
        self.quick_platform_test_button = QPushButton("测试平台")
        self.quick_collect_button = QPushButton("采集选中设备")
        self.quick_upload_button = QPushButton("上传待处理数据")
        self.quick_ack_button = QPushButton("确认告警")
        self.last_packet_button = QPushButton("查看最后一帧")

        self.query_mode_label = QLabel()
        self.query_pond_input = QLineEdit()
        self.query_device_input = QLineEdit()
        self.query_metric_input = QLineEdit()
        self.query_start_date = QDateEdit()
        self.query_end_date = QDateEdit()
        self.query_button = QPushButton("查询数据")
        self.query_reset_button = QPushButton("清空条件")
        self.export_query_button = QPushButton("导出当前结果")

        self.auto_save_label = QLabel()
        self.platform_label = QLabel()
        self.platform_runtime_label = QLabel()
        self.packet_policy_label = QLabel()
        self.upload_cache_label = QLabel()
        self.time_alignment_label = QLabel()

        self.all_devices_radio = QRadioButton("全部设备")
        self.selected_devices_radio = QRadioButton("仅选中设备")
        self.collect_scope_group = QButtonGroup(self)

        self.runtime_enable_checkbox = QCheckBox("启用实时入库")
        self.runtime_interval_select = QComboBox()
        self.platform_host_input = QLineEdit()
        self.platform_port_spin = QSpinBox()
        self.platform_site_input = QComboBox()
        self.platform_gateway_input = QLineEdit()

        self.save_basic_button = QPushButton("保存基本参数")
        self.save_platform_button = QPushButton("保存平台配置")
        self.test_platform_button = QPushButton("测试平台连接")
        self.add_serial_button = QPushButton("新增串口")
        self.edit_serial_button = QPushButton("编辑串口")
        self.delete_serial_button = QPushButton("删除串口")
        self.add_acquisition_button = QPushButton("新增采集模板")
        self.edit_acquisition_button = QPushButton("编辑采集模板")
        self.delete_acquisition_button = QPushButton("删除采集模板")
        self.add_site_button = QPushButton("新增站点")
        self.edit_site_button = QPushButton("编辑站点")
        self.delete_site_button = QPushButton("删除站点")
        self.add_device_button = QPushButton("新增设备")
        self.edit_device_button = QPushButton("编辑设备")
        self.copy_device_button = QPushButton("复制设备配置")
        self.test_device_button = QPushButton("测试连接")
        self.factor_config_button = QPushButton("编辑因子绑定")
        self.copy_factor_button = QPushButton("按同型号复制因子")
        self.factor_catalog_button = QPushButton("管理常规因子")

        self.refresh_button.setToolTip("刷新首页统计、设备状态、告警和上传任务。")
        self.quick_platform_test_button.setToolTip("先检查平台 IP/端口是否可连通，适合现场联调前先点一次。")
        self.quick_collect_button.setToolTip("对首页选中的设备执行一次采集；若配置未完成，会先提示缺项。")
        self.quick_upload_button.setToolTip("立即上传待处理数据。")
        self.quick_ack_button.setToolTip("确认首页选中的告警记录。")
        self.last_packet_button.setToolTip("查看并复制 PC 端最近一次实际发送的原始报文。")
        self.all_devices_radio.setToolTip("自动采集时轮询全部设备。")
        self.selected_devices_radio.setToolTip("自动采集时仅处理首页当前选中的设备。")

        self._build_window()
        self._load_settings_to_form()
        self.apply_runtime_settings(self.runtime_settings)
        self._update_platform_label()
        self._update_platform_runtime_view()
        self._reset_query_inputs()
        self.refresh_dashboard()

    def _build_window(self) -> None:
        self.setWindowTitle("养虾监测软件")
        self.resize(1560, 960)
        self.setMinimumSize(1360, 840)
        self.setStatusBar(QStatusBar())

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav_list.setFixedWidth(180)
        self.nav_list.addItems(["首页", "参数设置", "数据查询", "数据分析"])
        self.nav_list.currentRowChanged.connect(self.page_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        root.addWidget(self.nav_list)
        root.addWidget(self.page_stack, 1)

        self.page_stack.addWidget(self._build_home_page())
        self.page_stack.addWidget(self._build_settings_page())
        self.page_stack.addWidget(self._build_query_page())
        self.page_stack.addWidget(self._build_analysis_page())

        self.setCentralWidget(central)
        self._apply_styles()

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title_box = QVBoxLayout()
        title = QLabel("首页")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
        subtitle = QLabel("只保留实时状态和实时数据信息，便于值守查看")
        subtitle.setStyleSheet("font-size: 14px; color: #486581;")
        self.auto_save_label.setStyleSheet("font-size: 13px; color: #0b7285; font-weight: 600;")
        self.platform_label.setStyleSheet("font-size: 13px; color: #486581; font-weight: 600;")
        self.platform_runtime_label.setStyleSheet("font-size: 13px; color: #1d4ed8; font-weight: 600;")
        self.packet_policy_label.setStyleSheet("font-size: 13px; color: #7c2d12; font-weight: 600;")
        self.upload_cache_label.setStyleSheet("font-size: 13px; color: #7c2d12; font-weight: 600;")
        self.time_alignment_label.setStyleSheet("font-size: 13px; color: #475569; font-weight: 600;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addWidget(self.auto_save_label)
        title_box.addWidget(self.platform_label)
        title_box.addWidget(self.platform_runtime_label)
        title_box.addWidget(self.packet_policy_label)
        title_box.addWidget(self.upload_cache_label)
        title_box.addWidget(self.time_alignment_label)
        actions = QHBoxLayout()
        for button, handler in [
            (self.refresh_button, self.refresh_dashboard),
            (self.quick_platform_test_button, self.test_platform_settings),
            (self.quick_collect_button, self.collect_selected_device),
            (self.quick_upload_button, self.upload_pending_tasks),
            (self.quick_ack_button, self.acknowledge_selected_alert),
            (self.last_packet_button, self.show_last_packet_dialog),
        ]:
            button.clicked.connect(handler)
            actions.addWidget(button)
        self.collect_scope_group.addButton(self.all_devices_radio)
        self.collect_scope_group.addButton(self.selected_devices_radio)
        self.all_devices_radio.setChecked(True)
        self.all_devices_radio.toggled.connect(lambda checked: self._set_collect_scope("all" if checked else self.collect_scope))
        self.selected_devices_radio.toggled.connect(lambda checked: self._set_collect_scope("selected" if checked else self.collect_scope))
        actions.addWidget(self.all_devices_radio)
        actions.addWidget(self.selected_devices_radio)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addLayout(actions)
        layout.addWidget(header)

        cards = QGridLayout()
        for index, (key, title_text, accent) in enumerate(
            [
                ("site_count", "养殖站点", "#0b7285"),
                ("device_count", "设备总数", "#1c7ed6"),
                ("online_device_count", "在线设备", "#2b8a3e"),
                ("alert_count", "活动告警", "#c92a2a"),
                ("pending_upload_count", "待上传任务", "#e67700"),
            ]
        ):
            card = InfoCard(title_text, accent)
            self.cards[key] = card
            cards.addWidget(card, 0, index)
        layout.addLayout(cards)

        layout.addWidget(
            self._build_table_panel(
                "重点指标趋势概览",
                self.home_trend_table,
                ["指标", "最新值", "最近走势", "趋势判断", "状态", "最近时间"],
            )
        )
        layout.addWidget(self._build_table_panel("设备实时状态", self.device_table, ["ID", "塘口", "设备编号", "设备名称", "设备型号", "协议", "连接", "状态", "最近采集"]))
        self.device_table.itemSelectionChanged.connect(self._update_auto_save_label)
        layout.addWidget(self._build_table_panel("实时监测数据", self.latest_table, ["塘口", "设备", "指标", "数值", "质量", "采集时间"]))
        bottom_tables = QGridLayout()
        bottom_tables.setHorizontalSpacing(16)
        bottom_tables.setVerticalSpacing(16)
        bottom_tables.addWidget(
            self._build_table_panel("活动告警", self.alert_table, ["设备", "告警编码", "级别", "状态", "内容", "触发时间", "恢复时间"]),
            0,
            0,
        )
        bottom_tables.addWidget(
            self._build_table_panel("上传联调日志", self.upload_table, ["设备编号", "命令码", "数据时间", "状态", "发送结果", "创建时间"]),
            0,
            1,
        )
        layout.addLayout(bottom_tables)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        title = QLabel("参数设置")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
        subtitle = QLabel("统一管理站点、平台、串口、设备、因子等全部设置项")
        subtitle.setStyleSheet("font-size: 14px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.settings_tabs.addTab(self._build_basic_settings_panel(), "基本参数")
        self.settings_tabs.addTab(self._build_site_settings_panel(), "站点管理")
        self.settings_tabs.addTab(self._build_platform_settings_panel(), "平台配置")
        self.settings_tabs.addTab(self._build_acquisition_settings_panel(), "设备设置")
        self.settings_tabs.addTab(self._build_device_settings_panel(), "设备配置")
        layout.addWidget(self.settings_tabs, 1)
        return page

    def _build_query_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        title = QLabel("数据查询")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
        subtitle = QLabel("支持实时、分钟、小时三个层级的数据查看与筛选")
        subtitle.setStyleSheet("font-size: 14px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        query_form = QFrame()
        query_form.setObjectName("panel")
        form_layout = QHBoxLayout(query_form)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)
        self.query_mode_label.setText("实时数据查询")
        self.query_start_date.setCalendarPopup(True)
        self.query_end_date.setCalendarPopup(True)
        self.query_start_date.setDisplayFormat("yyyy-MM-dd")
        self.query_end_date.setDisplayFormat("yyyy-MM-dd")
        self.query_button.clicked.connect(self.run_query)
        self.query_reset_button.clicked.connect(self.reset_query)
        self.export_query_button.clicked.connect(self.export_current_query)
        for widget in [
            QLabel("查询模式"),
            self.query_mode_label,
            QLabel("塘口"),
            self.query_pond_input,
            QLabel("设备"),
            self.query_device_input,
            QLabel("指标"),
            self.query_metric_input,
            QLabel("开始日期"),
            self.query_start_date,
            QLabel("结束日期"),
            self.query_end_date,
            self.query_button,
            self.query_reset_button,
            self.export_query_button,
        ]:
            form_layout.addWidget(widget)

        headers = ["塘口", "设备编号", "设备名称", "指标编码", "指标名称", "数值", "质量", "时间"]
        self.query_tabs.addTab(self._build_table_panel("实时数据查询结果", self.query_table, headers), "实时数据")
        self.query_tabs.addTab(self._build_table_panel("分钟数据查询结果", self.minute_query_table, headers), "分钟数据")
        self.query_tabs.addTab(self._build_table_panel("小时数据查询结果", self.hour_query_table, headers), "小时数据")
        self.query_tabs.currentChanged.connect(self._on_query_tab_changed)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        right_layout.addWidget(query_form)
        right_layout.addWidget(self.query_tabs, 1)
        layout.addLayout(right_layout, 1)
        return page

    def _build_analysis_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        title = QLabel("数据分析")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
        subtitle = QLabel("依据本项目地表水技术要求目录与可配置阈值，分析水温、pH、溶解氧、电导率、浊度等趋势；建议需结合现场复核")
        subtitle.setStyleSheet("font-size: 14px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.analysis_advice_text.setReadOnly(True)
        self.analysis_advice_text.setMinimumHeight(110)
        layout.addWidget(self.analysis_advice_text)
        layout.addWidget(
            self._build_table_panel(
                "指标趋势分析",
                self.analysis_table,
                ["指标编码", "指标名称", "最新值", "最近走势", "均值", "最小", "最大", "样本数", "趋势", "状态", "质量提示", "最近时间"],
            ),
            2,
        )
        layout.addWidget(
            self._build_table_panel(
                "分析阈值配置说明",
                self.analysis_threshold_table,
                ["指标编码", "下限", "上限", "来源", "建议"],
            ),
            1,
        )
        return page

    def _build_basic_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("基本参数")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        layout.addWidget(title)
        form = QFormLayout()
        self.runtime_interval_select.addItem("30 秒", 30)
        self.runtime_interval_select.addItem("60 秒", 60)
        form.addRow("启用实时入库", self.runtime_enable_checkbox)
        form.addRow("实时保存间隔", self.runtime_interval_select)
        layout.addLayout(form)
        self.save_basic_button.clicked.connect(self.save_basic_settings)
        layout.addWidget(self.save_basic_button)
        layout.addStretch()
        return panel

    def _build_platform_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("平台配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        layout.addWidget(title)
        form = QFormLayout()
        self.platform_port_spin.setRange(1, 65535)
        form.addRow("平台 IP", self.platform_host_input)
        form.addRow("平台端口", self.platform_port_spin)
        form.addRow("站点编码", self.platform_site_input)
        form.addRow("网关编码", self.platform_gateway_input)
        layout.addLayout(form)
        actions = QHBoxLayout()
        self.save_platform_button.clicked.connect(self.save_platform_settings)
        self.test_platform_button.clicked.connect(self.test_platform_settings)
        actions.addWidget(self.save_platform_button)
        actions.addWidget(self.test_platform_button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        return panel

    def _build_site_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("站点管理")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        desc = QLabel("统一维护养殖站点基础信息，平台配置与设备归属都从这里选择。")
        desc.setStyleSheet("font-size: 13px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(desc)
        actions = QHBoxLayout()
        for button, handler in [
            (self.add_site_button, self.open_add_site_dialog),
            (self.edit_site_button, self.open_edit_site_dialog),
            (self.delete_site_button, self.delete_selected_site),
        ]:
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self._setup_table(self.site_table, ["ID", "站点编码", "站点名称", "联系人", "联系电话"])
        self.site_table.doubleClicked.connect(lambda *_: self.open_edit_site_dialog())
        layout.addWidget(self.site_table)
        return panel

    def _build_acquisition_settings_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = QLabel("设备设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        desc = QLabel("通过页内子菜单切换串口设置、采集设置和因子配置，避免长页面来回滚动。")
        desc.setStyleSheet("font-size: 13px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(desc)
        self.device_settings_tabs.clear()
        self.device_settings_tabs.addTab(self._build_serial_settings_panel(), "串口设置")
        self.device_settings_tabs.addTab(self._build_default_acquisition_panel(), "采集设置")
        self.device_settings_tabs.addTab(self._build_factor_settings_panel(), "因子配置")
        layout.addWidget(self.device_settings_tabs, 1)
        return container

    def _build_serial_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("串口设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        desc = QLabel("支持维护多个串口配置，串口号限定为 COM1 到 COM20，可指定默认配置。")
        desc.setStyleSheet("font-size: 13px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(desc)
        actions = QHBoxLayout()
        for button, handler in [
            (self.add_serial_button, self.open_add_serial_dialog),
            (self.edit_serial_button, self.open_edit_serial_dialog),
            (self.delete_serial_button, self.delete_selected_serial_dialog),
        ]:
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self._setup_table(self.serial_table, ["配置名称", "串口号", "波特率", "数据位", "校验位", "停止位", "设备地址", "是否默认"])
        self.serial_table.doubleClicked.connect(lambda *_: self.open_edit_serial_dialog())
        layout.addWidget(self.serial_table)
        return panel

    def _build_default_acquisition_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("采集设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        desc = QLabel("支持维护多个采集模板，协议当前限制为 Modbus TCP 和 Modbus RTU；RTU 模板需配置数据类型、寄存器地址和绑定串口。")
        desc.setStyleSheet("font-size: 13px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(desc)
        actions = QHBoxLayout()
        for button, handler in [
            (self.add_acquisition_button, self.open_add_acquisition_profile_dialog),
            (self.edit_acquisition_button, self.open_edit_acquisition_profile_dialog),
            (self.delete_acquisition_button, self.delete_selected_acquisition_profile),
        ]:
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self._setup_table(self.acquisition_table, ["设备名称", "协议类型", "连接方式", "绑定串口", "数据类型", "寄存器地址", "超时(秒)", "是否默认"])
        self.acquisition_table.doubleClicked.connect(lambda *_: self.open_edit_acquisition_profile_dialog())
        layout.addWidget(self.acquisition_table)
        return panel

    def _build_device_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("设备配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        layout.addWidget(title)
        action_bar = QHBoxLayout()
        for button, handler in [
            (self.add_device_button, self.open_add_device_dialog),
            (self.edit_device_button, self.open_device_config_dialog),
            (self.copy_device_button, self.copy_selected_device_configuration),
            (self.test_device_button, self.test_selected_device_connection),
        ]:
            button.clicked.connect(handler)
            action_bar.addWidget(button)
        action_bar.addStretch()
        layout.addLayout(action_bar)
        self._setup_table(self.settings_device_table, ["ID", "站点", "塘口", "设备编号", "设备名称", "设备型号", "协议", "连接", "配置完整度", "状态", "最近采集"])
        self.settings_device_table.doubleClicked.connect(lambda *_: self.open_device_config_dialog())
        layout.addWidget(self.settings_device_table)
        return panel

    def _build_factor_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("因子配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #102a43;")
        desc = QLabel("在设备设置流程中，先选中目标设备名称，再绑定常规水质因子并维护阈值；因子编码、名称、单位自动关联因子字典。")
        desc.setStyleSheet("font-size: 13px; color: #486581;")
        layout.addWidget(title)
        layout.addWidget(desc)
        self.factor_config_button.clicked.connect(self.open_factor_binding_dialog)
        self.copy_factor_button.clicked.connect(self.copy_selected_factor_bindings)
        self.factor_catalog_button.clicked.connect(self.open_factor_catalog_dialog)
        actions = QHBoxLayout()
        actions.addWidget(self.factor_config_button)
        actions.addWidget(self.copy_factor_button)
        actions.addWidget(self.factor_catalog_button)
        actions.addStretch()
        layout.addLayout(actions)
        self._setup_table(self.factor_table, ["设备编号", "设备名称", "设备型号", "协议", "已绑因子数", "已绑因子", "配置完整度", "状态"])
        self.factor_table.doubleClicked.connect(lambda *_: self.open_factor_binding_dialog())
        layout.addWidget(self.factor_table)
        return panel

    def _build_table_panel(self, title_text: str, table: QTableWidget, headers: list[str]) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #102a43;")
        layout.addWidget(title)
        self._setup_table(table, headers)
        layout.addWidget(table)
        return panel

    def _setup_table(self, table: QTableWidget, headers: Iterable[str]) -> None:
        table.setColumnCount(len(list(headers)))
        table.setHorizontalHeaderLabels(list(headers))
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

    def _apply_styles(self) -> None:
        QApplication.instance().setFont(QFont("Microsoft YaHei UI", 10))
        self.setStyleSheet(
            """
            QMainWindow { background-color: #f4f7fb; }
            QListWidget { background: #0f172a; color: #e2e8f0; border: none; padding: 12px; font-size: 14px; }
            QListWidget::item { padding: 12px 14px; border-radius: 10px; margin: 4px 0; }
            QListWidget::item:selected { background: #164e63; color: white; }
            QFrame#panel, QFrame#infoCard { background-color: #ffffff; border: 1px solid #d9e2ec; border-radius: 18px; }
            QPushButton { background-color: #0b7285; color: white; border: none; border-radius: 10px; padding: 10px 16px; font-size: 14px; font-weight: 600; }
            QPushButton:hover { background-color: #095c6b; }
            QTableWidget { background: #ffffff; alternate-background-color: #f8fbff; border: none; color: #102a43; }
            QHeaderView::section { background-color: #e9f2f9; color: #243b53; border: none; border-bottom: 1px solid #d9e2ec; padding: 8px; font-weight: 700; }
            QLineEdit, QComboBox, QDateEdit, QTextEdit, QSpinBox, QDoubleSpinBox { border: 1px solid #cbd5e1; border-radius: 8px; padding: 6px 8px; background: white; }
            """
        )

    def _load_settings_to_form(self) -> None:
        self.runtime_enable_checkbox.setChecked(self.runtime_settings.auto_save_enabled)
        interval_index = self.runtime_interval_select.findData(self.runtime_settings.save_interval_seconds)
        self.runtime_interval_select.setCurrentIndex(interval_index if interval_index >= 0 else 0)

        self.platform_host_input.setText(self.platform_settings.platform_host)
        self.platform_port_spin.setValue(self.platform_settings.platform_port)
        self.platform_gateway_input.setText(self.platform_settings.gateway_code)
        self._reload_site_choices(selected_site_code=self.platform_settings.site_code)

    def _reload_site_choices(self, selected_site_code: str = "") -> None:
        self.site_rows = self.service.fetch_sites()
        self.platform_site_input.clear()
        target_index = -1
        for index, site in enumerate(self.site_rows):
            self.platform_site_input.addItem(f"{site['site_code']} / {site['site_name']}", site["site_code"])
            if site["site_code"] == selected_site_code:
                target_index = index
        if target_index >= 0:
            self.platform_site_input.setCurrentIndex(target_index)
        elif self.platform_site_input.count() > 0:
            self.platform_site_input.setCurrentIndex(0)

    def _reset_query_inputs(self) -> None:
        today = QDate.currentDate()
        self.query_start_date.setDate(today.addDays(-7))
        self.query_end_date.setDate(today)

    def _query_granularity(self) -> str:
        mapping = {0: "realtime", 1: "minute", 2: "hour"}
        return mapping[self.query_tabs.currentIndex()]

    def _on_query_tab_changed(self, row: int) -> None:
        labels = ["实时数据查询", "分钟数据查询", "小时数据查询"]
        self.query_mode_label.setText(labels[row])
        self.run_query()

    def _set_collect_scope(self, scope: str) -> None:
        self.collect_scope = scope
        self._update_auto_save_label()
        if scope == "all":
            self.statusBar().showMessage("自动采集范围已切换为：全部设备", 3000)
        else:
            self.statusBar().showMessage(
                f"自动采集范围已切换为：仅选中设备（当前 {self._selected_home_device_count()} 台）",
                3000,
            )

    def _selected_home_device_count(self) -> int:
        selected_rows = {index.row() for index in self.device_table.selectedIndexes()}
        return len([row for row in selected_rows if 0 <= row < len(self.device_rows)])

    def _update_auto_save_label(self) -> None:
        if self.collect_scope == "all":
            scope_text = "全部设备"
            tooltip = "当前自动采集范围为全部设备。"
        else:
            selected_count = self._selected_home_device_count()
            scope_text = f"选中设备（{selected_count} 台）"
            tooltip = f"当前自动采集范围为首页选中的设备，已选 {selected_count} 台。"
        if self.runtime_settings.auto_save_enabled:
            self.auto_save_label.setText(f"实时入库已开启，保存间隔：{self.runtime_settings.save_interval_seconds} 秒，范围：{scope_text}")
        else:
            self.auto_save_label.setText(f"实时入库未开启，当前范围：{scope_text}")
        self.auto_save_label.setToolTip(f"用于查看当前实时入库开关、保存间隔和采集范围。{tooltip}")
        self.time_alignment_label.setText(
            "时间规整：数据时间按当前保存间隔向前规整，不会生成未来时间，用于平台查询和趋势对齐。"
        )
        self.time_alignment_label.setToolTip("例如 30 秒间隔会对齐到 HH:mm:00 或 HH:mm:30；60 秒间隔会对齐到整分钟。")

    def _update_platform_label(self) -> None:
        self.platform_label.setText(f"平台 TCP：{self.platform_settings.platform_host}:{self.platform_settings.platform_port} | 站点：{self.platform_settings.site_code} | 网关：{self.platform_settings.gateway_code}")
        self.platform_label.setToolTip("平台联调前可先使用首页“测试平台”或参数设置中的“测试平台连接”按钮确认 TCP 可达。")

    def _update_platform_runtime_view(self) -> None:
        status = self.platform_runtime_status
        snapshot = self.last_packet_snapshot
        upload_queue = self.service.fetch_upload_queue_status()
        last_send_time = status.last_send_time or "暂无"
        last_response = status.last_response or "暂无"
        self.platform_runtime_label.setText(
            f"连接状态：{status.connection_status} | 最后发送：{last_send_time} | 发送结果：{status.last_send_result} | ACK：{status.ack_status}"
        )
        self.platform_runtime_label.setToolTip(f"平台返回：{last_response}")
        self.packet_policy_label.setText(
            f"发送目标：{status.endpoint} | ACK 策略：{snapshot.ack_policy} | ACK等待：{snapshot.ack_timeout_seconds:g} 秒 | 最后一帧：{'已生成' if snapshot.packet_text else '暂无'}"
        )
        self.packet_policy_label.setToolTip("点击“查看最后一帧”可直接核对 MN、CN、DataTime 和因子编码。")
        self.upload_cache_label.setText(upload_queue.summary_text)
        self.upload_cache_label.setToolTip("补传、重试和重复跳过来自上传队列状态；同一轮同指纹报文不会重复发送。")

    def show_last_packet_dialog(self) -> None:
        self.last_packet_snapshot = self.service.fetch_last_packet_snapshot()
        dialog = LastPacketDialog(self.last_packet_snapshot, self)
        dialog.exec()

    def apply_runtime_settings(self, settings: RuntimeSettings) -> None:
        self.runtime_settings = settings
        if settings.auto_save_enabled:
            self.auto_save_timer.start(settings.save_interval_seconds * 1000)
        else:
            self.auto_save_timer.stop()
        self._update_auto_save_label()

    def save_basic_settings(self) -> None:
        try:
            self.runtime_settings = self.service.save_runtime_settings(
                self.runtime_enable_checkbox.isChecked(),
                int(self.runtime_interval_select.currentData()),
            )
            self.apply_runtime_settings(self.runtime_settings)
            self.statusBar().showMessage("基本参数已保存", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "保存基本参数失败", str(exc))

    def save_platform_settings(self) -> None:
        try:
            site_code = self.platform_site_input.currentData()
            if not site_code:
                raise ValueError("请先在站点管理中配置站点，再保存平台配置")
            if not self.platform_host_input.text().strip():
                raise ValueError("平台 IP 不能为空")
            if not self.platform_gateway_input.text().strip():
                raise ValueError("网关编码不能为空")
            self.platform_settings = self.service.save_platform_settings(
                self.platform_host_input.text(),
                self.platform_port_spin.value(),
                str(site_code),
                self.platform_gateway_input.text(),
            )
            self._update_platform_label()
            self.statusBar().showMessage("平台配置已保存", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "保存平台配置失败", str(exc))

    def _run_background_task(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_failure: Callable[[str], None],
    ) -> None:
        worker = BackgroundTask(task)
        self.background_tasks.append(worker)
        worker.signals.finished.connect(lambda _result, current=worker: self.background_tasks.remove(current))
        worker.signals.failed.connect(lambda _message, current=worker: self.background_tasks.remove(current))
        worker.signals.finished.connect(on_success)
        worker.signals.failed.connect(on_failure)
        self.thread_pool.start(worker)

    def test_platform_settings(self) -> None:
        try:
            site_code = self.platform_site_input.currentData()
            if not site_code:
                raise ValueError("请先在站点管理中配置站点，再测试平台连接")
            if not self.platform_host_input.text().strip():
                raise ValueError("平台 IP 不能为空")
            if not self.platform_gateway_input.text().strip():
                raise ValueError("网关编码不能为空")
            self.platform_settings = self.service.save_platform_settings(
                self.platform_host_input.text(),
                self.platform_port_spin.value(),
                str(site_code),
                self.platform_gateway_input.text(),
            )
            self._update_platform_label()
            result = self.service.test_platform_connection()
            self._show_connection_result(result)
            self.statusBar().showMessage(f"平台测试：{result.message}", 5000)
        except Exception as exc:
            self.statusBar().showMessage("平台测试失败，请检查平台参数后重试", 5000)
            QMessageBox.critical(self, "测试平台连接失败", str(exc))

    def open_add_serial_dialog(self) -> None:
        dialog = SerialConfigDialog(None, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                payload = dialog.get_payload()
                self.serial_profiles = self.service.save_serial_profile(
                    payload["profile_name"],
                    payload["port_name"],
                    payload["baudrate"],
                    payload["data_bits"],
                    payload["parity"],
                    payload["stop_bits"],
                    payload["slave_address"],
                    payload["is_default"],
                )
                self.serial_settings = self.service.fetch_serial_settings()
                self.refresh_dashboard()
                self.statusBar().showMessage("串口配置已新增", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "新增串口配置失败", str(exc))

    def open_edit_serial_dialog(self) -> None:
        profile = self._selected_serial_profile()
        if profile is None:
            QMessageBox.information(self, "请选择串口配置", "请先在串口设置列表中选择一个串口配置。")
            return
        dialog = SerialConfigDialog(profile, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                payload = dialog.get_payload()
                self.serial_profiles = self.service.save_serial_profile(
                    payload["profile_name"],
                    payload["port_name"],
                    payload["baudrate"],
                    payload["data_bits"],
                    payload["parity"],
                    payload["stop_bits"],
                    payload["slave_address"],
                    payload["is_default"],
                    original_name=profile.profile_name,
                )
                self.serial_settings = self.service.fetch_serial_settings()
                self.refresh_dashboard()
                self.statusBar().showMessage("串口配置已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存串口配置失败", str(exc))

    def delete_selected_serial_dialog(self) -> None:
        profile = self._selected_serial_profile()
        if profile is None:
            QMessageBox.information(self, "请选择串口配置", "请先在串口设置列表中选择一个串口配置。")
            return
        if QMessageBox.question(self, "确认删除", f"确认删除串口配置 {profile.profile_name} 吗？") != QMessageBox.Yes:
            return
        try:
            self.serial_profiles = self.service.delete_serial_profile(profile.profile_name)
            self.serial_settings = self.service.fetch_serial_settings()
            self.refresh_dashboard()
            self.statusBar().showMessage("串口配置已删除", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "删除串口配置失败", str(exc))

    def open_add_acquisition_profile_dialog(self) -> None:
        dialog = AcquisitionProfileDialog(None, [profile.profile_name for profile in self.serial_profiles], self)
        if dialog.exec() == QDialog.Accepted:
            try:
                payload = dialog.get_payload()
                self.acquisition_profiles = self.service.save_acquisition_profile(
                    payload["profile_name"],
                    payload["protocol_type"],
                    payload["connection_type"],
                    payload["serial_profile_name"],
                    payload["collect_timeout_seconds"],
                    payload["data_type"],
                    payload["register_address"],
                    payload["is_default"],
                )
                self.acquisition_settings = self.service.fetch_acquisition_settings()
                self.refresh_dashboard()
                self.statusBar().showMessage("采集模板已新增", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "新增采集模板失败", str(exc))

    def open_edit_acquisition_profile_dialog(self) -> None:
        profile = self._selected_acquisition_profile()
        if profile is None:
            QMessageBox.information(self, "请选择采集模板", "请先在采集设置列表中选择一个协议模板。")
            return
        dialog = AcquisitionProfileDialog(profile, [item.profile_name for item in self.serial_profiles], self)
        if dialog.exec() == QDialog.Accepted:
            try:
                payload = dialog.get_payload()
                self.acquisition_profiles = self.service.save_acquisition_profile(
                    payload["profile_name"],
                    payload["protocol_type"],
                    payload["connection_type"],
                    payload["serial_profile_name"],
                    payload["collect_timeout_seconds"],
                    payload["data_type"],
                    payload["register_address"],
                    payload["is_default"],
                    original_name=profile.profile_name,
                )
                self.acquisition_settings = self.service.fetch_acquisition_settings()
                self.refresh_dashboard()
                self.statusBar().showMessage("采集模板已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存采集模板失败", str(exc))

    def delete_selected_acquisition_profile(self) -> None:
        profile = self._selected_acquisition_profile()
        if profile is None:
            QMessageBox.information(self, "请选择采集模板", "请先在采集设置列表中选择一个采集模板。")
            return
        if QMessageBox.question(self, "确认删除", f"确认删除采集模板 {profile.profile_name} 吗？") != QMessageBox.Yes:
            return
        try:
            self.acquisition_profiles = self.service.delete_acquisition_profile(profile.profile_name)
            self.acquisition_settings = self.service.fetch_acquisition_settings()
            self.refresh_dashboard()
            self.statusBar().showMessage("采集模板已删除", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "删除采集模板失败", str(exc))

    def open_add_device_dialog(self) -> None:
        if not self.site_rows:
            QMessageBox.information(self, "缺少站点", "请先在参数设置 -> 站点管理中新增站点，再创建设备。")
            return
        default_site = next((site for site in self.site_rows if site["site_code"] == self.platform_settings.site_code), self.site_rows[0])
        dialog = DeviceConfigDialog(
            {
                "site_id": default_site["id"],
                "pond_code": "",
                "device_code": "",
                "device_name": "",
                "device_type": "",
                "protocol_type": self.acquisition_settings.default_protocol,
                "connection_type": self.acquisition_settings.default_connection,
                "sort_order": len(self.device_rows) + 1,
                "config_json": self.acquisition_settings.default_config_template,
            },
            self.protocol_options,
            self.connection_options,
            self.site_rows,
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            try:
                created = self.service.create_device(dialog.get_payload())
                self.refresh_dashboard()
                self.statusBar().showMessage(f"设备 {created['device_name']} 已新增", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "新增设备失败", str(exc))

    def _selected_settings_device_id(self) -> int | None:
        row_index = self.settings_device_table.currentRow()
        if row_index < 0 or row_index >= len(self.device_rows):
            return None
        return self.device_rows[row_index]["id"]

    def _selected_site_id(self) -> int | None:
        row_index = self.site_table.currentRow()
        if row_index < 0 or row_index >= len(self.site_rows):
            return None
        return self.site_rows[row_index]["id"]

    def _selected_acquisition_profile(self) -> AcquisitionProfile | None:
        row_index = self.acquisition_table.currentRow()
        if row_index < 0 or row_index >= len(self.acquisition_profiles):
            return None
        return self.acquisition_profiles[row_index]

    def _selected_serial_profile(self) -> SerialProfile | None:
        row_index = self.serial_table.currentRow()
        if row_index < 0 or row_index >= len(self.serial_profiles):
            return None
        return self.serial_profiles[row_index]

    def _selected_factor_device_id(self) -> int | None:
        row_index = self.factor_table.currentRow()
        if row_index < 0 or row_index >= len(self.device_rows):
            return None
        return self.device_rows[row_index]["id"]

    def _pick_template_device(
        self,
        target_device: dict,
        *,
        title: str,
        tip: str,
        device_type: str = "",
    ) -> int | None:
        candidates = self.service.fetch_device_template_candidates(device_type=device_type, exclude_device_id=target_device["id"])
        if not candidates:
            QMessageBox.information(self, "暂无可复用模板", "当前没有符合条件的模板设备，请先配置一台设备作为模板。")
            return None
        dialog = DeviceTemplateDialog(target_device, candidates, title, tip, self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.selected_device_id()

    def open_device_config_dialog(self) -> None:
        device_id = self._selected_settings_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在设备配置列表中选择一台设备。")
            return
        device = next(row for row in self.device_rows if row["id"] == device_id)
        dialog = DeviceConfigDialog(device, self.protocol_options, self.connection_options, self.site_rows, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                updated = self.service.update_device(device["id"], dialog.get_payload())
                self.refresh_dashboard()
                self.statusBar().showMessage(f"设备 {updated['device_name']} 配置已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存设备失败", str(exc))

    def open_add_site_dialog(self) -> None:
        dialog = SiteConfigDialog({}, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                created = self.service.create_site(dialog.get_payload())
                self._reload_site_choices(selected_site_code=created["site_code"])
                self.refresh_dashboard()
                self.statusBar().showMessage(f"站点 {created['site_name']} 已新增", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "新增站点失败", str(exc))

    def open_edit_site_dialog(self) -> None:
        site_id = self._selected_site_id()
        if site_id is None:
            QMessageBox.information(self, "请选择站点", "请先在站点管理列表中选择一个站点。")
            return
        site = next(row for row in self.site_rows if row["id"] == site_id)
        dialog = SiteConfigDialog(site, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                updated = self.service.update_site(site_id, dialog.get_payload())
                self._reload_site_choices(selected_site_code=updated["site_code"])
                if self.platform_settings.site_code == site["site_code"]:
                    self.platform_settings = self.service.save_platform_settings(
                        self.platform_settings.platform_host,
                        self.platform_settings.platform_port,
                        updated["site_code"],
                        self.platform_settings.gateway_code,
                    )
                    self._update_platform_label()
                self.refresh_dashboard()
                self.statusBar().showMessage(f"站点 {updated['site_name']} 已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存站点失败", str(exc))

    def delete_selected_site(self) -> None:
        site_id = self._selected_site_id()
        if site_id is None:
            QMessageBox.information(self, "请选择站点", "请先在站点管理列表中选择一个站点。")
            return
        site = next(row for row in self.site_rows if row["id"] == site_id)
        if QMessageBox.question(self, "确认删除", f"确认删除站点 {site['site_name']} 吗？") != QMessageBox.Yes:
            return
        try:
            self.service.delete_site(site_id)
            next_code = ""
            if self.platform_settings.site_code == site["site_code"]:
                remaining = [row for row in self.site_rows if row["id"] != site_id]
                next_code = remaining[0]["site_code"] if remaining else ""
                if next_code:
                    self.platform_settings = self.service.save_platform_settings(
                        self.platform_settings.platform_host,
                        self.platform_settings.platform_port,
                        next_code,
                        self.platform_settings.gateway_code,
                    )
                    self._update_platform_label()
            self._reload_site_choices(selected_site_code=next_code)
            self.refresh_dashboard()
            self.statusBar().showMessage(f"站点 {site['site_name']} 已删除", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "删除站点失败", str(exc))

    def copy_selected_device_configuration(self) -> None:
        device_id = self._selected_settings_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在设备配置列表中选择目标设备。")
            return
        target_device = next(row for row in self.device_rows if row["id"] == device_id)
        source_device_id = self._pick_template_device(
            target_device,
            title="复制设备配置",
            tip="复制后会覆盖目标设备的设备型号、协议类型、连接方式和连接参数。",
        )
        if source_device_id is None:
            return
        try:
            updated = self.service.copy_device_configuration(source_device_id, device_id)
            self.refresh_dashboard()
            self.statusBar().showMessage(f"设备 {updated['device_name']} 已复用模板配置", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "复制设备配置失败", str(exc))

    def open_metric_config_dialog(self) -> None:
        device_id = self._selected_settings_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在设备配置列表中选择一台设备。")
            return
        device = next(row for row in self.device_rows if row["id"] == device_id)
        metrics = self.service.fetch_device_metrics(device["id"])
        if not metrics:
            QMessageBox.information(self, "暂无指标", "当前设备还没有配置监测指标。")
            return
        dialog = MetricConfigDialog(device, metrics, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                self.service.save_device_metrics(device["id"], dialog.get_payload())
                self.statusBar().showMessage(f"设备 {device['device_name']} 指标阈值已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存指标阈值失败", str(exc))

    def open_factor_binding_dialog(self) -> None:
        device_id = self._selected_factor_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在因子配置列表中选择目标设备。")
            return
        device = next(row for row in self.device_rows if row["id"] == device_id)
        metrics = self.service.fetch_device_metrics(device_id)
        dialog = FactorBindingDialog(device, metrics, self.factor_catalog, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                self.service.save_factor_bindings(device_id, dialog.get_payload())
                self.statusBar().showMessage(f"设备 {device['device_name']} 的因子绑定已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存因子绑定失败", str(exc))

    def open_factor_catalog_dialog(self) -> None:
        dialog = FactorCatalogDialog(self.factor_catalog or DEFAULT_WATER_FACTORS, self)
        if dialog.exec() == QDialog.Accepted:
            try:
                self.factor_catalog = self.service.save_factor_catalog(dialog.get_payload())
                self.refresh_dashboard()
                self.statusBar().showMessage("常规因子字典已保存", 3000)
            except Exception as exc:
                QMessageBox.critical(self, "保存常规因子字典失败", str(exc))

    def copy_selected_factor_bindings(self) -> None:
        device_id = self._selected_factor_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在因子配置列表中选择目标设备。")
            return
        target_device = next(row for row in self.device_rows if row["id"] == device_id)
        source_device_id = self._pick_template_device(
            target_device,
            title="按同型号复制因子",
            tip="复制后会使用模板设备的因子绑定整体替换当前设备，适合同型号快速接入。",
            device_type=target_device.get("device_type", ""),
        )
        if source_device_id is None:
            return
        try:
            self.service.copy_factor_bindings(source_device_id, device_id)
            self.refresh_dashboard()
            self.statusBar().showMessage(f"设备 {target_device['device_name']} 已同步因子模板", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "复制因子模板失败", str(exc))

    def _show_connection_result(self, result: ConnectionTestResult) -> None:
        detail_text = "\n".join(result.details)
        message = f"{result.message}\n\n{detail_text}" if detail_text else result.message
        if result.success:
            QMessageBox.information(self, "连接测试结果", message)
        else:
            QMessageBox.warning(self, "连接测试结果", message)

    def test_selected_device_connection(self) -> None:
        device_id = self._selected_settings_device_id()
        if device_id is None:
            QMessageBox.information(self, "请选择设备", "请先在设备配置列表中选择一台设备。")
            return
        try:
            result = self.service.test_device_connection(device_id)
            self._show_connection_result(result)
            self.statusBar().showMessage(result.message, 5000)
        except Exception as exc:
            self.statusBar().showMessage("设备连接测试失败，请检查设备配置后重试", 5000)
            QMessageBox.critical(self, "连接测试失败", str(exc))

    def collect_selected_device(self) -> None:
        row_index = self.device_table.currentRow()
        if row_index < 0 or row_index >= len(self.device_rows):
            QMessageBox.information(self, "请选择设备", "请先在首页设备状态列表中选择一台设备。")
            return
        device = self.device_rows[row_index]
        if device.get("config_status") != "已完成":
            QMessageBox.warning(
                self,
                "暂不能试采",
                f"设备 {device['device_name']} 还有配置未完成：\n{device.get('config_hint', '请先完善设备配置。')}",
            )
            return
        self.quick_collect_button.setEnabled(False)
        self.statusBar().showMessage(f"正在采集设备 {device['device_code']}，界面仍可继续操作...", 5000)

        def on_success(result: object) -> None:
            self.quick_collect_button.setEnabled(True)
            self.refresh_dashboard()
            payload = result if isinstance(result, dict) else {}
            QMessageBox.information(
                self,
                "采集完成",
                f"设备 {payload.get('device_code', device['device_code'])} 已完成一次采集，采集到 {payload.get('metric_count', 0)} 个指标。",
            )

        def on_failure(message: str) -> None:
            self.quick_collect_button.setEnabled(True)
            self.statusBar().showMessage("试采失败，请检查设备配置或连接状态后重试", 5000)
            QMessageBox.critical(self, "试采失败", message)

        self._run_background_task(lambda: self.service.trigger_collect(device["id"]), on_success, on_failure)

    def run_auto_collect(self) -> None:
        if self.auto_collect_running:
            self.statusBar().showMessage("实时入库上一轮仍在执行，本轮已跳过以避免重复发包", 5000)
            return
        if self.collect_scope == "selected":
            selected_rows = sorted({index.row() for index in self.device_table.selectedIndexes()})
            device_ids = [
                self.device_rows[row_index]["id"]
                for row_index in selected_rows
                if 0 <= row_index < len(self.device_rows)
            ]
            if not device_ids:
                self.statusBar().showMessage("实时入库已跳过：当前范围为仅选中设备，但首页未选中设备", 5000)
                return
            task = lambda: self.service.auto_collect_selected_devices(device_ids)
        else:
            task = self.service.auto_collect_all_devices
        self.auto_collect_running = True
        self.statusBar().showMessage("实时入库后台执行中，界面仍可继续操作...", 5000)

        def on_success(result: object) -> None:
            self.auto_collect_running = False
            payload = result if isinstance(result, dict) else {}
            self.refresh_dashboard()
            self.statusBar().showMessage(
                f"实时入库完成：成功 {payload.get('device_count', 0)} 台，跳过 {payload.get('skipped_count', 0)} 台，写入 {payload.get('metric_count', 0)} 条指标",
                5000,
            )

        def on_failure(message: str) -> None:
            self.auto_collect_running = False
            self.auto_save_timer.stop()
            QMessageBox.critical(self, "实时入库失败", message)

        self._run_background_task(task, on_success, on_failure)

    def upload_pending_tasks(self) -> None:
        if self.upload_running:
            self.statusBar().showMessage("上传任务正在后台执行，请勿重复点击", 4000)
            return
        self.upload_running = True
        self.quick_upload_button.setEnabled(False)
        self.statusBar().showMessage("待上传数据后台发送中，界面仍可继续操作...", 5000)

        def on_success(result: object) -> None:
            self.upload_running = False
            self.quick_upload_button.setEnabled(True)
            payload = result if isinstance(result, dict) else {}
            self.refresh_dashboard()
            self.statusBar().showMessage(
                f"上传完成：处理 {payload.get('processed', 0)} 条，成功 {payload.get('uploaded', 0)} 条，失败 {payload.get('failed', 0)} 条，跳过重复 {payload.get('skipped', 0)} 条",
                5000,
            )

        def on_failure(message: str) -> None:
            self.upload_running = False
            self.quick_upload_button.setEnabled(True)
            QMessageBox.critical(self, "上传失败", message)

        self._run_background_task(self.service.upload_pending_tasks, on_success, on_failure)

    def retry_failed_upload_tasks(self) -> None:
        try:
            result = self.service.retry_failed_upload_tasks()
            self.refresh_dashboard()
            self.statusBar().showMessage(f"已重置 {result['reset']} 条失败任务，可重新上传", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "重试失败任务", str(exc))

    def acknowledge_selected_alert(self) -> None:
        row_index = self.alert_table.currentRow()
        if row_index < 0 or row_index >= len(self.alert_rows):
            QMessageBox.information(self, "请选择告警", "请先在首页告警表中选择一条告警。")
            return
        alert = self.alert_rows[row_index]
        if alert["status"] == "recovered":
            QMessageBox.information(self, "无需确认", "已恢复的告警无需再次确认。")
            return
        try:
            result = self.service.acknowledge_alert(alert["id"])
            self.refresh_dashboard()
            self.statusBar().showMessage(f"告警已确认，当前状态：{result['status']}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "确认告警失败", str(exc))

    def run_query(self) -> None:
        try:
            granularity = self._query_granularity()
            current_table = {
                "realtime": self.query_table,
                "minute": self.minute_query_table,
                "hour": self.hour_query_table,
            }[granularity]
            rows = self.service.query_telemetry(
                pond_code=self.query_pond_input.text(),
                device_keyword=self.query_device_input.text(),
                metric_keyword=self.query_metric_input.text(),
                start_date=self.query_start_date.date().toString("yyyy-MM-dd"),
                end_date=self.query_end_date.date().toString("yyyy-MM-dd"),
                granularity=granularity,
            )
            self.query_result_rows[granularity] = rows
            self._fill_table(
                current_table,
                [
                    [
                        r["pond_code"],
                        r["device_code"],
                        r["device_name"],
                        r["metric_code"],
                        r["metric_name"],
                        f"{r['metric_value']} {r['metric_unit']}".strip(),
                        r["quality"],
                        r["collected_at"],
                    ]
                    for r in rows
                ],
                status_column=6,
            )
            self.statusBar().showMessage(f"查询完成，共 {len(rows)} 条记录", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "数据查询失败", str(exc))

    def reset_query(self) -> None:
        self.query_pond_input.clear()
        self.query_device_input.clear()
        self.query_metric_input.clear()
        self._reset_query_inputs()
        self.query_table.setRowCount(0)
        self.minute_query_table.setRowCount(0)
        self.hour_query_table.setRowCount(0)
        self.query_result_rows = {"realtime": [], "minute": [], "hour": []}
        self.statusBar().showMessage("查询条件已清空", 3000)

    def export_current_query(self) -> None:
        granularity = self._query_granularity()
        rows = self.query_result_rows.get(granularity, [])
        if not rows:
            QMessageBox.information(self, "暂无结果可导出", "请先执行当前查询，确认有结果后再导出。")
            return
        try:
            file_path = self.service.export_query_rows_csv(self.project_root / "exports", rows, granularity)
            self.statusBar().showMessage(f"查询结果已导出: {file_path}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "导出查询结果失败", str(exc))

    def refresh_dashboard(self) -> None:
        stats = self.service.fetch_overview()
        self.cards["site_count"].set_value(str(stats.site_count))
        self.cards["device_count"].set_value(str(stats.device_count))
        self.cards["online_device_count"].set_value(str(stats.online_device_count))
        self.cards["alert_count"].set_value(str(stats.alert_count))
        self.cards["pending_upload_count"].set_value(str(stats.pending_upload_count))

        self.serial_settings = self.service.fetch_serial_settings()
        self.acquisition_settings = self.service.fetch_acquisition_settings()
        self.acquisition_profiles = self.service.fetch_acquisition_profiles()
        self.serial_profiles = self.service.fetch_serial_profiles()
        self.factor_catalog = self.service.fetch_factor_catalog()
        self.platform_runtime_status = self.service.fetch_platform_runtime_status()
        self.last_packet_snapshot = self.service.fetch_last_packet_snapshot()
        self.analysis_summary = self.service.fetch_analysis_summary()
        self._refresh_home_trend_view()
        self.site_rows = self.service.fetch_sites()
        self.device_rows = self.service.fetch_devices()
        device_rows = [
            [
                r["id"],
                r["pond_code"],
                r["device_code"],
                r["device_name"],
                r["device_type"],
                r["protocol_type"],
                r["connection_type"],
                r["status"],
                r["last_collected_at"],
            ]
            for r in self.device_rows
        ]
        settings_device_rows = [
            [
                r["id"],
                r["site_name"] or r["site_code"],
                r["pond_code"],
                r["device_code"],
                r["device_name"],
                r["device_type"],
                r["protocol_type"],
                r["connection_type"],
                r["config_status"],
                r["status"],
                r["last_collected_at"],
            ]
            for r in self.device_rows
        ]
        settings_device_tooltips = {
            (row_index, 8): row["config_hint"]
            for row_index, row in enumerate(self.device_rows)
        }
        factor_table_tooltips: dict[tuple[int, int], str] = {}
        for row_index, row in enumerate(self.device_rows):
            factor_table_tooltips[(row_index, 5)] = row.get("factor_summary", "")
            factor_table_tooltips[(row_index, 6)] = row["config_hint"]
        self._fill_table(self.device_table, device_rows, status_column=7)
        self._fill_table(self.settings_device_table, settings_device_rows, status_column=8, tooltips=settings_device_tooltips)
        self._fill_table(
            self.site_table,
            [[r["id"], r["site_code"], r["site_name"], r["contact_name"], r["contact_phone"]] for r in self.site_rows],
        )
        self._fill_table(
            self.serial_table,
            [
                [
                    profile.profile_name,
                    profile.port_name,
                    profile.baudrate,
                    profile.data_bits,
                    profile.parity,
                    profile.stop_bits,
                    profile.slave_address,
                    "是" if profile.is_default else "",
                ]
                for profile in self.serial_profiles
            ],
        )
        self._fill_table(
            self.acquisition_table,
            [
                [
                    profile.profile_name,
                    profile.protocol_type,
                    profile.connection_type,
                    profile.serial_profile_name,
                    profile.data_type,
                    profile.register_address,
                    profile.collect_timeout_seconds,
                    "是" if profile.is_default else "",
                ]
                for profile in self.acquisition_profiles
            ],
        )
        self._fill_table(
            self.factor_table,
            [
                [
                    r["device_code"],
                    r["device_name"],
                    r["device_type"],
                    r["protocol_type"],
                    r.get("factor_count", 0),
                    r.get("factor_summary", "未绑定因子"),
                    r["config_status"],
                    r["status"],
                ]
                for r in self.device_rows
            ],
            status_column=7,
            tooltips=factor_table_tooltips,
        )
        self._fill_table(
            self.latest_table,
            [[r["pond_code"], r["device_name"], r["metric_name"], f"{r['metric_value']} {r['metric_unit']}".strip(), r["quality"], r["collected_at"]] for r in self.service.fetch_latest_telemetry()],
            status_column=4,
        )
        self.alert_rows = self.service.fetch_recent_alerts()
        self._fill_table(
            self.alert_table,
            [[r["device_name"], r["alert_code"], r["alert_level"], r["status"], r["alert_message"], r["triggered_at"], r["recovered_at"]] for r in self.alert_rows],
            status_column=3,
        )
        upload_rows = self.service.fetch_upload_tasks()
        self._fill_table(
            self.upload_table,
            [[r["device_code"], r["command_code"], r["data_time"], r["status"], r["result_text"], r["created_at"]] for r in upload_rows],
            status_column=3,
            tooltips={
                (row_index, 4): row["packet_preview"]
                for row_index, row in enumerate(upload_rows)
                if row.get("packet_preview")
            },
        )
        self._refresh_analysis_view()
        if self.page_stack.currentIndex() == 2:
            self.run_query()
        self._update_platform_runtime_view()
        pending_config_count = sum(1 for row in self.device_rows if row.get("config_status") != "已完成")
        self.statusBar().showMessage(
            f"数据刷新完成：共 {len(self.device_rows)} 台设备，待完善 {pending_config_count} 台",
            4000,
        )

    def _format_analysis_value(self, value: float | None, unit: str = "") -> str:
        if value is None:
            return ""
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return f"{text} {unit}".strip()

    def _analysis_status_text(self, status: str) -> str:
        return {
            "good": "正常",
            "warning": "需关注",
            "unknown": "暂无数据",
        }.get(status, status)

    def _refresh_home_trend_view(self) -> None:
        focus_order = ["w01010", "w01014", "w01001", "w01019", "w01003"]
        metric_map = {row.metric_code: row for row in self.analysis_summary.metrics}
        rows = []
        for code in focus_order:
            row = metric_map.get(code)
            if row is None:
                continue
            rows.append(
                [
                    row.metric_name,
                    self._format_analysis_value(row.latest_value, row.metric_unit) or "暂无",
                    row.sparkline,
                    row.trend,
                    self._analysis_status_text(row.status),
                    row.latest_time or "暂无",
                ]
            )
        self._fill_table(self.home_trend_table, rows, status_column=4)

    def _refresh_analysis_view(self) -> None:
        summary = self.analysis_summary
        warning_rows = [row for row in summary.metrics if row.status == "warning"]
        if warning_rows:
            lines = [
                f"{row.metric_name}：最新 {self._format_analysis_value(row.latest_value, row.metric_unit)}，状态 {self._analysis_status_text(row.status)}；{row.quality_tip}；建议：{row.advice}"
                for row in warning_rows
            ]
        else:
            lines = ["当前重点指标未发现超出建议区间的最新值，建议继续保持巡检、校准和趋势观察。"]
        self.analysis_advice_text.setPlainText(
            f"分析时间：{summary.generated_at}；时间范围：最近 {summary.window_hours} 小时。\n"
            "规则说明：本地页面仅提供超标、疑似离群、疑似恒值提示；阈值来自本项目地表水技术要求目录与可配置项，最终告警以平台为准。\n"
            + "\n".join(lines)
        )
        self._fill_table(
            self.analysis_table,
            [
                [
                    row.metric_code,
                    row.metric_name,
                    self._format_analysis_value(row.latest_value, row.metric_unit),
                    row.sparkline,
                    self._format_analysis_value(row.avg_value, row.metric_unit),
                    self._format_analysis_value(row.min_value, row.metric_unit),
                    self._format_analysis_value(row.max_value, row.metric_unit),
                    row.sample_count,
                    row.trend,
                    self._analysis_status_text(row.status),
                    row.quality_tip,
                    row.latest_time,
                ]
                for row in summary.metrics
            ],
            status_column=9,
        )
        self._fill_table(
            self.analysis_threshold_table,
            [
                [
                    code,
                    "" if threshold.lower is None else threshold.lower,
                    "" if threshold.upper is None else threshold.upper,
                    threshold.source,
                    threshold.advice,
                ]
                for code, threshold in sorted(summary.thresholds.items())
            ],
        )

    def _fill_table(
        self,
        table: QTableWidget,
        rows: list[list[object]],
        status_column: int | None = None,
        tooltips: dict[tuple[int, int], str] | None = None,
    ) -> None:
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if status_column is not None and column_index == status_column:
                    self._apply_status_style(item, str(value))
                if tooltips and (row_index, column_index) in tooltips:
                    item.setToolTip(tooltips[(row_index, column_index)])
                table.setItem(row_index, column_index, item)
        table.resizeColumnsToContents()

    def _apply_status_style(self, item: QTableWidgetItem, status: str) -> None:
        colors = {
            "online": "#2b8a3e",
            "offline": "#c92a2a",
            "stale": "#e67700",
            "no_data": "#868e96",
            "active": "#c92a2a",
            "acknowledged": "#1971c2",
            "recovered": "#2b8a3e",
            "pending": "#e67700",
            "failed": "#c92a2a",
            "skipped": "#868e96",
            "uploaded": "#1c7ed6",
            "warning": "#e67700",
            "critical": "#c92a2a",
            "good": "#2b8a3e",
            "正常": "#2b8a3e",
            "需关注": "#e67700",
            "暂无数据": "#868e96",
        }
        item.setForeground(QColor(colors.get(status, colors.get(status.lower(), "#243b53"))))


def run() -> None:
    app = QApplication(sys.argv)
    splash_pixmap = QPixmap(560, 150)
    splash_pixmap.fill(QColor("#f4f7fb"))
    splash = QSplashScreen(splash_pixmap)
    splash.showMessage(
        "正在初始化数据库和服务，请稍候...",
        Qt.AlignCenter,
        QColor("#102a43"),
    )
    splash.show()
    app.processEvents()
    window = MainWindow()
    window.show()
    splash.finish(window)
    sys.exit(app.exec())

