"""
Inspector Rabbit - Counter Surveillance Monitor
Split-screen defensive intelligence widget.

Left  : Terminal-style live scan activity log (what IR is doing)
Right : Threat detection panel (who is watching / attacking back)
Bottom: Real-time metrics graphs — traffic I/O + detected scan attempts
"""

import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QTabWidget, QApplication, QMessageBox, QSizePolicy,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor

# Matplotlib embedded in Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib

from ..modules.connection_guard import ConnectionGuard
from ..modules.traffic_monitor import TrafficMonitor
from ..modules.scan_detector import ScanDetector, ScanEvent
from ..modules.dns_leak_monitor import DNSLeakMonitor
from .components import apply_page_header_style


SEV_COLOR = {
    'high':   '#f85149',
    'medium': '#ffa657',
    'low':    '#3fb950',
    'info':   '#58a6ff',
}
SEV_ICON = {
    'high':   '🔴',
    'medium': '🟡',
    'low':    '🟢',
    'info':   '🔵',
}

TERM_COLORS = {
    'info':    '#3fb950',   # green
    'warn':    '#ffa657',   # amber
    'threat':  '#f85149',   # red
    'action':  '#00f5ff',   # cyan
    'muted':   '#484f58',   # grey
}


class TerminalLog(QTextEdit):
    """Dark green-on-black terminal-style log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Ubuntu Mono", 10))
        self.setStyleSheet("""
            QTextEdit {
                background: #010409;
                color: #3fb950;
                border: none;
                border-radius: 0px;
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 11px;
                selection-background-color: #21262d;
            }
        """)
        self._max_lines = 1000

    def append_line(self, text: str, kind: str = 'info'):
        color = TERM_COLORS.get(kind, TERM_COLORS['info'])
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        html = (
            f'<span style="color:#484f58;">[{ts}]</span> '
            f'<span style="color:{color};">{text}</span><br/>'
        )
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertHtml(html)
        self.moveCursor(QTextCursor.MoveOperation.End)

        # Trim old lines
        doc = self.document()
        while doc.lineCount() > self._max_lines:
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()


class MetricsGraph(FigureCanvas):
    """Embedded matplotlib graph for traffic + scan metrics."""

    def __init__(self, title: str, y_label: str, color_in: str, color_out: str,
                 parent=None):
        self._fig = Figure(figsize=(5, 2.2), dpi=90, facecolor='#010409')
        super().__init__(self._fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor('#0d1117')
        self._ax.tick_params(colors='#484f58', labelsize=7)
        self._ax.spines[:].set_color('#21262d')
        self._ax.set_title(title, color='#8b949e', fontsize=9, pad=4)
        self._ax.set_ylabel(y_label, color='#484f58', fontsize=7)
        self._ax.yaxis.label.set_color('#484f58')

        self._color_in  = color_in
        self._color_out = color_out
        self._xs:  list = []
        self._ys1: list = []   # in / series 1
        self._ys2: list = []   # out / series 2
        self._label1 = 'In'
        self._label2 = 'Out'
        self._fig.tight_layout(pad=0.8)

    def update_data(self, xs: list, ys1: list, ys2: list,
                    label1='In', label2='Out'):
        self._xs = xs[-60:]
        self._ys1 = ys1[-60:]
        self._ys2 = ys2[-60:]
        self._label1 = label1
        self._label2 = label2
        self._redraw()

    def _redraw(self):
        self._ax.cla()
        self._ax.set_facecolor('#0d1117')
        self._ax.tick_params(colors='#484f58', labelsize=7)
        self._ax.spines[:].set_color('#21262d')

        x_range = range(len(self._ys1))
        if self._ys1:
            self._ax.fill_between(
                x_range, self._ys1,
                color=self._color_in, alpha=0.25, linewidth=0
            )
            self._ax.plot(
                x_range, self._ys1,
                color=self._color_in, linewidth=1.2, label=self._label1
            )
        if self._ys2:
            self._ax.fill_between(
                x_range, self._ys2,
                color=self._color_out, alpha=0.18, linewidth=0
            )
            self._ax.plot(
                x_range, self._ys2,
                color=self._color_out, linewidth=1.2,
                linestyle='--', label=self._label2
            )

        self._ax.legend(
            loc='upper left', fontsize=7,
            facecolor='#0d1117', edgecolor='#21262d', labelcolor='#8b949e'
        )
        self._ax.set_xlim(0, max(60, len(self._ys1)))
        self._ax.set_xticks([])
        self._fig.tight_layout(pad=0.6)
        self.draw()


class CounterSurveillanceWidget(QWidget):
    """
    🛡️ Counter Surveillance Monitor — Split-screen defensive intelligence.

    Left  : Terminal — real-time scan activity log (what IR is doing)
    Right : Threat panel — attackers, watchers, suspicious connections
    Bottom: Live metrics graphs
    """

    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._guard:   Optional[ConnectionGuard] = None
        self._traffic: Optional[TrafficMonitor]  = None
        self._scanner: Optional[ScanDetector]    = None
        self._dns:     Optional[DNSLeakMonitor]  = None
        self._monitoring = False
        self._conn_rows: dict = {}   # key -> table row index
        self._setup_ui()

    # ── UI Construction ────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_status_bar())

        # Main splitter: terminal | threat panel
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.setStyleSheet(
            "QSplitter::handle { background: #21262d; width: 3px; }"
        )
        main_split.addWidget(self._build_terminal_panel())
        main_split.addWidget(self._build_threat_panel())
        main_split.setSizes([560, 640])

        # Vertical outer splitter: main_split | metrics
        outer_split = QSplitter(Qt.Orientation.Vertical)
        outer_split.setStyleSheet(
            "QSplitter::handle { background: #21262d; height: 3px; }"
        )
        outer_split.addWidget(main_split)
        outer_split.addWidget(self._build_metrics_panel())
        outer_split.setSizes([520, 240])

        root.addWidget(outer_split, 1)

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        apply_page_header_style(bar, "#f85149")
        bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(12)

        icon = QLabel("🛡️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border:none; background:transparent;")
        lay.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Counter Surveillance Monitor")
        t1.setFont(QFont("Ubuntu", 14, QFont.Weight.Bold))
        t1.setStyleSheet("color:#e6edf3; border:none; background:transparent;")
        t2 = QLabel(
            "Connection Guard · Traffic Monitor · Scan Detector · DNS Leak Monitor"
        )
        t2.setStyleSheet(
            "color:#8b949e; font-size:10px; border:none; background:transparent;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        lay.addLayout(vl)
        lay.addStretch()

        self.start_btn = QPushButton("▶  Start Monitoring")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(36)
        self.start_btn.setFixedWidth(160)
        self.start_btn.clicked.connect(self._toggle_monitoring)
        lay.addWidget(self.start_btn)

        self.kill_btn = QPushButton("⚡  Kill Connection")
        self.kill_btn.setFixedHeight(36)
        self.kill_btn.setFixedWidth(140)
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background: #f8514918; border: 1px solid #f8514955;
                color: #f85149; border-radius: 8px; font-weight:700;
            }
            QPushButton:hover { background: #f8514930; border-color: #f85149; }
            QPushButton:pressed { background: #f8514950; }
        """)
        self.kill_btn.clicked.connect(self._kill_selected)
        lay.addWidget(self.kill_btn)

        clr_btn = QPushButton("🗑 Clear")
        clr_btn.setFixedHeight(36)
        clr_btn.setFixedWidth(80)
        clr_btn.clicked.connect(self._clear_all)
        lay.addWidget(clr_btn)

        return bar

    def _build_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            "QFrame { background: #0d1117; border-bottom: 1px solid #21262d; }"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 4, 20, 4)
        lay.setSpacing(24)

        self._stat_status = self._stat_label("⬛  IDLE", "#484f58")
        self._stat_conns  = self._stat_label("Connections: 0", "#484f58")
        self._stat_threats = self._stat_label("Threats: 0", "#484f58")
        self._stat_scanners = self._stat_label("Scanners: 0", "#484f58")
        self._stat_dns     = self._stat_label("DNS: OK", "#3fb950")

        for w in [self._stat_status, self._stat_conns,
                  self._stat_threats, self._stat_scanners, self._stat_dns]:
            lay.addWidget(w)
        lay.addStretch()

        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet(
            "color: #f85149; font-size: 11px; font-weight: 700;"
        )
        lay.addWidget(self.alert_label)
        return bar

    @staticmethod
    def _stat_label(text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Ubuntu Mono", 9))
        lbl.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        return lbl

    # ── Left: Terminal panel ───────────────────────────────────────────────

    def _build_terminal_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #010409;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(
            "QFrame { background:#0d1117; border-bottom:1px solid #21262d; }"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 4, 12, 4)
        title = QLabel("◼  SCAN ACTIVITY LOG")
        title.setFont(QFont("Ubuntu Mono", 9, QFont.Weight.Bold))
        title.setStyleSheet("color:#3fb950; border:none; background:transparent;")
        hl.addWidget(title)
        hl.addStretch()
        dot_r = QLabel("●"); dot_r.setStyleSheet("color:#f85149; border:none; background:transparent;")
        dot_y = QLabel("●"); dot_y.setStyleSheet("color:#ffa657; border:none; background:transparent;")
        dot_g = QLabel("●"); dot_g.setStyleSheet("color:#3fb950; border:none; background:transparent;")
        for d in [dot_r, dot_y, dot_g]:
            hl.addWidget(d)
        lay.addWidget(hdr)

        self.terminal = TerminalLog()
        lay.addWidget(self.terminal, 1)

        # Boot message
        self.terminal.append_line(
            "Inspector Rabbit Counter Surveillance v1.2.0", 'action'
        )
        self.terminal.append_line(
            "4 defensive modules loaded — press ▶ Start Monitoring", 'muted'
        )
        self.terminal.append_line(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'muted'
        )
        return panel

    # ── Right: Threat panel ────────────────────────────────────────────────

    def _build_threat_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #010409;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.threat_tabs = QTabWidget()
        self.threat_tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#010409; }
            QTabBar::tab {
                background:#0d1117; color:#8b949e;
                padding:6px 14px; border:none;
                border-bottom: 2px solid transparent;
                font-size:10px;
            }
            QTabBar::tab:selected { color:#00f5ff; border-bottom:2px solid #00f5ff; }
        """)
        lay.addWidget(self.threat_tabs)

        # Tab 1: Threat events
        self.threat_table = self._make_table(
            ["Time", "Severity", "Type", "Source IP", "Detail"]
        )
        self.threat_table.setColumnWidth(0, 72)
        self.threat_table.setColumnWidth(1, 64)
        self.threat_table.setColumnWidth(2, 120)
        self.threat_table.setColumnWidth(3, 110)
        self.threat_tabs.addTab(self.threat_table, "⚠️ Threats (0)")

        # Tab 2: Active connections
        conn_widget = QWidget()
        conn_lay = QVBoxLayout(conn_widget)
        conn_lay.setContentsMargins(0, 0, 0, 0)
        conn_lay.setSpacing(4)

        self.conn_table = self._make_table(
            ["Time", "Process", "Local", "Remote", "Status", "Risk"]
        )
        self.conn_table.setColumnWidth(0, 72)
        self.conn_table.setColumnWidth(1, 90)
        self.conn_table.setColumnWidth(2, 110)
        self.conn_table.setColumnWidth(3, 120)
        self.conn_table.setColumnWidth(4, 80)
        conn_lay.addWidget(self.conn_table, 1)

        kill_hint = QLabel("  Double-click a row or press ⚡ Kill Connection to terminate")
        kill_hint.setStyleSheet("color:#484f58; font-size:10px; padding:4px;")
        conn_lay.addWidget(kill_hint)
        self.conn_table.doubleClicked.connect(self._kill_from_table)
        self.threat_tabs.addTab(conn_widget, "🔌 Connections (0)")

        # Tab 3: Detected scanners
        self.scanner_table = self._make_table(
            ["First Seen", "IP", "Type", "Ports Probed", "Hits", "Severity"]
        )
        self.scanner_table.setColumnWidth(0, 72)
        self.scanner_table.setColumnWidth(1, 110)
        self.scanner_table.setColumnWidth(2, 110)
        self.threat_tabs.addTab(self.scanner_table, "🔭 Scanners (0)")

        # Tab 4: DNS checks
        self.dns_table = self._make_table(
            ["Time", "Host", "Resolved IP", "Expected", "Latency ms", "OK"]
        )
        self.dns_table.setColumnWidth(0, 72)
        self.dns_table.setColumnWidth(1, 120)
        self.dns_table.setColumnWidth(2, 110)
        self.dns_table.setColumnWidth(3, 90)
        self.dns_table.setColumnWidth(4, 80)
        self.threat_tabs.addTab(self.dns_table, "🔍 DNS Checks")

        return panel

    # ── Bottom: Metrics graphs ─────────────────────────────────────────────

    def _build_metrics_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            "background: #010409; border-top: 1px solid #21262d;"
        )
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Traffic graph
        traffic_frame = QFrame()
        traffic_frame.setStyleSheet(
            "QFrame { background:#0d1117; border:1px solid #21262d; border-radius:8px; }"
        )
        tfl = QVBoxLayout(traffic_frame)
        tfl.setContentsMargins(8, 4, 8, 4)
        tfl.setSpacing(2)
        tlbl = QLabel("📊  NETWORK TRAFFIC  (bytes/sec)")
        tlbl.setStyleSheet("color:#8b949e; font-size:9px; font-weight:700; border:none;")
        tfl.addWidget(tlbl)
        self.traffic_graph = MetricsGraph(
            '', 'B/s', '#00f5ff', '#f87171'
        )
        tfl.addWidget(self.traffic_graph, 1)
        lay.addWidget(traffic_frame, 1)

        # Scan attempts graph
        scan_frame = QFrame()
        scan_frame.setStyleSheet(
            "QFrame { background:#0d1117; border:1px solid #21262d; border-radius:8px; }"
        )
        sfl = QVBoxLayout(scan_frame)
        sfl.setContentsMargins(8, 4, 8, 4)
        sfl.setSpacing(2)
        slbl = QLabel("🔭  SCAN ATTEMPTS DETECTED AGAINST ME")
        slbl.setStyleSheet("color:#8b949e; font-size:9px; font-weight:700; border:none;")
        sfl.addWidget(slbl)
        self.scan_graph = MetricsGraph(
            '', 'events', '#f85149', '#ffa657'
        )
        sfl.addWidget(self.scan_graph, 1)
        lay.addWidget(scan_frame, 1)

        self._scan_history: list = []
        self._scan_ts: list = []
        self._scan_severity_high: list = []
        self._scan_severity_med: list = []

        return panel

    # ── Monitoring control ─────────────────────────────────────────────────

    def _toggle_monitoring(self):
        if self._monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        self._monitoring = True
        self.start_btn.setText("⏹  Stop Monitoring")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #f8514918; border: 1px solid #f8514944;
                color: #f85149; border-radius:8px; font-weight:700;
            }
            QPushButton:hover { background:#f8514930; }
        """)
        self._stat_status.setText("🟢  ACTIVE")
        self._stat_status.setStyleSheet("color:#3fb950; font-size:10px;")

        self.terminal.append_line("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'muted')
        self.terminal.append_line("▶  COUNTER SURVEILLANCE ACTIVE", 'action')

        # Start Connection Guard
        self._guard = ConnectionGuard()
        self._guard.new_connection.connect(self._on_new_connection)
        self._guard.connection_closed.connect(self._on_conn_closed)
        self._guard.threat_detected.connect(self._on_threat)
        self._guard.stats_update.connect(self._on_guard_stats)
        self._guard.log_event.connect(lambda m: self.terminal.append_line(m, 'info'))
        self._guard.start()

        # Start Traffic Monitor
        self._traffic = TrafficMonitor()
        self._traffic.sample_ready.connect(self._on_traffic_sample)
        self._traffic.anomaly.connect(lambda d: self._on_threat({**d, 'type': f"TRAFFIC_{d['direction']}"}))
        self._traffic.log_event.connect(lambda m: self.terminal.append_line(m, 'warn'))
        self._traffic.start()

        # Start Scan Detector
        self._scanner = ScanDetector()
        self._scanner.scan_detected.connect(self._on_scanner_detected)
        self._scanner.stats_update.connect(self._on_scanner_stats)
        self._scanner.log_event.connect(lambda m: self.terminal.append_line(m, 'threat'))
        self._scanner.start()

        # Start DNS Monitor
        self._dns = DNSLeakMonitor()
        self._dns.leak_detected.connect(self._on_threat)
        self._dns.resolver_changed.connect(self._on_resolver_changed)
        self._dns.dns_check_result.connect(self._on_dns_result)
        self._dns.log_event.connect(lambda m: self.terminal.append_line(m, 'warn'))
        self._dns.stats_update.connect(self._on_dns_stats)
        self._dns.start()

        self.status_message.emit("Counter Surveillance monitoring active")

    def _stop_monitoring(self):
        self._monitoring = False
        self.start_btn.setText("▶  Start Monitoring")
        self.start_btn.setStyleSheet("")
        self._stat_status.setText("⬛  IDLE")
        self._stat_status.setStyleSheet("color:#484f58; font-size:10px;")

        for mod in [self._guard, self._traffic, self._scanner, self._dns]:
            if mod and mod.isRunning():
                mod.quit()
                mod.wait(1500)

        self.terminal.append_line("⏹  Monitoring stopped", 'warn')
        self.status_message.emit("Counter Surveillance stopped")

    # ── Signal handlers ────────────────────────────────────────────────────

    def _on_new_connection(self, rec: dict):
        risk = rec.get('risk', 'low')
        kind = 'threat' if risk == 'high' else ('warn' if risk == 'medium' else 'info')
        direction = '← INBOUND' if rec.get('inbound') else '→'
        self.terminal.append_line(
            f"{direction}  {rec['process']}  {rec['laddr']}:{rec['lport']} "
            f"↔ {rec['raddr']}:{rec['rport']}  [{rec['status']}]  [{risk.upper()}]",
            kind
        )

        row = self.conn_table.rowCount()
        self.conn_table.insertRow(row)
        self._conn_rows[rec['key']] = row

        items = [
            rec['timestamp'], rec['process'],
            f"{rec['laddr']}:{rec['lport']}",
            f"{rec['raddr']}:{rec['rport']}",
            rec['status'], risk.upper()
        ]
        risk_color = {'high': '#f85149', 'medium': '#ffa657', 'low': '#3fb950'}.get(risk, '#8b949e')
        for col, val in enumerate(items):
            item = QTableWidgetItem(str(val))
            if col == 5:
                item.setForeground(QColor(risk_color))
                item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
            self.conn_table.setItem(row, col, item)

        # Store remote address for kill action
        self.conn_table.item(row, 3).setData(
            Qt.ItemDataRole.UserRole, (rec['raddr'], rec['rport'])
        )

        # Update tab label
        idx = self.threat_tabs.indexOf(self.conn_table.parent())
        if idx == -1:
            idx = 1
        self.threat_tabs.setTabText(idx, f"🔌 Connections ({self.conn_table.rowCount()})")

    def _on_conn_closed(self, key: str):
        if key in self._conn_rows:
            row = self._conn_rows[key]
            if row < self.conn_table.rowCount():
                for col in range(self.conn_table.columnCount()):
                    item = self.conn_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#30363d"))
            del self._conn_rows[key]

    def _on_threat(self, d: dict):
        sev = d.get('severity', 'medium')
        icon = SEV_ICON.get(sev, '●')
        color = QColor(SEV_COLOR.get(sev, '#8b949e'))

        row = self.threat_table.rowCount()
        self.threat_table.insertRow(row)

        vals = [
            d.get('timestamp', '—'),
            f"{icon} {sev.upper()}",
            d.get('type', '—').replace('_', ' '),
            d.get('ip', '—'),
            d.get('detail', '—'),
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(str(val))
            if col == 1:
                item.setForeground(color)
                item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
            elif col == 3:
                item.setForeground(QColor("#00f5ff"))
            self.threat_table.setItem(row, col, item)

        self.threat_table.scrollToBottom()

        # Update tab label
        self.threat_tabs.setTabText(0, f"⚠️ Threats ({self.threat_table.rowCount()})")

        # Flash alert bar for high severity
        if sev == 'high':
            self.alert_label.setText(
                f"🔴  {d.get('type','THREAT')} — {d.get('ip','?')}"
            )
            QTimer.singleShot(6000, lambda: self.alert_label.setText(""))
            self.terminal.append_line(
                f"⚠  THREAT: {d.get('type')} from {d.get('ip','?')} — {d.get('detail','')}",
                'threat'
            )

    def _on_scanner_detected(self, ev: ScanEvent):
        row = self.scanner_table.rowCount()
        self.scanner_table.insertRow(row)
        color = QColor(SEV_COLOR.get(ev.severity, '#8b949e'))

        vals = [
            ev.first_seen, ev.ip, ev.scan_type.replace('_', ' ').title(),
            str(sorted(ev.ports_probed)[:8]),
            str(ev.total_attempts),
            ev.severity.upper(),
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(val)
            if col in (1, 5):
                item.setForeground(color)
                if col == 5:
                    item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
            self.scanner_table.setItem(row, col, item)

        self.threat_tabs.setTabText(2, f"🔭 Scanners ({self.scanner_table.rowCount()})")

        # Update scan history for graph
        self._scan_ts.append(ev.first_seen)
        if ev.severity == 'high':
            self._scan_severity_high.append(
                (self._scan_severity_high[-1] if self._scan_severity_high else 0) + 1
            )
            self._scan_severity_med.append(
                self._scan_severity_med[-1] if self._scan_severity_med else 0
            )
        else:
            self._scan_severity_high.append(
                self._scan_severity_high[-1] if self._scan_severity_high else 0
            )
            self._scan_severity_med.append(
                (self._scan_severity_med[-1] if self._scan_severity_med else 0) + 1
            )
        self.scan_graph.update_data(
            self._scan_ts,
            self._scan_severity_high,
            self._scan_severity_med,
            label1='High', label2='Medium'
        )

    def _on_dns_result(self, d: dict):
        row = self.dns_table.rowCount()
        self.dns_table.insertRow(row)
        ok = d.get('ok', True)

        vals = [
            d.get('timestamp', '—'),
            d.get('host', '—'),
            d.get('resolved_ip', '—'),
            d.get('expected', 'any'),
            str(d.get('latency_ms', '—')),
            '✓' if ok else '✗',
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(val)
            if col == 5:
                item.setForeground(QColor('#3fb950' if ok else '#f85149'))
                item.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
            elif col == 4 and isinstance(d.get('latency_ms'), (int, float)):
                lat = d['latency_ms']
                item.setForeground(QColor('#f85149' if lat > 2000 else '#ffa657' if lat > 500 else '#3fb950'))
            self.dns_table.setItem(row, col, item)

        dns_ok = '✓ OK' if ok else '✗ FAIL'
        self._stat_dns.setText(f"DNS: {dns_ok}")
        self._stat_dns.setStyleSheet(
            f"color:{'#3fb950' if ok else '#f85149'}; font-size:10px;"
        )

    def _on_resolver_changed(self, d: dict):
        self.terminal.append_line(
            f"🔴 DNS RESOLVER CHANGED: {d['old']} → {d['new']}", 'threat'
        )

    def _on_traffic_sample(self, d: dict):
        self.traffic_graph.update_data(
            d['timestamps'],
            d['history_in'],
            d['history_out'],
            label1='↓ In', label2='↑ Out'
        )

    def _on_guard_stats(self, d: dict):
        self._stat_conns.setText(f"Connections: {d.get('active', 0)}")
        self._stat_threats.setText(f"Threats: {self.threat_table.rowCount()}")

    def _on_scanner_stats(self, d: dict):
        self._stat_scanners.setText(f"Scanners: {d.get('total_scanners', 0)}")

    def _on_dns_stats(self, d: dict):
        resolvers = d.get('resolvers', [])
        if resolvers:
            self.terminal.append_line(
                f"DNS resolvers: {', '.join(resolvers)}", 'muted'
            )

    # ── Kill switch ────────────────────────────────────────────────────────

    def _kill_selected(self):
        self._kill_from_conn_table()

    def _kill_from_conn_table(self):
        rows = self.conn_table.selectedItems()
        if not rows:
            QMessageBox.information(self, "Kill Connection",
                                    "Select a connection row in the Connections tab first.")
            return
        row = rows[0].row()
        item = self.conn_table.item(row, 3)
        if not item:
            return
        addr_data = item.data(Qt.ItemDataRole.UserRole)
        if not addr_data:
            return
        raddr, rport = addr_data
        self._do_kill(raddr, rport)

    def _kill_from_table(self, index):
        row = index.row()
        item = self.conn_table.item(row, 3)
        if not item:
            return
        addr_data = item.data(Qt.ItemDataRole.UserRole)
        if not addr_data:
            return
        raddr, rport = addr_data
        self._do_kill(raddr, rport)

    def _do_kill(self, raddr: str, rport: int):
        reply = QMessageBox.question(
            self, "⚡ Kill Connection",
            f"Terminate connection to {raddr}:{rport}?\n\n"
            "This will forcibly close the TCP connection.\n"
            "Only use against suspicious/hostile connections.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if not self._guard:
            QMessageBox.warning(self, "Kill Connection",
                                "Start monitoring first.")
            return

        ok, msg = self._guard.kill_connection(raddr, rport)
        if ok:
            self.terminal.append_line(f"⚡ KILLED: {raddr}:{rport} — {msg}", 'action')
            self.status_message.emit(f"Connection killed: {raddr}:{rport}")
        else:
            self.terminal.append_line(f"⚠  Kill failed: {msg}", 'warn')
            QMessageBox.warning(self, "Kill Failed", msg)

    # ── Public API: receive events from other IR modules ──────────────────

    def log_scan_event(self, module: str, target: str, message: str):
        """Called by main_window to relay other modules' activity here."""
        self.terminal.append_line(
            f"[{module.upper():<12}] {target}  —  {message}",
            'info'
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_table(headers) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(False)
        t.setStyleSheet("""
            QTableWidget { background:#010409; border:none; }
            QHeaderView::section {
                background:#0d1117; color:#484f58;
                border:none; border-bottom:1px solid #21262d;
                font-size:10px; padding:4px 6px;
            }
            QTableWidget::item { padding: 2px 6px; font-size:10px; }
            QTableWidget::item:selected { background:#1f6feb22; }
        """)
        return t

    def _clear_all(self):
        for t in [self.threat_table, self.conn_table,
                  self.scanner_table, self.dns_table]:
            t.setRowCount(0)
        self.terminal.clear()
        self.terminal.append_line("Log cleared", 'muted')
        self._conn_rows.clear()
        self.threat_tabs.setTabText(0, "⚠️ Threats (0)")
        self.threat_tabs.setTabText(1, "🔌 Connections (0)")
        self.threat_tabs.setTabText(2, "🔭 Scanners (0)")

    def apply_settings(self, s):
        pass
