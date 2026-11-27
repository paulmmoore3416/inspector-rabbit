"""
Inspector Rabbit - Network Diagnostics Widget
Ping, traceroute, port scanning, banner grabbing, and rDNS.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.netdiag import NetDiagThread, PORT_NAMES
from .components import apply_page_header_style

ACCENT = "#f97316"

TERM_COLORS = {
    "info":    "#58a6ff",
    "success": "#3fb950",
    "error":   "#f85149",
    "warn":    "#e3b341",
    "data":    "#e6edf3",
}


class NetDiagWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._result = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        topbar = self._build_topbar()
        layout.addWidget(topbar)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        layout.addLayout(content, 1)

        content.addWidget(self._build_left_panel())
        content.addWidget(self._build_right_panel(), 1)

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        apply_page_header_style(bar, ACCENT)
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        bl.setSpacing(16)

        icon = QLabel("🔌")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(0)
        t1 = QLabel("Network Diagnostics")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Ping · Traceroute · Port Scan · Banner Grab · rDNS")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        return bar

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)

        self._sec("TARGET", layout)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("IP address or hostname")
        self.target_input.setFixedHeight(42)
        self.target_input.setFont(QFont("Ubuntu", 12))
        self.target_input.returnPressed.connect(self._start_diag)
        layout.addWidget(self.target_input)

        self.run_btn = QPushButton("🔌  Run Diagnostics")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setFixedHeight(42)
        self.run_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.run_btn.clicked.connect(self._start_diag)
        layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⛔  Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_diag)
        layout.addWidget(self.stop_btn)

        layout.addWidget(self._sep())
        self._sec("TESTS", layout)

        self.cb_ping = QCheckBox("Ping")
        self.cb_ping.setChecked(True)
        self.cb_traceroute = QCheckBox("Traceroute")
        self.cb_traceroute.setChecked(True)
        self.cb_portscan = QCheckBox("Port Scan")
        self.cb_portscan.setChecked(True)
        self.cb_banner = QCheckBox("Banner Grab")
        self.cb_banner.setChecked(True)
        self.cb_rdns = QCheckBox("rDNS")
        self.cb_rdns.setChecked(True)

        for cb in (self.cb_ping, self.cb_traceroute, self.cb_portscan, self.cb_banner, self.cb_rdns):
            cb.setStyleSheet("color: #e6edf3; font-size: 12px;")
            layout.addWidget(cb)

        layout.addWidget(self._sep())
        self._sec("RESULTS SUMMARY", layout)

        self.rtt_lbl = self._stat_row("Avg RTT:", "—", layout)
        self.loss_lbl = self._stat_row("Packet loss:", "—", layout)
        self.ports_lbl = self._stat_row("Open ports:", "—", layout)
        self.hostname_lbl = self._stat_row("Hostname:", "—", layout)

        layout.addWidget(self._sep())
        self._sec("STATUS LOG", layout)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setFont(QFont("Ubuntu Mono", 10))
        self.status_log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: #3fb950;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        self.status_log.setMinimumHeight(100)
        layout.addWidget(self.status_log)

        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #0d1117;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Terminal output
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Ubuntu Mono", 10))
        self.terminal.setStyleSheet(
            "background: #030810; color: #3fb950; border: 1px solid #21262d;"
        )
        layout.addWidget(self.terminal, 1)

        # Ports table
        self.ports_table = self._make_ports_table()
        self.ports_table.setFixedHeight(200)
        layout.addWidget(self.ports_table)

        return panel

    def _make_ports_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(3)
        t.setHorizontalHeaderLabels(["Port", "Protocol", "Banner"])
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setFont(QFont("Ubuntu Mono", 10))
        t.setColumnWidth(0, 70)
        t.setColumnWidth(1, 120)
        t.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                border: 1px solid #21262d;
                color: #e6edf3;
                gridline-color: #21262d;
            }
            QHeaderView::section {
                background: #010409;
                color: #8b949e;
                border: none;
                border-bottom: 1px solid #21262d;
                padding: 4px;
            }
        """)
        return t

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _stat_row(self, label: str, value: str, layout) -> QLabel:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        lbl.setFixedWidth(90)
        val = QLabel(value)
        val.setFont(QFont("Ubuntu Mono", 10))
        val.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
        row.addWidget(lbl)
        row.addWidget(val, 1)
        layout.addLayout(row)
        return val

    def _sec(self, text: str, layout):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(lbl)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _term_append(self, text: str, kind: str = "info"):
        color = TERM_COLORS.get(kind, TERM_COLORS["data"])
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.terminal.append(f'<span style="color:{color};">{safe}</span>')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_diag(self):
        target = self.target_input.text().strip()
        if not target:
            self.status_log.append("Enter a target IP or hostname.")
            return

        tests = []
        if self.cb_ping.isChecked():
            tests.append("ping")
        if self.cb_traceroute.isChecked():
            tests.append("traceroute")
        if self.cb_portscan.isChecked():
            tests.append("portscan")
        if self.cb_banner.isChecked():
            tests.append("banner")
        if self.cb_rdns.isChecked():
            tests.append("rdns")

        if not tests:
            self.status_log.append("Select at least one test.")
            return

        self.terminal.clear()
        self.ports_table.setRowCount(0)
        self.status_log.clear()
        self.status_log.append(f"Starting diagnostics: {target}")
        self._term_append(f"=== Network Diagnostics: {target} ===", "info")

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.rtt_lbl.setText("...")
        self.loss_lbl.setText("...")
        self.ports_lbl.setText("...")
        self.hostname_lbl.setText("...")

        self._thread = NetDiagThread(target, tests)
        self._thread.line_output.connect(self._on_line)
        self._thread.result_ready.connect(self._on_result)
        self._thread.done.connect(self._on_done)
        self._thread.start()

        self.status_message.emit(f"Running diagnostics for: {target}")

    def _stop_diag(self):
        if self._thread and self._thread.isRunning():
            self._thread.terminate()
            self._term_append("Stopped by user.", "warn")
            self.status_log.append("Stopped.")
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_line(self, text: str, kind: str):
        self._term_append(text, kind)
        self.status_log.append(text)

    def _on_result(self, result: dict):
        self._result = result

        # Update summary labels
        rtt = result.get("ping_ms")
        self.rtt_lbl.setText(f"{rtt} ms" if rtt is not None else "N/A")

        loss = result.get("packet_loss")
        self.loss_lbl.setText(f"{loss}%" if loss is not None else "N/A")

        open_ports = result.get("open_ports", [])
        self.ports_lbl.setText(str(len(open_ports)))

        hostname = result.get("hostname", "") or result.get("ip", "")
        self.hostname_lbl.setText(hostname[:30] if hostname else "N/A")

        # Populate ports table
        banners = result.get("banners", {})
        for port in open_ports:
            row = self.ports_table.rowCount()
            self.ports_table.insertRow(row)

            port_item = QTableWidgetItem(str(port))
            port_item.setForeground(QColor(ACCENT))
            port_item.setFont(QFont("Ubuntu Mono", 10, QFont.Weight.Bold))
            self.ports_table.setItem(row, 0, port_item)

            proto_item = QTableWidgetItem(PORT_NAMES.get(port, "?"))
            proto_item.setForeground(QColor("#3fb950"))
            self.ports_table.setItem(row, 1, proto_item)

            banner = banners.get(port, "")
            banner_item = QTableWidgetItem(banner[:120] if banner else "")
            banner_item.setForeground(QColor("#8b949e"))
            self.ports_table.setItem(row, 2, banner_item)

    def _on_done(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._term_append("=== Diagnostics finished ===", "success")
        self.status_log.append("Done.")
        target = self.target_input.text().strip()
        self.status_message.emit(f"Diagnostics complete: {target}")

    def apply_settings(self, settings: dict):
        pass
