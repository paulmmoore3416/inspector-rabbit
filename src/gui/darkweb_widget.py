"""
Inspector Rabbit - Dark Web Exposure Widget
Search public OSINT / dark-web index sources for target exposure.
"""

import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QSplitter, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.darkweb_lookup import DarkWebThread
from .components import apply_page_header_style


ACCENT = "#a855f7"

RISK_COLORS = {
    "high":   "#f85149",
    "medium": "#ffa657",
    "low":    "#3fb950",
}
RISK_ICONS = {
    "high":   "🔴",
    "medium": "🟡",
    "low":    "🟢",
}
RISK_BG = {
    "high":   "#2d0d0d",
    "medium": "#2d1a00",
    "low":    "#0d1f0d",
}

QUERY_TYPES = ["Email", "Domain", "Username", "Keyword"]


class DarkWebWidget(QWidget):
    send_to_graph = pyqtSignal(dict)   # included for consistency
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._results: list[dict] = []
        self._summary: dict = {}
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────────────

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

        icon = QLabel("🕵️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Dark Web Exposure Scanner")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel(
            "Ahmia.fi · Intelligence X · Pastebin (psbdmp) · DarkSearch.io — "
            "all free, no Tor required"
        )
        t2.setStyleSheet(
            "color: #8b949e; font-size: 11px; border: none; background: transparent;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")
        layout.addWidget(splitter, 1)

        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([290, 900])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet(
            "QFrame { background: #010409; border-right: 1px solid #21262d; }"
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(12)

        # Query input
        self._lbl("SEARCH QUERY", lay)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("email, domain, username, keyword…")
        self.query_input.setFixedHeight(42)
        self.query_input.setFont(QFont("Ubuntu", 12))
        self.query_input.returnPressed.connect(self._start)
        self.query_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 8px; color: #e6edf3; padding: 4px 12px;
            }
            QLineEdit:focus { border-color: #a855f7; }
        """)
        lay.addWidget(self.query_input)

        # Query type selector
        self._lbl("QUERY TYPE", lay)
        self.type_combo = QComboBox()
        self.type_combo.addItems(QUERY_TYPES)
        self.type_combo.setFixedHeight(36)
        self.type_combo.setFont(QFont("Ubuntu", 11))
        self.type_combo.setStyleSheet(f"""
            QComboBox {{
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 8px; color: #e6edf3; padding: 4px 12px;
            }}
            QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background: #0d1117; color: #e6edf3;
                selection-background-color: {ACCENT}33;
            }}
        """)
        lay.addWidget(self.type_combo)

        # Scan button
        self.scan_btn = QPushButton("🕵️  Scan Dark Web")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22; border: 1px solid {ACCENT}55;
                color: {ACCENT}; border-radius: 8px; padding: 4px 16px;
            }}
            QPushButton:hover {{ background: {ACCENT}40; border-color: {ACCENT}; }}
            QPushButton:pressed {{ background: {ACCENT}60; }}
            QPushButton:disabled {{ color: #484f58; border-color: #21262d; background: #010409; }}
        """)
        self.scan_btn.clicked.connect(self._start)
        lay.addWidget(self.scan_btn)

        lay.addWidget(self._sep())
        self._lbl("STATUS LOG", lay)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet("""
            QTextEdit {
                background: #010409; border: 1px solid #21262d;
                border-radius: 8px; color: #3fb950;
                font-family: 'Ubuntu Mono', monospace; font-size: 11px;
            }
        """)
        self.log.setMinimumHeight(160)
        lay.addWidget(self.log)

        lay.addStretch()

        # Exposure score label
        self.exposure_lbl = QLabel("Exposure Score: —")
        self.exposure_lbl.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        self.exposure_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exposure_lbl.setStyleSheet(
            "color: #484f58; border: 1px solid #21262d; border-radius: 8px; padding: 8px;"
        )
        self.exposure_lbl.setWordWrap(True)
        lay.addWidget(self.exposure_lbl)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #21262d; border-radius: 6px; }}
            QTabBar::tab {{
                background: #010409; color: #8b949e;
                padding: 8px 16px; border: 1px solid #21262d;
                border-bottom: none; border-radius: 6px 6px 0 0; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: #0d1117; color: #e6edf3; border-bottom: 2px solid {ACCENT}; }}
            QTabBar::tab:hover {{ background: #0d1117; color: #c9d1d9; }}
        """)
        lay.addWidget(self.tabs)

        # Tab 1: All Results
        self.all_table = self._make_table(
            ["Source", "Title", "Risk", "Snippet", "URL"]
        )
        self.all_table.setColumnWidth(0, 120)
        self.all_table.setColumnWidth(2, 70)
        self.all_table.doubleClicked.connect(
            lambda idx: self._open_url(self.all_table, idx, 4)
        )
        self.tabs.addTab(self.all_table, "🔍 All Results (0)")

        # Tab 2: High Risk
        self.high_table = self._make_table(
            ["Source", "Title", "Snippet", "URL"]
        )
        self.high_table.doubleClicked.connect(
            lambda idx: self._open_url(self.high_table, idx, 3)
        )
        self.tabs.addTab(self.high_table, "🔴 High Risk (0)")

        # Tab 3: Exposure Score breakdown
        self.score_widget = QWidget()
        score_lay = QVBoxLayout(self.score_widget)
        score_lay.setContentsMargins(32, 32, 32, 32)
        score_lay.setSpacing(16)

        self.score_html = QLabel("Run a scan to see exposure analysis.")
        self.score_html.setWordWrap(True)
        self.score_html.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.score_html.setFont(QFont("Ubuntu", 11))
        self.score_html.setStyleSheet("color: #c9d1d9; border: none; background: transparent;")
        self.score_html.setTextFormat(Qt.TextFormat.RichText)
        score_lay.addWidget(self.score_html)
        score_lay.addStretch()

        self.tabs.addTab(self.score_widget, "📊 Exposure Score")

        return panel

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(
            len(headers) - 1, QHeaderView.ResizeMode.Stretch
        )
        t.setAlternatingRowColors(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(True)
        t.setStyleSheet("""
            QTableWidget {
                background: #0d1117; color: #c9d1d9;
                border: 1px solid #21262d; border-radius: 6px;
                gridline-color: #161b22;
            }
            QHeaderView::section {
                background: #010409; color: #8b949e;
                border: none; border-bottom: 1px solid #21262d;
                padding: 4px 8px; font-size: 10px; font-weight: 700;
            }
        """)
        return t

    def _lbl(self, text: str, lay):
        l = QLabel(text)
        l.setStyleSheet(
            "color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        lay.addWidget(l)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _open_url(self, table: QTableWidget, index, url_col: int):
        item = table.item(index.row(), url_col)
        if item and item.text().startswith("http"):
            webbrowser.open(item.text())

    # ── Actions ───────────────────────────────────────────────────────────────

    def _start(self):
        query = self.query_input.text().strip()
        if not query:
            self.log.append("⚠️  Enter a search query.")
            return

        query_type = self.type_combo.currentText().lower()
        self.log.clear()
        self.all_table.setRowCount(0)
        self.high_table.setRowCount(0)
        self._results = []
        self._summary = {}
        self.score_html.setText("Scanning…")
        self.exposure_lbl.setText("Scanning…")
        self.exposure_lbl.setStyleSheet(
            "color: #8b949e; border: 1px solid #21262d; border-radius: 8px; padding: 8px;"
        )

        self.scan_btn.setEnabled(False)
        self.log.append(f"🐇 Scanning for [{query_type}]: {query}")

        self._thread = DarkWebThread(query, query_type)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_found.connect(self._on_result)
        self._thread.done.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"Dark web scan: {query}")

    def _on_result(self, r: dict):
        self._results.append(r)
        risk = r.get("risk_level", "low")
        color = QColor(RISK_COLORS.get(risk, "#8b949e"))
        bg_hex = RISK_BG.get(risk, "#0d1117")
        icon = RISK_ICONS.get(risk, "●")

        # All Results tab
        row = self.all_table.rowCount()
        self.all_table.insertRow(row)

        src_item = QTableWidgetItem(r.get("source", ""))
        src_item.setForeground(QColor(ACCENT))
        self.all_table.setItem(row, 0, src_item)
        self.all_table.setItem(row, 1, QTableWidgetItem(r.get("title", "")[:80]))

        risk_item = QTableWidgetItem(f"{icon} {risk.upper()}")
        risk_item.setForeground(color)
        risk_item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
        self.all_table.setItem(row, 2, risk_item)
        self.all_table.setItem(row, 3, QTableWidgetItem(r.get("snippet", "")[:80]))

        url_item = QTableWidgetItem(r.get("url", ""))
        url_item.setForeground(QColor("#58a6ff"))
        self.all_table.setItem(row, 4, url_item)

        # Tint row background by risk level
        bg = QColor(bg_hex)
        for col in range(5):
            cell = self.all_table.item(row, col)
            if cell:
                cell.setBackground(bg)

        # High Risk tab
        if risk == "high":
            row2 = self.high_table.rowCount()
            self.high_table.insertRow(row2)

            src_item2 = QTableWidgetItem(r.get("source", ""))
            src_item2.setForeground(QColor("#f85149"))
            self.high_table.setItem(row2, 0, src_item2)
            self.high_table.setItem(row2, 1, QTableWidgetItem(r.get("title", "")[:80]))
            self.high_table.setItem(row2, 2, QTableWidgetItem(r.get("snippet", "")[:80]))
            url_item2 = QTableWidgetItem(r.get("url", ""))
            url_item2.setForeground(QColor("#58a6ff"))
            self.high_table.setItem(row2, 3, url_item2)
            for col in range(4):
                cell = self.high_table.item(row2, col)
                if cell:
                    cell.setBackground(QColor("#2d0d0d"))

        # Update tab labels live
        all_idx  = self.tabs.indexOf(self.all_table)
        high_idx = self.tabs.indexOf(self.high_table)
        total    = self.all_table.rowCount()
        highs    = self.high_table.rowCount()
        self.tabs.setTabText(all_idx,  f"🔍 All Results ({total})")
        self.tabs.setTabText(high_idx, f"🔴 High Risk ({highs})")

    def _on_done(self, summary: dict):
        self._summary = summary
        self.scan_btn.setEnabled(True)

        total   = summary.get("total_found", 0)
        highs   = summary.get("high_risk", 0)
        sources = summary.get("sources_checked", 0)
        score   = summary.get("exposure_score", 0)

        medium_count = sum(
            1 for r in self._results if r.get("risk_level") == "medium"
        )
        low_count = sum(
            1 for r in self._results if r.get("risk_level") == "low"
        )

        self.log.append(
            f"✅ Done — {total} result(s) from {sources} source(s). "
            f"Exposure score: {score}"
        )

        # Exposure score label
        if score > 20:
            score_color = "#f85149"
        elif score > 10:
            score_color = "#ffa657"
        else:
            score_color = "#3fb950"

        self.exposure_lbl.setText(
            f"<span style='font-size:18px; color:{score_color};'>"
            f"Score: {score}</span>"
        )
        self.exposure_lbl.setStyleSheet(
            f"color: {score_color}; border: 1px solid {score_color}44; "
            f"border-radius: 8px; padding: 8px;"
        )

        # Score tab HTML
        rec_lines = []
        if highs > 0:
            rec_lines.append(
                "⛔ <b>Immediate action required</b>: change passwords, "
                "enable 2FA, review all exposed accounts."
            )
        if medium_count > 0:
            rec_lines.append(
                "⚠️ Review exposed profile/account information — "
                "consider privacy hardening."
            )
        if score == 0:
            rec_lines.append(
                "✅ No significant exposure found in scanned sources."
            )

        recs_html = "".join(
            f"<li style='margin:4px 0;'>{r}</li>" for r in rec_lines
        )

        self.score_html.setText(f"""
<h2 style='color:{score_color};'>Exposure Score: {score}</h2>
<table style='border-collapse:collapse; font-size:13px; color:#c9d1d9;'>
  <tr><td style='padding:4px 16px 4px 0; color:#f85149;'>🔴 High Risk</td>
      <td><b>{highs}</b> result(s) × 10 = <b>{highs * 10}</b> pts</td></tr>
  <tr><td style='padding:4px 16px 4px 0; color:#ffa657;'>🟡 Medium Risk</td>
      <td><b>{medium_count}</b> result(s) × 5 = <b>{medium_count * 5}</b> pts</td></tr>
  <tr><td style='padding:4px 16px 4px 0; color:#3fb950;'>🟢 Low Risk</td>
      <td><b>{low_count}</b> result(s) × 1 = <b>{low_count}</b> pt(s)</td></tr>
  <tr><td style='padding:8px 16px 4px 0; color:#8b949e;'>Sources Checked</td>
      <td>{sources}</td></tr>
  <tr><td style='padding:4px 16px 4px 0; color:#8b949e;'>Total Results</td>
      <td>{total}</td></tr>
</table>
<br>
<b style='color:#e6edf3;'>Recommendations:</b>
<ul style='color:#c9d1d9; padding-left:18px;'>{recs_html}</ul>
        """)

        self.tabs.setCurrentIndex(self.tabs.indexOf(self.score_widget))
        self.status_message.emit(
            f"Dark web scan complete: {total} results, score {score}"
        )
        if highs > 0:
            self.tabs.setCurrentIndex(self.tabs.indexOf(self.high_table))

    def apply_settings(self, s):
        pass
