"""
Inspector Rabbit - Breach Aggregation Widget
Query multiple breach databases and aggregate results.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QComboBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.breach_agg import BreachAggThread
from .components import apply_page_header_style


ACCENT = "#ff6b6b"

SEV_COLOR = {
    'high':   '#f85149',
    'medium': '#e3b341',
    'low':    '#3fb950',
}
SEV_ICON = {
    'high':   '🔴',
    'medium': '🟡',
    'low':    '🟢',
}


class BreachWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._breaches = []
        self._settings = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        bar = QFrame()
        apply_page_header_style(bar, ACCENT)
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)

        icon = QLabel("🚨")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Breach Aggregator")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("HIBP · LeakCheck · BreachDirectory — multi-source breach intelligence")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        layout.addLayout(content, 1)
        content.addWidget(self._build_left())
        content.addWidget(self._build_right(), 1)

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(12)

        self._lbl("QUERY", lay)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("email, domain, or username")
        self.query_input.setFixedHeight(42)
        self.query_input.setFont(QFont("Ubuntu", 12))
        self.query_input.returnPressed.connect(self._start)
        lay.addWidget(self.query_input)

        self._lbl("TYPE", lay)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Email", "Domain", "Username"])
        self.type_combo.setFixedHeight(38)
        self.type_combo.setFont(QFont("Ubuntu", 11))
        lay.addWidget(self.type_combo)

        self._lbl("HIBP API KEY (optional)", lay)
        self.hibp_input = QLineEdit()
        self.hibp_input.setPlaceholderText("Paste your HIBP key here")
        self.hibp_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.hibp_input.setFixedHeight(38)
        self.hibp_input.setFont(QFont("Ubuntu", 11))
        lay.addWidget(self.hibp_input)

        self.scan_btn = QPushButton("🔎  Scan Breaches")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.clicked.connect(self._start)
        lay.addWidget(self.scan_btn)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet(f"""
            QTextEdit {{
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: {ACCENT};
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }}
        """)
        self.log.setMinimumHeight(140)
        lay.addWidget(self.log)

        lay.addStretch()

        # Risk summary frame
        self.risk_frame = QFrame()
        self.risk_frame.setStyleSheet("""
            QFrame {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
            }
        """)
        risk_lay = QVBoxLayout(self.risk_frame)
        risk_lay.setContentsMargins(12, 10, 12, 10)
        risk_lay.setSpacing(4)

        self._lbl("RISK SUMMARY", risk_lay)
        self.total_label = QLabel("Total breaches: —")
        self.total_label.setStyleSheet("color: #c9d1d9; font-size: 12px; border: none;")
        risk_lay.addWidget(self.total_label)

        self.severity_label = QLabel("Highest severity: —")
        self.severity_label.setStyleSheet("color: #484f58; font-size: 12px; border: none;")
        risk_lay.addWidget(self.severity_label)

        lay.addWidget(self.risk_frame)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # All Breaches table
        cols_all = ["Source", "Breach Name", "Date", "Records", "Severity", "Description"]
        self.all_table = self._make_table(cols_all)
        self.all_table.setColumnWidth(0, 110)
        self.all_table.setColumnWidth(1, 150)
        self.all_table.setColumnWidth(2, 90)
        self.all_table.setColumnWidth(3, 80)
        self.all_table.setColumnWidth(4, 80)
        self.tabs.addTab(self.all_table, "📋 All Breaches (0)")

        # High Risk table
        cols_high = ["Source", "Breach Name", "Date", "Records", "Description"]
        self.high_table = self._make_table(cols_high)
        self.tabs.addTab(self.high_table, "🔴 High Risk (0)")

        # Summary tab
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setStyleSheet("QLabel { background: #0d1117; color: #c9d1d9; padding: 16px; border: none; }")
        self.summary_label.setText(self._placeholder_html())
        self.tabs.addTab(self.summary_label, "📊 Summary")

        return panel

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_table(self, headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(True)
        return t

    def _lbl(self, text: str, lay):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(l)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _placeholder_html(self) -> str:
        return """
        <div style='padding:24px; text-align:center; color:#8b949e;'>
        <div style='font-size:48px; margin-bottom:16px;'>🚨</div>
        <h2 style='color:#e6edf3;'>Breach Aggregator</h2>
        <p>Enter a query and click Scan Breaches to aggregate results<br>
        from HIBP, LeakCheck, and BreachDirectory.</p>
        </div>
        """

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start(self):
        query = self.query_input.text().strip()
        if not query:
            self.log.append("⚠️  Enter a query")
            return

        query_type = self.type_combo.currentText().lower()
        hibp_key = self.hibp_input.text().strip()
        if not hibp_key:
            hibp_key = self._settings.get('hibp_api_key', '')

        self.log.clear()
        self._breaches = []
        self.all_table.setRowCount(0)
        self.high_table.setRowCount(0)
        self.total_label.setText("Total breaches: scanning...")
        self.severity_label.setText("Highest severity: —")
        self.severity_label.setStyleSheet("color: #484f58; font-size: 12px; border: none;")

        self.tabs.setTabText(0, "📋 All Breaches (0)")
        self.tabs.setTabText(1, "🔴 High Risk (0)")

        self.log.append(f"🐇 Scanning: {query} [{query_type}]")
        self.scan_btn.setEnabled(False)

        self._thread = BreachAggThread(query, query_type, hibp_key)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.breach_found.connect(self._on_breach)
        self._thread.result_ready.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"Scanning breaches for: {query}")

    def _on_breach(self, breach: dict):
        self._breaches.append(breach)
        source = breach.get('source', '')
        name = breach.get('breach_name', '')
        date = breach.get('date', '')
        count = breach.get('count', '')
        severity = breach.get('severity', 'low')
        description = breach.get('description', '')[:120]

        icon = SEV_ICON.get(severity, '⚪')
        color = QColor(SEV_COLOR.get(severity, '#8b949e'))

        # All Breaches
        row = self.all_table.rowCount()
        self.all_table.insertRow(row)

        src_item = QTableWidgetItem(source)
        src_item.setForeground(QColor("#58a6ff"))
        self.all_table.setItem(row, 0, src_item)

        name_item = QTableWidgetItem(name)
        name_item.setForeground(QColor("#e6edf3"))
        self.all_table.setItem(row, 1, name_item)

        self.all_table.setItem(row, 2, QTableWidgetItem(date))

        count_item = QTableWidgetItem(count)
        count_item.setForeground(QColor("#8b949e"))
        self.all_table.setItem(row, 3, count_item)

        sev_item = QTableWidgetItem(f"{icon} {severity.upper()}")
        sev_item.setForeground(color)
        sev_item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
        self.all_table.setItem(row, 4, sev_item)

        self.all_table.setItem(row, 5, QTableWidgetItem(description))

        # High Risk tab
        if severity == 'high':
            row2 = self.high_table.rowCount()
            self.high_table.insertRow(row2)

            src2 = QTableWidgetItem(source)
            src2.setForeground(QColor("#f85149"))
            self.high_table.setItem(row2, 0, src2)

            nm2 = QTableWidgetItem(name)
            nm2.setForeground(QColor("#e6edf3"))
            self.high_table.setItem(row2, 1, nm2)

            self.high_table.setItem(row2, 2, QTableWidgetItem(date))

            cnt2 = QTableWidgetItem(count)
            cnt2.setForeground(QColor("#ffa657"))
            self.high_table.setItem(row2, 3, cnt2)

            self.high_table.setItem(row2, 4, QTableWidgetItem(description))

        # Update tab counts
        total = self.all_table.rowCount()
        high_count = self.high_table.rowCount()
        self.tabs.setTabText(0, f"📋 All Breaches ({total})")
        self.tabs.setTabText(1, f"🔴 High Risk ({high_count})")

    def _on_done(self, summary: dict):
        self.scan_btn.setEnabled(True)
        total = summary.get('total_breaches', 0)
        sources = summary.get('sources_checked', [])
        highest = summary.get('highest_severity', 'low')
        query = summary.get('query', '')

        self.total_label.setText(f"Total breaches: {total}")
        sev_color = SEV_COLOR.get(highest, '#8b949e')
        sev_icon = SEV_ICON.get(highest, '⚪')
        self.severity_label.setText(f"Highest: {sev_icon} {highest.upper()}")
        self.severity_label.setStyleSheet(
            f"color: {sev_color}; font-size: 12px; font-weight: bold; border: none;"
        )

        self.log.append(f"✅ Done — {total} breach(es) found")
        self.status_message.emit(f"Breach scan: {total} results, highest={highest}")

        # Summary HTML
        high_count = self.high_table.rowCount()
        medium_count = sum(1 for b in self._breaches if b.get('severity') == 'medium')
        low_count = sum(1 for b in self._breaches if b.get('severity') == 'low')

        html = f"""
        <div style='padding:20px; color:#c9d1d9;'>
          <h2 style='color:{ACCENT}; margin-bottom:16px;'>🚨 Breach Report: {query}</h2>

          <table style='width:100%; border-collapse:collapse; margin-bottom:20px;'>
            <tr>
              <td style='padding:12px; background:#1c0a0a; border:1px solid #f8514944;
                          border-radius:6px; text-align:center; width:25%;'>
                <div style='font-size:28px; color:#f85149;'>{total}</div>
                <div style='font-size:11px; color:#8b949e;'>Total Breaches</div>
              </td>
              <td style='width:4%;'></td>
              <td style='padding:12px; background:#1c1200; border:1px solid #e3b34144;
                          border-radius:6px; text-align:center; width:25%;'>
                <div style='font-size:28px; color:#f85149;'>{high_count}</div>
                <div style='font-size:11px; color:#8b949e;'>High Severity</div>
              </td>
              <td style='width:4%;'></td>
              <td style='padding:12px; background:#0d1117; border:1px solid #21262d;
                          border-radius:6px; text-align:center; width:25%;'>
                <div style='font-size:28px; color:#e3b341;'>{medium_count}</div>
                <div style='font-size:11px; color:#8b949e;'>Medium Severity</div>
              </td>
              <td style='width:4%;'></td>
              <td style='padding:12px; background:#0d1117; border:1px solid #21262d;
                          border-radius:6px; text-align:center; width:25%;'>
                <div style='font-size:28px; color:#3fb950;'>{low_count}</div>
                <div style='font-size:11px; color:#8b949e;'>Low Severity</div>
              </td>
            </tr>
          </table>

          <div style='margin-bottom:12px;'>
            <span style='color:#484f58; font-size:10px; font-weight:700; letter-spacing:1px;'>
              SOURCES CHECKED
            </span>
          </div>
          <div style='margin-bottom:20px;'>
        """
        for src in sources:
            html += f"""
            <span style='background:#161b22; border:1px solid #30363d; border-radius:6px;
                          padding:4px 12px; margin-right:8px; color:#58a6ff; font-size:12px;'>
              {src}
            </span>"""

        html += "</div>"

        if self._breaches:
            html += """
            <div style='margin-bottom:8px;'>
              <span style='color:#484f58; font-size:10px; font-weight:700; letter-spacing:1px;'>
                BREACH LIST
              </span>
            </div>"""
            for b in self._breaches:
                sev = b.get('severity', 'low')
                sc = SEV_COLOR.get(sev, '#8b949e')
                si = SEV_ICON.get(sev, '⚪')
                html += f"""
                <div style='background:#0a0f16; border:1px solid #21262d; border-radius:8px;
                             padding:10px 14px; margin-bottom:8px;'>
                  <span style='color:#e6edf3; font-weight:bold;'>{b.get('breach_name', '?')}</span>
                  <span style='margin-left:12px; color:#484f58; font-size:11px;'>
                    {b.get('source', '')} | {b.get('date', 'N/A')} |
                    {b.get('count', '?')} records
                  </span>
                  <span style='margin-left:12px; color:{sc}; font-size:11px; font-weight:bold;'>
                    {si} {sev.upper()}
                  </span>
                  <div style='color:#8b949e; font-size:11px; margin-top:4px;'>
                    {b.get('description', '')[:200]}
                  </div>
                </div>"""
        else:
            html += """
            <div style='text-align:center; color:#3fb950; padding:24px;'>
              <div style='font-size:40px;'>✅</div>
              <p>No breaches found for this query.</p>
            </div>"""

        html += "</div>"
        self.summary_label.setText(html)
        self.tabs.setCurrentIndex(2)

        if high_count > 0:
            self.tabs.setCurrentIndex(1)

    def apply_settings(self, settings: dict):
        self._settings = settings
        saved_key = settings.get('hibp_api_key', '')
        if saved_key and not self.hibp_input.text().strip():
            self.hibp_input.setText(saved_key)
