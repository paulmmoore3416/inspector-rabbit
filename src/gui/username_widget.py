"""
Inspector Rabbit - Username Search Widget
"""

import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFrame, QComboBox, QCheckBox, QGroupBox,
    QSplitter, QTextEdit, QScrollArea, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices, QClipboard

from ..modules.username_checker import UsernameCheckerThread, load_sites, get_categories
from ..modules.report_generator import generate_username_report, save_html_report, save_json_report
from .components import apply_page_header_style


STATUS_COLORS = {
    "FOUND":     ("#3fb950", "#1a3a2a"),
    "NOT FOUND": ("#8b949e", "#21262d"),
    "ERROR":     ("#f85149", "#2a1515"),
    "TIMEOUT":   ("#e3b341", "#2a2010"),
}


def _colored_item(text: str, fg: str, bg: str = None) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(QColor(fg))
    if bg:
        item.setBackground(QColor(bg))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class UsernameWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._all_results = []
        self._settings = {}
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
        apply_page_header_style(bar, "#00f5ff")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        icon = QLabel("👤")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)
        t1 = QLabel("Username Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Hunt usernames across 100+ social platforms")
        t2.setFont(QFont("Ubuntu", 11))
        t2.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        title_layout.addWidget(t1)
        title_layout.addWidget(t2)
        layout.addLayout(title_layout)
        layout.addStretch()

        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("""
            QFrame {
                background: #010409;
                border-right: 1px solid #21262d;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(16)

        # Username input
        self._lbl_section("TARGET", layout)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username to hunt...")
        self.username_input.setFixedHeight(42)
        self.username_input.setFont(QFont("Ubuntu", 13))
        self.username_input.returnPressed.connect(self._start_search)
        layout.addWidget(self.username_input)

        # Start button
        self.start_btn = QPushButton("🔍  Hunt Username")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.start_btn.clicked.connect(self._start_search)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⛔  Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.clicked.connect(self._stop_search)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        # Separator
        layout.addWidget(self._sep())

        # Category filter
        self._lbl_section("FILTER BY CATEGORY", layout)
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        for cat in get_categories():
            self.category_combo.addItem(cat.capitalize())
        layout.addWidget(self.category_combo)

        # Options
        self._lbl_section("OPTIONS", layout)

        self.show_found_only = QCheckBox("Show found only")
        self.show_found_only.setChecked(False)
        self.show_found_only.stateChanged.connect(self._filter_results)
        layout.addWidget(self.show_found_only)

        self.auto_graph = QCheckBox("Auto-add found to graph")
        self.auto_graph.setChecked(True)
        layout.addWidget(self.auto_graph)

        # Threads
        layout.addWidget(self._sep())
        self._lbl_section("THREADS", layout)
        threads_row = QHBoxLayout()
        self.threads_input = QLineEdit("20")
        self.threads_input.setFixedWidth(60)
        self.threads_input.setFixedHeight(32)
        threads_lbl = QLabel("concurrent requests")
        threads_lbl.setStyleSheet("color: #8b949e;")
        threads_row.addWidget(self.threads_input)
        threads_row.addWidget(threads_lbl)
        threads_row.addStretch()
        layout.addLayout(threads_row)

        # Progress
        layout.addWidget(self._sep())
        self._lbl_section("PROGRESS", layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Idle")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.progress_label)

        # Stats
        layout.addWidget(self._sep())
        self._lbl_section("LIVE STATS", layout)

        self.stat_found = QLabel("Found: 0")
        self.stat_found.setStyleSheet("color: #3fb950; font-weight: 700; font-size: 14px;")
        layout.addWidget(self.stat_found)

        self.stat_checked = QLabel("Checked: 0")
        self.stat_checked.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.stat_checked)

        layout.addStretch()

        # Export
        layout.addWidget(self._sep())
        export_btn = QPushButton("📄 Export HTML Report")
        export_btn.setFixedHeight(36)
        export_btn.clicked.connect(self._export_html)
        layout.addWidget(export_btn)

        json_btn = QPushButton("💾 Export JSON")
        json_btn.setFixedHeight(36)
        json_btn.clicked.connect(self._export_json)
        layout.addWidget(json_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Filter row
        filter_row = QHBoxLayout()

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("🔎 Filter results...")
        self.filter_input.setFixedHeight(36)
        self.filter_input.textChanged.connect(self._filter_results)
        filter_row.addWidget(self.filter_input, 1)

        copy_btn = QPushButton("📋 Copy Found URLs")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(self._copy_found_urls)
        filter_row.addWidget(copy_btn)

        graph_all_btn = QPushButton("🕸️ Send All to Graph")
        graph_all_btn.setFixedHeight(36)
        graph_all_btn.clicked.connect(self._send_all_to_graph)
        filter_row.addWidget(graph_all_btn)

        layout.addLayout(filter_row)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Platform", "Category", "Status", "Profile URL", "Response (ms)", "Error"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_url)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table, 1)

        # Status log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        self.log.setFont(QFont("Monospace", 10))
        self.log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: #3fb950;
                font-family: 'Ubuntu Mono', 'Monospace';
                font-size: 11px;
            }
        """)
        self.log.setPlaceholderText("// Activity log will appear here...")
        layout.addWidget(self.log)

        return panel

    def _lbl_section(self, text: str, layout):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #484f58; letter-spacing: 1px; font-size: 10px; font-weight: 700;")
        layout.addWidget(lbl)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _start_search(self):
        username = self.username_input.text().strip()
        if not username:
            self.log.append("⚠️  Please enter a username")
            return

        if self._thread and self._thread.isRunning():
            return

        self._all_results = []
        self.table.setRowCount(0)
        self.stat_found.setText("Found: 0")
        self.stat_checked.setText("Checked: 0")
        self.progress_bar.setValue(0)
        self.log.clear()
        self.log.append(f"🐇 Hunting username: '{username}' across 100+ platforms...")

        try:
            threads = int(self.threads_input.text())
        except ValueError:
            threads = 20

        self._thread = UsernameCheckerThread(username, max_threads=threads)
        self._thread.result_ready.connect(self._on_result)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_message.emit(f"Hunting @{username}...")

    def _stop_search(self):
        if self._thread:
            self._thread.stop()
            self.log.append("⛔  Search stopped by user")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_result(self, result):
        self._all_results.append(result)

        # Determine display
        filter_text = self.filter_input.text().lower()
        if self.show_found_only.isChecked() and not result.found:
            return
        if filter_text and filter_text not in result.site.lower() and filter_text not in result.url.lower():
            return

        self._add_table_row(result)

        # Auto-add found to graph
        if result.found and self.auto_graph.isChecked():
            self.send_to_graph.emit({
                'type': 'social',
                'id': f"social_{result.site}_{result.username}",
                'label': f"{result.site}\n@{result.username}",
                'url': result.url,
                'platform': result.site,
                'username': result.username,
            })

        # Log found ones
        if result.found:
            self.log.append(f"✅ FOUND: {result.site} — {result.url}")

    def _add_table_row(self, result):
        row = self.table.rowCount()
        self.table.insertRow(row)

        if result.found:
            status, fg, bg = "FOUND", "#3fb950", "#1a3a2a"
        elif result.error:
            status = result.error[:20]
            fg, bg = "#e3b341", "#2a2010"
        else:
            status, fg, bg = "NOT FOUND", "#484f58", None

        items = [
            QTableWidgetItem(result.site),
            QTableWidgetItem(result.category.capitalize()),
            _colored_item(status, fg, bg),
            QTableWidgetItem(result.url),
            QTableWidgetItem(str(result.response_time) if result.response_time else ""),
            QTableWidgetItem(result.error[:40] if result.error else ""),
        ]

        for col, item in enumerate(items):
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col == 3 and result.found:
                item.setForeground(QColor("#58a6ff"))
            self.table.setItem(row, col, item)

    def _on_progress(self, current: int, total: int):
        pct = int(current * 100 / total) if total else 0
        self.progress_bar.setValue(pct)
        self.progress_label.setText(f"{current}/{total} checked")
        self.stat_checked.setText(f"Checked: {current}")
        found_count = sum(1 for r in self._all_results if r.found)
        self.stat_found.setText(f"Found: {found_count}")

    def _on_finished(self, results):
        found = sum(1 for r in results if r.found)
        total = len(results)
        self.log.append(f"\n🏁 Complete! {found}/{total} profiles found.")
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Done — {found} found")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_message.emit(f"Username search complete: {found} profiles found")

    def _on_error(self, error: str):
        self.log.append(f"❌ Error: {error}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _filter_results(self):
        filter_text = self.filter_input.text().lower()
        found_only = self.show_found_only.isChecked()
        self.table.setRowCount(0)
        for result in self._all_results:
            if found_only and not result.found:
                continue
            if filter_text and filter_text not in result.site.lower() and filter_text not in result.url.lower():
                continue
            self._add_table_row(result)

    def _open_url(self, index):
        row = index.row()
        url_item = self.table.item(row, 3)
        if url_item:
            url = url_item.text()
            if url.startswith('http'):
                QDesktopServices.openUrl(QUrl(url))

    def _copy_found_urls(self):
        urls = []
        for r in self._all_results:
            if r.found:
                urls.append(r.url)
        if urls:
            QApplication.clipboard().setText('\n'.join(urls))
            self.log.append(f"📋 Copied {len(urls)} URLs to clipboard")

    def _send_all_to_graph(self):
        found = [r for r in self._all_results if r.found]
        for r in found:
            self.send_to_graph.emit({
                'type': 'social',
                'id': f"social_{r.site}_{r.username}",
                'label': f"{r.site}\n@{r.username}",
                'url': r.url,
                'platform': r.site,
                'username': r.username,
            })
        self.log.append(f"🕸️ Sent {len(found)} profiles to graph")

    def _export_html(self):
        if not self._all_results:
            self.log.append("⚠️  No results to export")
            return
        username = self.username_input.text().strip() or "unknown"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML Report",
            f"{username}_osint_report.html", "HTML (*.html)"
        )
        if path:
            html = generate_username_report(username, self._all_results)
            save_html_report(html, path)
            self.log.append(f"📄 Report saved: {path}")

    def _export_json(self):
        if not self._all_results:
            return
        username = self.username_input.text().strip() or "unknown"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", f"{username}_results.json", "JSON (*.json)"
        )
        if path:
            data = [r.__dict__ for r in self._all_results]
            save_json_report(data, path)
            self.log.append(f"💾 JSON saved: {path}")

    def apply_settings(self, settings: dict):
        self._settings = settings
