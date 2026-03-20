"""
Inspector Rabbit - Dark Web Exposure Widget  v1.5.0
Space Gray theme. Per-source toggles, stop button, detail panel,
query history, CSV/JSON export.
"""

import csv
import json
import webbrowser
from io import StringIO

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QSplitter, QSizePolicy,
    QCheckBox, QScrollArea, QFileDialog, QApplication, QMenu,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QAction

from ..modules.darkweb_lookup import DarkWebThread
from .components import apply_page_header_style, MODULE_ACCENTS


ACCENT = MODULE_ACCENTS.get("darkweb", "#bf5af2")

RISK_COLOR = {"high": "#ff453a", "medium": "#ff9f0a", "low": "#30d158"}
RISK_BG    = {"high": "#2a0e0e", "medium": "#261a06", "low": "#0e1f0e"}
RISK_ICON  = {"high": "🔴",      "medium": "🟡",       "low": "🟢"}

QUERY_TYPES = ["Email", "Domain", "Username", "Keyword"]

SOURCE_ICONS = {
    "Ahmia.fi":           "🧅",
    "Intelligence X":     "🗄️",
    "Pastebin (psbdmp)":  "📋",
    "DarkSearch.io":      "🌑",
    "grep.app (GitHub)":  "🐙",
    "URLScan.io":         "🔬",
}


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("background: #38383a; max-height: 1px; border: none; margin: 4px 0;")
    return f


def _section_lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        "color: #3a3a3c; font-size: 10px; font-weight: 700; "
        "letter-spacing: 1.2px; background: transparent;"
    )
    return l


class DarkWebWidget(QWidget):
    send_to_graph  = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: DarkWebThread | None = None
        self._results: list[dict] = []
        self._history: list[str]  = []
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────────────────
        bar = QFrame()
        apply_page_header_style(bar, ACCENT)
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 0, 24, 0)
        bl.setSpacing(12)

        icon = QLabel("🌑")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(1)
        t1 = QLabel("Dark Web Exposure Monitor")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #f5f5f7; border: none; background: transparent;")
        t2 = QLabel(
            "Ahmia · Intelligence X · Pastebin · DarkSearch · GitHub leaks · URLScan"
            "  —  all free, no Tor required"
        )
        t2.setStyleSheet(
            "color: #636366; font-size: 11px; border: none; background: transparent;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl, 1)

        # Export button in header
        self.export_btn = QPushButton("⬇  Export")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setEnabled(False)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}14; border: 1px solid {ACCENT}44;
                color: {ACCENT}; border-radius: 7px;
                padding: 4px 14px; font-weight: 600; font-size: 11px;
            }}
            QPushButton:hover  {{ background: {ACCENT}28; border-color: {ACCENT}88; }}
            QPushButton:disabled {{ color: #3a3a3c; border-color: #2c2c2e; background: transparent; }}
        """)
        self.export_btn.clicked.connect(self._export)
        bl.addWidget(self.export_btn)

        root.addWidget(bar)

        # ── Main horizontal split ───────────────────────────────────────────
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.setHandleWidth(1)
        main_split.setStyleSheet("QSplitter::handle { background: #2c2c2e; }")
        root.addWidget(main_split, 1)

        main_split.addWidget(self._build_left())
        main_split.addWidget(self._build_right())
        main_split.setSizes([300, 900])
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)

    # ── Left panel ─────────────────────────────────────────────────────────────

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(300)
        panel.setStyleSheet(
            "QFrame#leftPanel { background: #161618; border-right: 1px solid #2c2c2e; }"
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical { background: #3a3a3c; border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(16, 18, 16, 18)
        lay.setSpacing(10)

        # ── Query ──────────────────────────────────────────────────────────
        lay.addWidget(_section_lbl("SEARCH TARGET"))

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("email, domain, username, keyword…")
        self.query_input.setFixedHeight(40)
        self.query_input.setFont(QFont("Ubuntu", 12))
        self.query_input.returnPressed.connect(self._start)
        self.query_input.setStyleSheet(f"""
            QLineEdit {{
                background: #2c2c2e; border: 1px solid #38383a;
                border-radius: 8px; color: #f5f5f7; padding: 4px 12px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        lay.addWidget(self.query_input)

        # History combo
        self.history_combo = QComboBox()
        self.history_combo.setPlaceholderText("— recent queries —")
        self.history_combo.setFixedHeight(34)
        self.history_combo.setFont(QFont("Ubuntu", 11))
        self.history_combo.setStyleSheet(f"""
            QComboBox {{
                background: #2c2c2e; border: 1px solid #38383a;
                border-radius: 8px; color: #aeaeb2; padding: 2px 10px;
            }}
            QComboBox:hover {{ border-color: #48484a; }}
            QComboBox QAbstractItemView {{
                background: #2c2c2e; color: #f5f5f7;
                selection-background-color: {ACCENT}33;
                border: 1px solid #38383a; border-radius: 8px;
            }}
        """)
        self.history_combo.currentTextChanged.connect(
            lambda t: self.query_input.setText(t) if t else None
        )
        lay.addWidget(self.history_combo)

        # ── Query type ─────────────────────────────────────────────────────
        lay.addWidget(_section_lbl("QUERY TYPE"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(QUERY_TYPES)
        self.type_combo.setFixedHeight(36)
        self.type_combo.setFont(QFont("Ubuntu", 11))
        self.type_combo.setStyleSheet(f"""
            QComboBox {{
                background: #2c2c2e; border: 1px solid #38383a;
                border-radius: 8px; color: #f5f5f7; padding: 4px 12px;
            }}
            QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background: #2c2c2e; color: #f5f5f7;
                selection-background-color: {ACCENT}33;
                border: 1px solid #38383a;
            }}
        """)
        lay.addWidget(self.type_combo)

        # ── Sources ────────────────────────────────────────────────────────
        lay.addWidget(_sep())
        lay.addWidget(_section_lbl("SOURCES"))

        self._src_checks: dict[str, QCheckBox] = {}
        for src, ico in SOURCE_ICONS.items():
            cb = QCheckBox(f"{ico}  {src}")
            cb.setChecked(True)
            cb.setFont(QFont("Ubuntu", 11))
            cb.setStyleSheet(f"""
                QCheckBox {{ color: #aeaeb2; spacing: 6px; background: transparent; }}
                QCheckBox::indicator {{
                    width: 15px; height: 15px; border-radius: 4px;
                    border: 1px solid #48484a; background: #2c2c2e;
                }}
                QCheckBox::indicator:checked {{
                    background: {ACCENT}; border: none;
                }}
            """)
            self._src_checks[src] = cb
            lay.addWidget(cb)

        # ── Scan / Stop buttons ────────────────────────────────────────────
        lay.addWidget(_sep())

        self.scan_btn = QPushButton("🌑  Scan Dark Web")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22; border: 1px solid {ACCENT}55;
                color: {ACCENT}; border-radius: 8px; padding: 4px 16px;
            }}
            QPushButton:hover   {{ background: {ACCENT}40; border-color: {ACCENT}; }}
            QPushButton:pressed {{ background: {ACCENT}60; }}
            QPushButton:disabled {{ color: #3a3a3c; border-color: #2c2c2e; background: #161618; }}
        """)
        self.scan_btn.clicked.connect(self._start)
        lay.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("⏹  Stop Scan")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #ff453a22; border: 1px solid #ff453a55;
                color: #ff453a; border-radius: 8px; padding: 4px 16px;
                font-weight: 600;
            }
            QPushButton:hover   { background: #ff453a40; border-color: #ff453a; }
            QPushButton:disabled { color: #3a3a3c; border-color: #2c2c2e; background: #161618; }
        """)
        self.stop_btn.clicked.connect(self._stop)
        lay.addWidget(self.stop_btn)

        # ── Status log ─────────────────────────────────────────────────────
        lay.addWidget(_sep())
        lay.addWidget(_section_lbl("STATUS LOG"))

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setMinimumHeight(180)
        self.log.setStyleSheet(f"""
            QTextEdit {{
                background: #1c1c1e; border: 1px solid #2c2c2e;
                border-radius: 8px; color: #30d158;
                font-family: 'Ubuntu Mono', monospace; font-size: 10px;
                padding: 8px;
            }}
        """)
        lay.addWidget(self.log)

        lay.addStretch()

        # ── Exposure score badge ───────────────────────────────────────────
        self.score_badge = QLabel("Exposure Score\n—")
        self.score_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_badge.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        self.score_badge.setFixedHeight(64)
        self.score_badge.setStyleSheet(
            "color: #3a3a3c; border: 1px solid #2c2c2e; "
            "border-radius: 10px; padding: 8px; background: #1c1c1e;"
        )
        self.score_badge.setWordWrap(True)
        lay.addWidget(self.score_badge)

        scroll.setWidget(inner)

        # Wrap scroll in panel
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(scroll)
        return panel

    # ── Right panel ────────────────────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #1c1c1e;")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Vertical splitter: tabs on top, detail panel on bottom
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setHandleWidth(1)
        vsplit.setStyleSheet("QSplitter::handle { background: #2c2c2e; }")
        outer.addWidget(vsplit)

        # ── Tabs ───────────────────────────────────────────────────────────
        tab_container = QWidget()
        tab_container.setStyleSheet("background: #1c1c1e;")
        tl = QVBoxLayout(tab_container)
        tl.setContentsMargins(16, 12, 16, 0)
        tl.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                border-top: 1px solid #38383a;
                background: #1c1c1e;
            }}
            QTabBar::tab {{
                background: transparent; color: #636366;
                border: none; border-bottom: 2px solid transparent;
                padding: 9px 18px; margin-right: 2px;
                font-size: 12px; font-weight: 500;
            }}
            QTabBar::tab:selected {{
                color: #f5f5f7; border-bottom: 2px solid {ACCENT};
            }}
            QTabBar::tab:hover:!selected {{
                color: #aeaeb2; border-bottom: 2px solid #3a3a3c;
            }}
        """)
        tl.addWidget(self.tabs)

        # Tab 1: All Results
        self.all_table = self._make_table(["Source", "Title", "Risk", "Snippet", "URL"])
        self.all_table.setColumnWidth(0, 130)
        self.all_table.setColumnWidth(2, 76)
        self.all_table.itemSelectionChanged.connect(
            lambda: self._show_detail_from(self.all_table)
        )
        self.all_table.doubleClicked.connect(
            lambda idx: self._open_url(self.all_table, idx.row(), 4)
        )
        self.all_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.all_table.customContextMenuRequested.connect(
            lambda pos: self._ctx_menu(self.all_table, pos, 4)
        )
        self.tabs.addTab(self.all_table, "🔍  All Results (0)")

        # Tab 2: High Risk
        self.high_table = self._make_table(["Source", "Title", "Snippet", "URL"])
        self.high_table.itemSelectionChanged.connect(
            lambda: self._show_detail_from(self.high_table, url_col=3)
        )
        self.high_table.doubleClicked.connect(
            lambda idx: self._open_url(self.high_table, idx.row(), 3)
        )
        self.high_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.high_table.customContextMenuRequested.connect(
            lambda pos: self._ctx_menu(self.high_table, pos, 3)
        )
        self.tabs.addTab(self.high_table, "🔴  High Risk (0)")

        # Tab 3: By Source
        self.source_table = self._make_table(["Source", "Count", "Status"])
        self.source_table.setColumnWidth(0, 200)
        self.source_table.setColumnWidth(1, 60)
        self._populate_source_table()
        self.tabs.addTab(self.source_table, "📡  Sources")

        # Tab 4: Exposure Report
        report_widget = QWidget()
        report_widget.setStyleSheet("background: #1c1c1e;")
        rl = QVBoxLayout(report_widget)
        rl.setContentsMargins(24, 20, 24, 20)

        self.report_lbl = QLabel("Run a scan to see the exposure report.")
        self.report_lbl.setWordWrap(True)
        self.report_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.report_lbl.setFont(QFont("Ubuntu", 11))
        self.report_lbl.setStyleSheet("color: #aeaeb2; border: none; background: transparent;")
        self.report_lbl.setTextFormat(Qt.TextFormat.RichText)
        rl.addWidget(self.report_lbl)
        rl.addStretch()
        self.tabs.addTab(report_widget, "📊  Exposure Report")

        vsplit.addWidget(tab_container)

        # ── Detail panel ───────────────────────────────────────────────────
        detail_frame = QFrame()
        detail_frame.setStyleSheet(
            "QFrame { background: #161618; border-top: 1px solid #2c2c2e; }"
        )
        detail_frame.setMinimumHeight(140)
        dl = QVBoxLayout(detail_frame)
        dl.setContentsMargins(20, 12, 20, 12)
        dl.setSpacing(6)

        detail_header = QHBoxLayout()
        detail_header.setSpacing(8)

        detail_title_lbl = QLabel("RESULT DETAIL")
        detail_title_lbl.setStyleSheet(
            "color: #3a3a3c; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1.2px; background: transparent;"
        )
        detail_header.addWidget(detail_title_lbl)
        detail_header.addStretch()

        self.open_btn = QPushButton("🌐  Open in Browser")
        self.open_btn.setFixedHeight(28)
        self.open_btn.setEnabled(False)
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}18; border: 1px solid {ACCENT}44;
                color: {ACCENT}; border-radius: 6px; padding: 2px 12px;
                font-weight: 600; font-size: 11px;
            }}
            QPushButton:hover {{ background: {ACCENT}30; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #3a3a3c; border-color: #2c2c2e; background: transparent; }}
        """)
        self.open_btn.clicked.connect(self._open_selected_url)
        detail_header.addWidget(self.open_btn)

        self.copy_url_btn = QPushButton("📋  Copy URL")
        self.copy_url_btn.setFixedHeight(28)
        self.copy_url_btn.setEnabled(False)
        self.copy_url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_url_btn.setStyleSheet("""
            QPushButton {
                background: #2c2c2e; border: 1px solid #38383a;
                color: #aeaeb2; border-radius: 6px; padding: 2px 12px;
                font-weight: 600; font-size: 11px;
            }
            QPushButton:hover { background: #3a3a3c; border-color: #48484a; }
            QPushButton:disabled { color: #3a3a3c; border-color: #2c2c2e; background: transparent; }
        """)
        self.copy_url_btn.clicked.connect(self._copy_selected_url)
        detail_header.addWidget(self.copy_url_btn)

        dl.addLayout(detail_header)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Ubuntu", 11))
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none;
                color: #aeaeb2; padding: 0;
            }
        """)
        self.detail_text.setPlaceholderText(
            "Select a result row above to see full details here…"
        )
        dl.addWidget(self.detail_text)

        vsplit.addWidget(detail_frame)
        vsplit.setSizes([500, 180])
        vsplit.setStretchFactor(0, 1)
        vsplit.setStretchFactor(1, 0)

        self._selected_url = ""
        return panel

    # ── Table factory ──────────────────────────────────────────────────────────

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        t.horizontalHeader().setSectionResizeMode(
            len(headers) - 1, QHeaderView.ResizeMode.Stretch
        )
        t.setAlternatingRowColors(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(True)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setStyleSheet("""
            QTableWidget {
                background: #1c1c1e; color: #aeaeb2;
                border: none; gridline-color: #2c2c2e;
            }
            QTableWidget::item { padding: 6px 10px; border: none; }
            QTableWidget::item:selected {
                background: #0a84ff18; color: #f5f5f7;
            }
            QHeaderView::section {
                background: #161618; color: #636366;
                border: none; border-bottom: 1px solid #2c2c2e;
                border-right: 1px solid #2c2c2e;
                padding: 7px 10px; font-size: 10px; font-weight: 700;
                text-transform: uppercase; letter-spacing: 0.5px;
            }
        """)
        return t

    # ── Source status table ────────────────────────────────────────────────────

    def _populate_source_table(self):
        self.source_table.setRowCount(0)
        for src, ico in SOURCE_ICONS.items():
            row = self.source_table.rowCount()
            self.source_table.insertRow(row)
            src_item = QTableWidgetItem(f"{ico}  {src}")
            src_item.setForeground(QColor("#aeaeb2"))
            self.source_table.setItem(row, 0, src_item)
            cnt_item = QTableWidgetItem("—")
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item.setForeground(QColor("#636366"))
            self.source_table.setItem(row, 1, cnt_item)
            status_item = QTableWidgetItem("pending")
            status_item.setForeground(QColor("#48484a"))
            self.source_table.setItem(row, 2, status_item)

    def _update_source_status(self, source: str, count: int, status: str):
        for row in range(self.source_table.rowCount()):
            cell = self.source_table.item(row, 0)
            if cell and source in cell.text():
                cnt_item = QTableWidgetItem(str(count) if count >= 0 else "—")
                cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cnt_item.setForeground(
                    QColor("#30d158") if count > 0 else QColor("#636366")
                )
                self.source_table.setItem(row, 1, cnt_item)

                colors = {
                    "ok":      "#30d158",
                    "error":   "#ff453a",
                    "skipped": "#48484a",
                    "running": "#ff9f0a",
                    "pending": "#48484a",
                }
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(colors.get(status, "#636366")))
                self.source_table.setItem(row, 2, status_item)
                break

    # ── Scan control ───────────────────────────────────────────────────────────

    def _start(self):
        query = self.query_input.text().strip()
        if not query:
            self.log.append("⚠️  Enter a search target first.")
            return

        # Prevent double-start (avoids GC crash from orphaned thread)
        if self._thread is not None and self._thread.isRunning():
            self.log.append("⚠️  Scan already in progress — click Stop first.")
            return

        # Save to history
        if query not in self._history:
            self._history.insert(0, query)
            self._history = self._history[:15]
            self.history_combo.clear()
            self.history_combo.addItems(self._history)

        enabled = [src for src, cb in self._src_checks.items() if cb.isChecked()]
        if not enabled:
            self.log.append("⚠️  Enable at least one source.")
            return

        query_type = self.type_combo.currentText().lower()
        self.log.clear()
        self.all_table.setRowCount(0)
        self.high_table.setRowCount(0)
        self._results.clear()
        self._selected_url = ""
        self.detail_text.clear()
        self.open_btn.setEnabled(False)
        self.copy_url_btn.setEnabled(False)
        self.report_lbl.setText("Scanning…")
        self._update_score_badge(None)
        self._populate_source_table()
        self.tabs.setCurrentIndex(0)

        for src in enabled:
            self._update_source_status(src, 0, "running")

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)

        self.log.append(f"🔍 [{query_type.upper()}]  {query}")
        self.log.append(f"   Sources: {', '.join(enabled)}")

        self._thread = DarkWebThread(query, query_type, enabled)
        # deleteLater prevents C++ QThread segfault when Python GC runs
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.progress.connect(self._on_log)
        self._thread.result_found.connect(self._on_result)
        self._thread.source_status.connect(self._update_source_status)
        self._thread.done.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"Dark web scan started: {query}")

    def _stop(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
        self.stop_btn.setEnabled(False)
        self.log.append("⏹  Stop requested…")

    def _on_log(self, msg: str):
        self.log.append(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Results ────────────────────────────────────────────────────────────────

    def _on_result(self, r: dict):
        self._results.append(r)
        risk     = r.get("risk_level", "low")
        color    = QColor(RISK_COLOR.get(risk, "#aeaeb2"))
        bg_hex   = RISK_BG.get(risk, "#1c1c1e")
        icon     = RISK_ICON.get(risk, "●")
        bg       = QColor(bg_hex)

        # ── All Results ────────────────────────────────────────────────────
        row = self.all_table.rowCount()
        self.all_table.insertRow(row)

        src_item = QTableWidgetItem(r.get("source", ""))
        src_item.setForeground(QColor(ACCENT))
        self.all_table.setItem(row, 0, src_item)

        self.all_table.setItem(row, 1, QTableWidgetItem(r.get("title", "")[:90]))

        risk_item = QTableWidgetItem(f"{icon} {risk.upper()}")
        risk_item.setForeground(color)
        risk_item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
        self.all_table.setItem(row, 2, risk_item)

        self.all_table.setItem(row, 3, QTableWidgetItem(r.get("snippet", "")[:90]))

        url_item = QTableWidgetItem(r.get("url", ""))
        url_item.setForeground(QColor("#0a84ff"))
        self.all_table.setItem(row, 4, url_item)

        for col in range(5):
            cell = self.all_table.item(row, col)
            if cell:
                cell.setBackground(bg)

        # ── High Risk tab ──────────────────────────────────────────────────
        if risk == "high":
            r2 = self.high_table.rowCount()
            self.high_table.insertRow(r2)

            si = QTableWidgetItem(r.get("source", ""))
            si.setForeground(QColor("#ff453a"))
            self.high_table.setItem(r2, 0, si)
            self.high_table.setItem(r2, 1, QTableWidgetItem(r.get("title", "")[:90]))
            self.high_table.setItem(r2, 2, QTableWidgetItem(r.get("snippet", "")[:90]))
            ui = QTableWidgetItem(r.get("url", ""))
            ui.setForeground(QColor("#0a84ff"))
            self.high_table.setItem(r2, 3, ui)
            bg2 = QColor("#2a0e0e")
            for col in range(4):
                cell = self.high_table.item(r2, col)
                if cell:
                    cell.setBackground(bg2)

        # Update tab labels
        total = self.all_table.rowCount()
        highs = self.high_table.rowCount()
        self.tabs.setTabText(0, f"🔍  All Results ({total})")
        self.tabs.setTabText(1, f"🔴  High Risk ({highs})")

    def _on_done(self, summary: dict):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(bool(self._results))

        total   = summary.get("total_found", 0)
        highs   = summary.get("high_risk", 0)
        meds    = summary.get("medium_risk", 0)
        lows    = summary.get("low_risk", 0)
        sources = summary.get("sources_checked", 0)
        score   = summary.get("exposure_score", 0)

        self._update_score_badge(score)
        self._build_report(summary)

        self.log.append(
            f"\n✅ Done — {total} result(s) / {sources} source(s)  |  Score: {score}"
        )
        self.status_message.emit(
            f"Dark web scan complete — {total} results, score {score}"
        )

        # Auto-jump to most interesting tab
        if highs > 0:
            self.tabs.setCurrentIndex(1)
        elif total > 0:
            self.tabs.setCurrentIndex(3)

    # ── Score badge ────────────────────────────────────────────────────────────

    def _update_score_badge(self, score):
        if score is None:
            self.score_badge.setText("Exposure Score\n—")
            self.score_badge.setStyleSheet(
                "color: #3a3a3c; border: 1px solid #2c2c2e; "
                "border-radius: 10px; padding: 8px; background: #1c1c1e;"
            )
            return

        if score >= 30:
            c = "#ff453a"
        elif score >= 10:
            c = "#ff9f0a"
        elif score > 0:
            c = "#ffd60a"
        else:
            c = "#30d158"

        self.score_badge.setText(f"Exposure Score\n{score}")
        self.score_badge.setStyleSheet(
            f"color: {c}; border: 1px solid {c}44; "
            f"border-radius: 10px; padding: 8px; background: {c}0d;"
        )

    # ── Exposure report ────────────────────────────────────────────────────────

    def _build_report(self, s: dict):
        total   = s.get("total_found", 0)
        highs   = s.get("high_risk", 0)
        meds    = s.get("medium_risk", 0)
        lows    = s.get("low_risk", 0)
        sources = s.get("sources_checked", 0)
        score   = s.get("exposure_score", 0)
        query   = s.get("query", "")
        qtype   = s.get("query_type", "")

        if score >= 30:
            color = "#ff453a"
            verdict = "CRITICAL EXPOSURE"
        elif score >= 10:
            color = "#ff9f0a"
            verdict = "MODERATE EXPOSURE"
        elif score > 0:
            color = "#ffd60a"
            verdict = "LOW EXPOSURE"
        else:
            color = "#30d158"
            verdict = "NO EXPOSURE FOUND"

        recs = []
        if highs > 0:
            recs.append("⛔ <b>Immediate action:</b> Change passwords for all exposed accounts, enable 2FA, and revoke any leaked API keys or tokens.")
        if meds > 0:
            recs.append("⚠️ <b>Review exposure:</b> Personal or account data found — consider privacy hardening and monitoring for misuse.")
        if score == 0:
            recs.append("✅ <b>No significant exposure</b> found in scanned sources. Continue monitoring periodically.")
        if highs == 0 and score > 0:
            recs.append("💡 <b>Monitor regularly:</b> Low-level exposure detected. Set up alerts for this target.")

        rec_html = "".join(
            f"<li style='margin:5px 0; color:#aeaeb2;'>{r}</li>"
            for r in recs
        )

        self.report_lbl.setText(f"""
<div style='font-family: Ubuntu, sans-serif;'>
<h2 style='color:{color}; margin:0 0 4px 0;'>{verdict}</h2>
<p style='color:#636366; margin:0 0 16px 0; font-size:12px;'>
  Target: <b style='color:#f5f5f7;'>{query}</b>
  &nbsp;·&nbsp; Type: {qtype}
</p>

<table style='border-collapse:collapse; font-size:13px; color:#aeaeb2; margin-bottom:16px;'>
  <tr>
    <td style='padding:4px 20px 4px 0;'>
      <span style='color:#ff453a;'>🔴</span> High Risk
    </td>
    <td><b style='color:#f5f5f7;'>{highs}</b> &nbsp;×&nbsp; 10 = <b style='color:#ff453a;'>{highs*10}</b> pts</td>
  </tr>
  <tr>
    <td style='padding:4px 20px 4px 0;'>
      <span style='color:#ff9f0a;'>🟡</span> Medium Risk
    </td>
    <td><b style='color:#f5f5f7;'>{meds}</b> &nbsp;×&nbsp; 5 = <b style='color:#ff9f0a;'>{meds*5}</b> pts</td>
  </tr>
  <tr>
    <td style='padding:4px 20px 4px 0;'>
      <span style='color:#30d158;'>🟢</span> Low Risk
    </td>
    <td><b style='color:#f5f5f7;'>{lows}</b> &nbsp;×&nbsp; 1 = <b style='color:#30d158;'>{lows}</b> pts</td>
  </tr>
  <tr>
    <td style='padding:8px 20px 4px 0; color:#636366;'>Sources checked</td>
    <td style='color:#f5f5f7;'>{sources}</td>
  </tr>
  <tr>
    <td style='padding:4px 20px 4px 0; color:#636366;'>Total results</td>
    <td style='color:#f5f5f7;'>{total}</td>
  </tr>
  <tr>
    <td style='padding:4px 20px 4px 0; color:#636366;'>Exposure score</td>
    <td><b style='color:{color}; font-size:15px;'>{score}</b></td>
  </tr>
</table>

<b style='color:#f5f5f7;'>Recommendations</b>
<ul style='padding-left:18px; margin-top:8px;'>{rec_html}</ul>
</div>
        """)

    # ── Detail panel ───────────────────────────────────────────────────────────

    def _show_detail_from(self, table: QTableWidget, url_col: int = 4):
        rows = table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()

        def cell(c):
            item = table.item(row, c)
            return item.text() if item else ""

        ncols = table.columnCount()
        if ncols == 5:  # all_table
            source  = cell(0)
            title   = cell(1)
            risk    = cell(2)
            snippet = cell(3)
            url     = cell(4)
        else:           # high_table (4 cols)
            source  = cell(0)
            title   = cell(1)
            snippet = cell(2)
            url     = cell(3)
            risk    = "🔴 HIGH"

        self._selected_url = url
        self.open_btn.setEnabled(bool(url and url.startswith("http")))
        self.copy_url_btn.setEnabled(bool(url))

        risk_color = RISK_COLOR.get(risk.lower().replace("🔴 ", "").replace("🟡 ", "").replace("🟢 ", ""), "#aeaeb2")

        html = (
            f"<b style='color:#f5f5f7;'>{title or '(no title)'}</b><br><br>"
            f"<span style='color:#636366;'>Source:</span> "
            f"<span style='color:{ACCENT};'>{source}</span> &nbsp;·&nbsp; "
            f"<span style='color:#636366;'>Risk:</span> "
            f"<span style='color:{risk_color};'>{risk}</span><br><br>"
        )
        if snippet:
            html += f"<span style='color:#636366;'>Preview:</span><br>"
            html += f"<span style='color:#aeaeb2;'>{snippet}</span><br><br>"
        if url:
            html += f"<span style='color:#636366;'>URL:</span> "
            html += f"<span style='color:#0a84ff;'>{url}</span>"

        self.detail_text.setHtml(html)

    def _open_selected_url(self):
        if self._selected_url and self._selected_url.startswith("http"):
            webbrowser.open(self._selected_url)

    def _copy_selected_url(self):
        if self._selected_url:
            QApplication.clipboard().setText(self._selected_url)

    def _open_url(self, table: QTableWidget, row: int, url_col: int):
        item = table.item(row, url_col)
        if item and item.text().startswith("http"):
            webbrowser.open(item.text())

    def _ctx_menu(self, table: QTableWidget, pos: QPoint, url_col: int):
        item = table.itemAt(pos)
        if not item:
            return
        row = item.row()
        url_item = table.item(row, url_col)
        url = url_item.text() if url_item else ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2c2c2e; border: 1px solid #38383a;
                border-radius: 8px; padding: 4px;
            }
            QMenu::item { padding: 7px 20px; color: #aeaeb2; border-radius: 5px; }
            QMenu::item:selected { background: #0a84ff22; color: #f5f5f7; }
        """)

        if url.startswith("http"):
            open_act = QAction("🌐  Open in Browser", self)
            open_act.triggered.connect(lambda: webbrowser.open(url))
            menu.addAction(open_act)

        copy_act = QAction("📋  Copy URL", self)
        copy_act.triggered.connect(lambda: QApplication.clipboard().setText(url))
        copy_act.setEnabled(bool(url))
        menu.addAction(copy_act)

        title_item = table.item(row, 1)
        if title_item:
            copy_title = QAction("📝  Copy Title", self)
            copy_title.triggered.connect(
                lambda: QApplication.clipboard().setText(title_item.text())
            )
            menu.addAction(copy_title)

        menu.exec(table.viewport().mapToGlobal(pos))

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export(self):
        if not self._results:
            return
        path, fmt = QFileDialog.getSaveFileName(
            self,
            "Export Dark Web Results",
            "darkweb_results",
            "CSV Files (*.csv);;JSON Files (*.json)",
        )
        if not path:
            return

        try:
            if path.endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self._results, f, indent=2, ensure_ascii=False)
            else:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    if self._results:
                        writer = csv.DictWriter(f, fieldnames=self._results[0].keys())
                        writer.writeheader()
                        writer.writerows(self._results)
            self.log.append(f"✅ Exported {len(self._results)} result(s) → {path}")
        except Exception as exc:
            self.log.append(f"⚠️  Export failed: {exc}")

    # ── Settings passthrough ───────────────────────────────────────────────────

    def apply_settings(self, s):
        pass
