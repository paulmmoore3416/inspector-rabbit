"""
Inspector Rabbit - Dark Web Search Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFrame, QSplitter, QTextEdit, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QClipboard

from ..modules.dark_web_engine import DarkWebThread
from .components import apply_page_header_style


class DarkWebWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._all_results = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== Top Bar =====
        topbar = self._build_topbar()
        layout.addWidget(topbar)

        # ===== Main Splitter =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        # Left: Controls
        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)

        # Right: Results
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 900])

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        apply_page_header_style(bar, "#7c3aed") # Purple accent
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        icon = QLabel("🕵️‍♂️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)
        t1 = QLabel("Dark Web Search")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Search onion services via public gateways")
        t2.setFont(QFont("Ubuntu", 11))
        t2.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        title_layout.addWidget(t1)
        title_layout.addWidget(t2)
        layout.addLayout(title_layout)
        layout.addStretch()

        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setStyleSheet("background: #0d1117; border-right: 1px solid #21262d;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("SEARCH QUERY"))
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("e.g. market, bitcoin, forum...")
        self.query_input.returnPressed.connect(self._on_search_clicked)
        layout.addWidget(self.query_input)

        self.search_btn = QPushButton("Start Deep Search")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_btn)

        layout.addSpacing(10)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        layout.addStretch()

        # Info card
        info = QFrame()
        info.setObjectName("card")
        info_layout = QVBoxLayout(info)
        info_label = QLabel(
            "Note: This module uses public gateways (Ahmia, Phobos) "
            "to search the Tor network without requiring a Tor proxy locally."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        info_layout.addWidget(info_label)
        layout.addWidget(info)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Title", "Onion Address", "Source"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_table)

        # Detail area
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("Select a result to view details...")
        self.detail_text.setMaximumHeight(150)
        self.detail_text.setStyleSheet("background: #0a0f16; border-top: 1px solid #21262d;")
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.detail_text)

        return panel

    def _on_search_clicked(self):
        query = self.query_input.text().strip()
        if not query:
            return

        self._all_results = []
        self.results_table.setRowCount(0)
        self.detail_text.clear()
        
        self.search_btn.setEnabled(False)
        self.progress.show()
        self.status_message.emit(f"Searching Dark Web for: {query}...")

        self._thread = DarkWebThread(query)
        self._thread.finished.connect(self._on_search_finished)
        self._thread.error.connect(self._on_search_error)
        self._thread.start()

    def _on_search_finished(self, results):
        self.search_btn.setEnabled(True)
        self.progress.hide()
        self._all_results = results
        
        self.results_table.setRowCount(len(results))
        for i, res in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(res["title"]))
            self.results_table.setItem(i, 1, QTableWidgetItem(res["onion"]))
            self.results_table.setItem(i, 2, QTableWidgetItem(res["source"]))
        
        self.status_message.emit(f"Dark Web search complete. Found {len(results)} results.")

    def _on_search_error(self, err):
        self.search_btn.setEnabled(True)
        self.progress.hide()
        self.status_message.emit(f"Error searching Dark Web: {err}")

    def _on_selection_changed(self):
        row = self.results_table.currentRow()
        if 0 <= row < len(self._all_results):
            res = self._all_results[row]
            text = f"TITLE: {res['title']}\n"
            text += f"ONION: {res['onion']}\n"
            text += f"SOURCE: {res['source']}\n\n"
            text += f"SNIPPET:\n{res['snippet']}"
            self.detail_text.setText(text)

    def _on_item_double_clicked(self, item):
        row = item.row()
        if 0 <= row < len(self._all_results):
            onion = self._all_results[row]["onion"]
            QApplication.clipboard().setText(onion)
            self.status_message.emit(f"Copied {onion} to clipboard.")
