from __future__ import annotations

import sys
from typing import Any, Dict, List

from PyQt6 import QtCore, QtWidgets

from api_client import ApiClient


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CopyTrade Desktop")
        self.resize(1200, 800)

        self.client = ApiClient("https://localhost:8000", verify_tls=True)

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        layout.addWidget(self._build_connection_bar())
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        self.signals_tab = self._build_signals_tab()
        self.orders_tab = self._build_orders_tab()
        self.tabs.addTab(self.signals_tab, "Signals")
        self.tabs.addTab(self.orders_tab, "Child Orders")

        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_connection_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QtWidgets.QLabel("API Base URL:"))
        self.base_url_input = QtWidgets.QLineEdit("https://localhost:8000")
        layout.addWidget(self.base_url_input, stretch=1)

        self.verify_tls_checkbox = QtWidgets.QCheckBox("Verify TLS")
        self.verify_tls_checkbox.setChecked(True)
        layout.addWidget(self.verify_tls_checkbox)

        self.apply_conn_button = QtWidgets.QPushButton("Apply")
        self.apply_conn_button.clicked.connect(self._apply_connection_settings)
        layout.addWidget(self.apply_conn_button)

        self.ping_button = QtWidgets.QPushButton("Ping")
        self.ping_button.clicked.connect(self._ping_api)
        layout.addWidget(self.ping_button)

        return bar

    def _build_signals_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        form_group = QtWidgets.QGroupBox("Generate Signal")
        form_layout = QtWidgets.QGridLayout(form_group)

        self.signal_strategy_id = QtWidgets.QLineEdit()
        self.signal_instrument_id = QtWidgets.QLineEdit()
        self.signal_trading_symbol = QtWidgets.QLineEdit()
        self.signal_side = QtWidgets.QComboBox()
        self.signal_side.addItems(["buy", "sell"])
        self.signal_quantity = QtWidgets.QLineEdit()
        self.signal_price = QtWidgets.QLineEdit()
        self.signal_meta = QtWidgets.QPlainTextEdit()
        self.signal_meta.setPlaceholderText("Optional JSON or notes")

        form_layout.addWidget(QtWidgets.QLabel("Strategy ID"), 0, 0)
        form_layout.addWidget(self.signal_strategy_id, 0, 1)
        form_layout.addWidget(QtWidgets.QLabel("Instrument ID"), 0, 2)
        form_layout.addWidget(self.signal_instrument_id, 0, 3)

        form_layout.addWidget(QtWidgets.QLabel("Trading Symbol"), 1, 0)
        form_layout.addWidget(self.signal_trading_symbol, 1, 1)
        form_layout.addWidget(QtWidgets.QLabel("Side"), 1, 2)
        form_layout.addWidget(self.signal_side, 1, 3)

        form_layout.addWidget(QtWidgets.QLabel("Quantity"), 2, 0)
        form_layout.addWidget(self.signal_quantity, 2, 1)
        form_layout.addWidget(QtWidgets.QLabel("Price"), 2, 2)
        form_layout.addWidget(self.signal_price, 2, 3)

        form_layout.addWidget(QtWidgets.QLabel("Meta Data"), 3, 0)
        form_layout.addWidget(self.signal_meta, 3, 1, 1, 3)

        self.create_signal_button = QtWidgets.QPushButton("Submit Signal")
        self.create_signal_button.clicked.connect(self._create_signal)
        form_layout.addWidget(self.create_signal_button, 4, 3)

        layout.addWidget(form_group)

        list_group = QtWidgets.QGroupBox("Signals")
        list_layout = QtWidgets.QVBoxLayout(list_group)
        toolbar = QtWidgets.QHBoxLayout()
        self.refresh_signals_button = QtWidgets.QPushButton("Refresh Signals")
        self.refresh_signals_button.clicked.connect(self._load_signals)
        toolbar.addWidget(self.refresh_signals_button)

        self.signal_id_for_orders = QtWidgets.QLineEdit()
        self.signal_id_for_orders.setPlaceholderText("Signal ID for child orders")
        toolbar.addWidget(self.signal_id_for_orders)
        self.load_orders_for_signal_button = QtWidgets.QPushButton("Load Orders")
        self.load_orders_for_signal_button.clicked.connect(self._load_orders_for_signal)
        toolbar.addWidget(self.load_orders_for_signal_button)
        toolbar.addStretch(1)
        list_layout.addLayout(toolbar)

        self.signals_table = QtWidgets.QTableWidget()
        self.signals_table.setColumnCount(0)
        self.signals_table.setRowCount(0)
        self.signals_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.signals_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.signals_table.doubleClicked.connect(self._select_signal_from_table)
        list_layout.addWidget(self.signals_table)

        layout.addWidget(list_group, stretch=1)
        return tab

    def _build_orders_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        filters_group = QtWidgets.QGroupBox("Filter Child Orders")
        filters_layout = QtWidgets.QGridLayout(filters_group)
        self.orders_signal_id = QtWidgets.QLineEdit()
        self.orders_parent_tag = QtWidgets.QLineEdit()
        self.orders_status = QtWidgets.QLineEdit()
        filters_layout.addWidget(QtWidgets.QLabel("Signal ID"), 0, 0)
        filters_layout.addWidget(self.orders_signal_id, 0, 1)
        filters_layout.addWidget(QtWidgets.QLabel("Parent Tag"), 0, 2)
        filters_layout.addWidget(self.orders_parent_tag, 0, 3)
        filters_layout.addWidget(QtWidgets.QLabel("Status"), 0, 4)
        filters_layout.addWidget(self.orders_status, 0, 5)
        self.refresh_orders_button = QtWidgets.QPushButton("Refresh Child Orders")
        self.refresh_orders_button.clicked.connect(self._load_child_orders)
        filters_layout.addWidget(self.refresh_orders_button, 0, 6)
        layout.addWidget(filters_group)

        self.orders_table = QtWidgets.QTableWidget()
        self.orders_table.setColumnCount(0)
        self.orders_table.setRowCount(0)
        self.orders_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.orders_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.orders_table.doubleClicked.connect(self._select_order_from_table)
        layout.addWidget(self.orders_table, stretch=1)

        update_group = QtWidgets.QGroupBox("Update Order Status")
        update_layout = QtWidgets.QGridLayout(update_group)
        self.update_order_id = QtWidgets.QLineEdit()
        self.update_status = QtWidgets.QComboBox()
        self.update_status.addItems(["", "pending", "completed", "failed"])
        self.update_filled_qty = QtWidgets.QLineEdit()
        self.update_avg_price = QtWidgets.QLineEdit()
        self.update_broker_order_id = QtWidgets.QLineEdit()
        self.update_error_code = QtWidgets.QLineEdit()
        self.update_error_message = QtWidgets.QLineEdit()

        update_layout.addWidget(QtWidgets.QLabel("Order ID"), 0, 0)
        update_layout.addWidget(self.update_order_id, 0, 1)
        update_layout.addWidget(QtWidgets.QLabel("Status"), 0, 2)
        update_layout.addWidget(self.update_status, 0, 3)
        update_layout.addWidget(QtWidgets.QLabel("Filled Qty"), 0, 4)
        update_layout.addWidget(self.update_filled_qty, 0, 5)

        update_layout.addWidget(QtWidgets.QLabel("Avg Price"), 1, 0)
        update_layout.addWidget(self.update_avg_price, 1, 1)
        update_layout.addWidget(QtWidgets.QLabel("Broker Order ID"), 1, 2)
        update_layout.addWidget(self.update_broker_order_id, 1, 3)
        update_layout.addWidget(QtWidgets.QLabel("Error Code"), 1, 4)
        update_layout.addWidget(self.update_error_code, 1, 5)

        update_layout.addWidget(QtWidgets.QLabel("Error Message"), 2, 0)
        update_layout.addWidget(self.update_error_message, 2, 1, 1, 3)

        self.update_order_button = QtWidgets.QPushButton("Update Status")
        self.update_order_button.clicked.connect(self._update_order_status)
        update_layout.addWidget(self.update_order_button, 2, 5)

        layout.addWidget(update_group)
        return tab

    def _apply_connection_settings(self) -> None:
        base_url = self.base_url_input.text().strip()
        if not base_url:
            self._set_status("Base URL is required.")
            return
        self.client = ApiClient(
            base_url=base_url, verify_tls=self.verify_tls_checkbox.isChecked()
        )
        self._set_status("Connection settings applied.")

    def _ping_api(self) -> None:
        try:
            response = self.client.get("/signals/")
            self._set_status(response.get("message", "Ping ok"))
        except Exception as exc:
            self._set_status(f"Ping failed: {exc}")

    def _create_signal(self) -> None:
        try:
            payload = {
                "strategy_id": int(self.signal_strategy_id.text().strip()),
                "instrument_id": self.signal_instrument_id.text().strip(),
                "trading_symbol": self.signal_trading_symbol.text().strip(),
                "side": self.signal_side.currentText(),
                "quantity": int(self.signal_quantity.text().strip()),
                "price": float(self.signal_price.text().strip()),
            }
            meta = self.signal_meta.toPlainText().strip()
            if meta:
                payload["meta_data"] = meta
            response = self.client.post("/signals/", payload)
            self._set_status(response.get("message", "Signal submitted."))
            self._load_signals()
        except Exception as exc:
            self._set_status(f"Create signal failed: {exc}")

    def _load_signals(self) -> None:
        try:
            response = self.client.get("/signals/")
            items = response.get("data") or []
            self._populate_table(self.signals_table, items)
            self._set_status(response.get("message", "Signals loaded."))
        except Exception as exc:
            self._set_status(f"Load signals failed: {exc}")

    def _load_orders_for_signal(self) -> None:
        signal_id = self.signal_id_for_orders.text().strip()
        if not signal_id:
            self._set_status("Signal ID is required.")
            return
        try:
            response = self.client.get(f"/signals/{int(signal_id)}/orders")
            items = response.get("data") or []
            self._populate_table(self.orders_table, items)
            self._set_status(response.get("message", "Orders loaded."))
            self.tabs.setCurrentWidget(self.orders_tab)
        except Exception as exc:
            self._set_status(f"Load orders failed: {exc}")

    def _load_child_orders(self) -> None:
        params: Dict[str, Any] = {}
        if self.orders_signal_id.text().strip():
            params["signal_id"] = int(self.orders_signal_id.text().strip())
        if self.orders_parent_tag.text().strip():
            params["parent_tag"] = self.orders_parent_tag.text().strip()
        if self.orders_status.text().strip():
            params["status"] = self.orders_status.text().strip()
        try:
            response = self.client.get("/orders/children", params=params)
            items = response.get("data") or []
            self._populate_table(self.orders_table, items)
            self._set_status(response.get("message", "Child orders loaded."))
        except Exception as exc:
            self._set_status(f"Load child orders failed: {exc}")

    def _update_order_status(self) -> None:
        order_id = self.update_order_id.text().strip()
        if not order_id:
            self._set_status("Order ID is required.")
            return
        payload: Dict[str, Any] = {}
        status_value = self.update_status.currentText().strip()
        if status_value:
            payload["status"] = status_value
        if self.update_filled_qty.text().strip():
            payload["filled_quantity"] = int(self.update_filled_qty.text().strip())
        if self.update_avg_price.text().strip():
            payload["average_price"] = float(self.update_avg_price.text().strip())
        if self.update_broker_order_id.text().strip():
            payload["broker_order_id"] = self.update_broker_order_id.text().strip()
        if self.update_error_code.text().strip():
            payload["error_code"] = self.update_error_code.text().strip()
        if self.update_error_message.text().strip():
            payload["error_message"] = self.update_error_message.text().strip()

        try:
            response = self.client.put(f"/orders/{int(order_id)}/status", payload)
            self._set_status(response.get("message", "Order updated."))
            self._load_child_orders()
        except Exception as exc:
            self._set_status(f"Update order failed: {exc}")

    def _populate_table(self, table: QtWidgets.QTableWidget, items: List[Dict[str, Any]]) -> None:
        table.clear()
        if not items:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        headers = list(items[0].keys())
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            for col_idx, key in enumerate(headers):
                value = item.get(key)
                cell = QtWidgets.QTableWidgetItem(str(value))
                table.setItem(row_idx, col_idx, cell)
        table.resizeColumnsToContents()

    def _select_signal_from_table(self) -> None:
        row = self.signals_table.currentRow()
        if row < 0:
            return
        signal_id_item = self.signals_table.item(row, 0)
        if not signal_id_item:
            return
        self.signal_id_for_orders.setText(signal_id_item.text())

    def _select_order_from_table(self) -> None:
        row = self.orders_table.currentRow()
        if row < 0:
            return
        order_id_item = self.orders_table.item(row, 0)
        if not order_id_item:
            return
        self.update_order_id.setText(order_id_item.text())

    def _set_status(self, message: str) -> None:
        self.status_bar.showMessage(message, 8000)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
