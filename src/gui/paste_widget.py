"""
Inspector Rabbit - Paste & Leak Scanner Widget
Search for exposed data across paste sites, GitHub, Reddit, and HackerNews
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import webbrowser

from ..modules.paste_scanner import PasteScannerThread
from .components import apply_page_header_style


RISK_COLORS = {
    'high':   '#f85149',
    'medium': '#ffa657',
    'low':    '#3fb950',
    'info':   '#58a6ff',
}

RISK_ICONS = {
    'high':   '🔴',
    'medium': '🟡',
    'low':    '🟢',
    'info':   '🔵',
}


class PasteWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._results = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        bar = QFrame()
        apply_page_header_style(bar, "#f472b6")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("📋")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Paste & Leak Scanner")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Search GitHub · HackerNews · Reddit · Pastebin for exposed credentials & data")
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

        self._lbl("SEARCH QUERY", lay)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("email, domain, username...")
        self.query_input.setFixedHeight(42)
        self.query_input.setFont(QFont("Ubuntu", 12))
        self.query_input.returnPressed.connect(self._start)
        lay.addWidget(self.query_input)

        self.scan_btn = QPushButton("🔎  Scan All Sources")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.clicked.connect(self._start)
        lay.addWidget(self.scan_btn)

        lay.addWidget(self._sep())
        self._lbl("SOURCES", lay)

        self.src_github = QCheckBox("GitHub Gists & Code")
        self.src_github.setChecked(True)
        self.src_hackernews = QCheckBox("HackerNews (Algolia)")
        self.src_hackernews.setChecked(True)
        self.src_reddit = QCheckBox("Reddit (Pushshift)")
        self.src_reddit.setChecked(True)
        self.src_pastebin = QCheckBox("Pastebin (psbdmp)")
        self.src_pastebin.setChecked(True)

        for cb in [self.src_github, self.src_hackernews, self.src_reddit, self.src_pastebin]:
            cb.setStyleSheet("color: #c9d1d9; font-size: 12px;")
            lay.addWidget(cb)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet("""
            QTextEdit { background:#010409; border:1px solid #21262d; border-radius:8px;
                        color:#3fb950; font-family:'Ubuntu Mono',monospace; font-size:11px; }
        """)
        self.log.setMinimumHeight(160)
        lay.addWidget(self.log)

        lay.addStretch()

        # Risk summary
        self.risk_label = QLabel("Risk: —")
        self.risk_label.setStyleSheet("color: #484f58; font-size: 12px; border: none;")
        lay.addWidget(self.risk_label)

        copy_btn = QPushButton("📋 Copy All Results")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(self._copy_results)
        lay.addWidget(copy_btn)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # All results table
        self.all_table = self._make_table(["Risk", "Source", "Title / Snippet", "Date", "URL"])
        self.all_table.setColumnWidth(0, 60)
        self.all_table.setColumnWidth(1, 100)
        self.all_table.setColumnWidth(3, 90)
        self.all_table.doubleClicked.connect(self._open_link)
        self.tabs.addTab(self.all_table, "🔍 All Results (0)")

        # High risk table
        self.high_table = self._make_table(["Source", "Title / Snippet", "Date", "URL"])
        self.high_table.doubleClicked.connect(self._open_link_high)
        self.tabs.addTab(self.high_table, "🔴 High Risk (0)")

        # GitHub tab
        self.github_table = self._make_table(["Type", "Title", "Language", "URL"])
        self.github_table.doubleClicked.connect(self._open_link_github)
        self.tabs.addTab(self.github_table, "🐙 GitHub")

        # Pastebin tab
        self.paste_table = self._make_table(["ID", "Title", "Date", "URL"])
        self.paste_table.doubleClicked.connect(self._open_link_paste)
        self.tabs.addTab(self.paste_table, "📋 Pastes")

        return panel

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(True)
        return t

    def _lbl(self, text, lay):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(l)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _start(self):
        query = self.query_input.text().strip()
        if not query:
            self.log.append("⚠️  Enter a search query")
            return

        sources = {
            'github': self.src_github.isChecked(),
            'hackernews': self.src_hackernews.isChecked(),
            'reddit': self.src_reddit.isChecked(),
            'pastebin': self.src_pastebin.isChecked(),
        }

        self.log.clear()
        for t in [self.all_table, self.high_table, self.github_table, self.paste_table]:
            t.setRowCount(0)
        self._results = []

        self.log.append(f"🐇 Scanning for: {query}")
        self.scan_btn.setEnabled(False)
        self.risk_label.setText("Risk: scanning...")

        self._thread = PasteScannerThread(query, sources)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.finished.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"Scanning paste sites for: {query}")

    def _on_result(self, result: dict):
        self._results.append(result)
        source = result.get('source', '')
        title = result.get('title', result.get('snippet', ''))[:80]
        url = result.get('url', '')
        date = result.get('date', '')[:10] if result.get('date') else ''
        risk = result.get('risk', 'info')
        icon = RISK_ICONS.get(risk, '●')
        color = QColor(RISK_COLORS.get(risk, '#8b949e'))

        # All results table
        row = self.all_table.rowCount()
        self.all_table.insertRow(row)
        risk_item = QTableWidgetItem(f"{icon} {risk.upper()}")
        risk_item.setForeground(color)
        risk_item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
        self.all_table.setItem(row, 0, risk_item)
        src_item = QTableWidgetItem(source)
        src_item.setForeground(QColor("#58a6ff"))
        self.all_table.setItem(row, 1, src_item)
        self.all_table.setItem(row, 2, QTableWidgetItem(title))
        self.all_table.setItem(row, 3, QTableWidgetItem(date))
        url_item = QTableWidgetItem(url)
        url_item.setForeground(QColor("#00f5ff"))
        self.all_table.setItem(row, 4, url_item)

        # High risk
        if risk == 'high':
            row2 = self.high_table.rowCount()
            self.high_table.insertRow(row2)
            src_item2 = QTableWidgetItem(source)
            src_item2.setForeground(QColor("#f85149"))
            self.high_table.setItem(row2, 0, src_item2)
            self.high_table.setItem(row2, 1, QTableWidgetItem(title))
            self.high_table.setItem(row2, 2, QTableWidgetItem(date))
            url_item2 = QTableWidgetItem(url)
            url_item2.setForeground(QColor("#00f5ff"))
            self.high_table.setItem(row2, 3, url_item2)

        # Source-specific tabs
        if source in ('GitHub Gists', 'GitHub Code', 'GitHub Repos'):
            row3 = self.github_table.rowCount()
            self.github_table.insertRow(row3)
            type_item = QTableWidgetItem(source.replace('GitHub ', ''))
            type_item.setForeground(QColor("#a78bfa"))
            self.github_table.setItem(row3, 0, type_item)
            self.github_table.setItem(row3, 1, QTableWidgetItem(title))
            lang = result.get('language', '')
            self.github_table.setItem(row3, 2, QTableWidgetItem(lang or ''))
            url_item3 = QTableWidgetItem(url)
            url_item3.setForeground(QColor("#00f5ff"))
            self.github_table.setItem(row3, 3, url_item3)

        if source == 'Pastebin':
            row4 = self.paste_table.rowCount()
            self.paste_table.insertRow(row4)
            pid = result.get('id', '')
            self.paste_table.setItem(row4, 0, QTableWidgetItem(pid))
            self.paste_table.setItem(row4, 1, QTableWidgetItem(title))
            self.paste_table.setItem(row4, 2, QTableWidgetItem(date))
            url_item4 = QTableWidgetItem(url)
            url_item4.setForeground(QColor("#00f5ff"))
            self.paste_table.setItem(row4, 3, url_item4)

    def _on_done(self):
        self.scan_btn.setEnabled(True)
        total = len(self._results)
        high = sum(1 for r in self._results if r.get('risk') == 'high')
        medium = sum(1 for r in self._results if r.get('risk') == 'medium')

        idx = self.tabs.indexOf(self.all_table)
        self.tabs.setTabText(idx, f"🔍 All Results ({total})")
        idx2 = self.tabs.indexOf(self.high_table)
        self.tabs.setTabText(idx2, f"🔴 High Risk ({high})")

        if high > 0:
            self.risk_label.setText(f"🔴 {high} HIGH · {medium} medium")
            self.risk_label.setStyleSheet("color: #f85149; font-size: 12px; font-weight: bold; border: none;")
        elif medium > 0:
            self.risk_label.setText(f"🟡 {medium} medium results")
            self.risk_label.setStyleSheet("color: #ffa657; font-size: 12px; border: none;")
        else:
            self.risk_label.setText(f"🟢 {total} results (low risk)")
            self.risk_label.setStyleSheet("color: #3fb950; font-size: 12px; border: none;")

        self.log.append(f"✅ Scan complete: {total} results ({high} high risk)")
        self.status_message.emit(f"Leak scan: {total} results, {high} high risk")

        if high > 0:
            idx2 = self.tabs.indexOf(self.high_table)
            self.tabs.setCurrentIndex(idx2)

    def _open_link(self, index):
        url_col = 4
        url = self.all_table.item(index.row(), url_col)
        if url and url.text().startswith('http'):
            webbrowser.open(url.text())

    def _open_link_high(self, index):
        url_col = 3
        url = self.high_table.item(index.row(), url_col)
        if url and url.text().startswith('http'):
            webbrowser.open(url.text())

    def _open_link_github(self, index):
        url_col = 3
        url = self.github_table.item(index.row(), url_col)
        if url and url.text().startswith('http'):
            webbrowser.open(url.text())

    def _open_link_paste(self, index):
        url_col = 3
        url = self.paste_table.item(index.row(), url_col)
        if url and url.text().startswith('http'):
            webbrowser.open(url.text())

    def _copy_results(self):
        if not self._results:
            return
        lines = []
        for r in self._results:
            lines.append(f"[{r.get('risk','?').upper()}] {r.get('source','')} | {r.get('title','')} | {r.get('url','')}")
        QApplication.clipboard().setText('\n'.join(lines))
        self.log.append(f"📋 Copied {len(self._results)} results")

    def apply_settings(self, s):
        pass
