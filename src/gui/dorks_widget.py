"""
Inspector Rabbit - Google Dorks Widget
"""

import json
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QTreeWidget,
    QTreeWidgetItem, QComboBox, QCheckBox, QScrollArea,
    QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

from ..modules.dorks_engine import (
    load_dork_templates, build_dork_query, DorkWorker,
    generate_dork_queries, get_google_url
)
from .components import apply_page_header_style


class DorksWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._all_results = []
        self._setup_ui()
        self._load_templates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Topbar
        bar = QFrame()
        apply_page_header_style(bar, "#fb923c")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("🔍")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Google Dorks Engine")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("60+ dork templates · Live search · DuckDuckGo / Bing / Google links")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # Left: template library
        left = self._build_left_panel()
        splitter.addWidget(left)

        # Right: search + results
        right = self._build_right_panel()
        splitter.addWidget(right)

        splitter.setSizes([350, 850])

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet("QFrame { background: #010409; border-bottom: 1px solid #21262d; }")
        hdr.setFixedHeight(48)
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(16, 8, 16, 8)
        lbl = QLabel("DORK LIBRARY")
        lbl.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        hdr_layout.addWidget(lbl)
        hdr_layout.addStretch()
        layout.addWidget(hdr)

        # Template tree
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderHidden(True)
        self.template_tree.setStyleSheet("""
            QTreeWidget {
                background: #010409;
                border: none;
                color: #c9d1d9;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 6px 8px;
            }
            QTreeWidget::item:selected {
                background: #1f3a5f;
            }
            QTreeWidget::item:hover {
                background: #161b22;
            }
        """)
        self.template_tree.itemClicked.connect(self._on_template_selected)
        layout.addWidget(self.template_tree, 1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Target + search row
        target_row = QHBoxLayout()

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Target domain, name, or keyword...")
        self.target_input.setFixedHeight(42)
        self.target_input.setFont(QFont("Ubuntu", 13))
        target_row.addWidget(self.target_input, 1)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["DuckDuckGo", "Bing"])
        self.engine_combo.setFixedHeight(42)
        self.engine_combo.setFixedWidth(130)
        target_row.addWidget(self.engine_combo)

        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.setFixedHeight(42)
        self.search_btn.setFixedWidth(110)
        self.search_btn.clicked.connect(self._run_search)
        target_row.addWidget(self.search_btn)

        self.stop_btn = QPushButton("⛔")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(42)
        self.stop_btn.setFixedWidth(48)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_search)
        target_row.addWidget(self.stop_btn)

        layout.addLayout(target_row)

        # Custom dork row
        custom_row = QHBoxLayout()
        self.custom_dork = QLineEdit()
        self.custom_dork.setPlaceholderText("Custom dork: site:{target} filetype:pdf (use {target} for replacement)...")
        self.custom_dork.setFixedHeight(38)
        custom_row.addWidget(self.custom_dork, 1)

        run_custom_btn = QPushButton("▶ Run Custom")
        run_custom_btn.setFixedHeight(38)
        run_custom_btn.clicked.connect(self._run_custom_dork)
        custom_row.addWidget(run_custom_btn)

        open_google_btn = QPushButton("🌐 Open in Google")
        open_google_btn.setFixedHeight(38)
        open_google_btn.clicked.connect(self._open_in_google)
        custom_row.addWidget(open_google_btn)
        layout.addLayout(custom_row)

        # Selected template info
        self.template_info = QFrame()
        self.template_info.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 10px;
            }
        """)
        self.template_info.setFixedHeight(70)
        info_layout = QHBoxLayout(self.template_info)
        info_layout.setContentsMargins(16, 10, 16, 10)
        self.template_name_lbl = QLabel("Select a dork template from the library →")
        self.template_name_lbl.setStyleSheet("color: #8b949e; font-size: 12px; border: none; background: transparent;")
        info_layout.addWidget(self.template_name_lbl, 1)
        layout.addWidget(self.template_info)

        # Status log
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setFixedHeight(60)
        self.status_log.setFont(QFont("Ubuntu Mono", 10))
        self.status_log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 6px;
                color: #3fb950;
                font-size: 11px;
                font-family: 'Ubuntu Mono', monospace;
            }
        """)
        layout.addWidget(self.status_log)

        # Results tabs
        self.results_tabs = QTabWidget()
        layout.addWidget(self.results_tabs, 1)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["Query", "Title", "URL", "Snippet", "Engine"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.doubleClicked.connect(self._open_result_url)
        self.results_tabs.addTab(self.results_table, "🔍 Search Results")

        # Google Links tab
        self.google_links = QTextEdit()
        self.google_links.setReadOnly(True)
        self.google_links.setStyleSheet("QTextEdit { background: #0d1117; border: none; padding: 12px; }")
        self.results_tabs.addTab(self.google_links, "🌐 Google Links")

        # Run All tab
        self.run_all_widget = self._build_run_all_tab()
        self.results_tabs.addTab(self.run_all_widget, "⚡ Bulk Search")

        return panel

    def _build_run_all_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel(
            "Bulk search runs all selected dork templates against the target.\n"
            "Results are shown in the Search Results tab."
        )
        info.setStyleSheet("color: #8b949e; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.bulk_target = QLineEdit()
        self.bulk_target.setPlaceholderText("Target for bulk search...")
        self.bulk_target.setFixedHeight(40)
        layout.addWidget(self.bulk_target)

        row = QHBoxLayout()
        self.bulk_category = QComboBox()
        self.bulk_category.addItem("All Categories")
        row.addWidget(self.bulk_category)

        bulk_btn = QPushButton("⚡ Run Bulk Search")
        bulk_btn.setObjectName("primaryBtn")
        bulk_btn.setFixedHeight(40)
        bulk_btn.clicked.connect(self._run_bulk_search)
        row.addWidget(bulk_btn)
        layout.addLayout(row)

        self.bulk_progress = QTextEdit()
        self.bulk_progress.setReadOnly(True)
        self.bulk_progress.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 6px;
                color: #3fb950;
                font-size: 11px;
                font-family: 'Ubuntu Mono', monospace;
            }
        """)
        layout.addWidget(self.bulk_progress, 1)

        return w

    def _load_templates(self):
        templates = load_dork_templates()
        self.template_tree.clear()
        self._template_map = {}

        for cat_key, cat_data in templates.get('categories', {}).items():
            cat_item = QTreeWidgetItem([f"  {cat_data.get('name', cat_key)}"])
            cat_item.setFont(0, QFont("Ubuntu", 11, QFont.Weight.Bold))
            cat_item.setForeground(0, QColor("#00f5ff"))
            cat_item.setData(0, Qt.ItemDataRole.UserRole, None)

            for tmpl in cat_data.get('templates', []):
                tmpl_item = QTreeWidgetItem([f"   {tmpl['name']}"])
                tmpl_item.setForeground(0, QColor("#c9d1d9"))
                tmpl_item.setData(0, Qt.ItemDataRole.UserRole, tmpl)
                cat_item.addChild(tmpl_item)
                self._template_map[tmpl['name']] = tmpl

            self.template_tree.addTopLevelItem(cat_item)

        self.template_tree.expandAll()

        # Populate bulk category
        if hasattr(self, 'bulk_category'):
            self.bulk_category.clear()
            self.bulk_category.addItem("All Categories")
            for cat_key, cat_data in templates.get('categories', {}).items():
                self.bulk_category.addItem(cat_data.get('name', cat_key))

    def _on_template_selected(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        self.template_name_lbl.setText(
            f"<b style='color:#00f5ff;'>{data['name']}</b> — "
            f"<span style='color:#8b949e;'>{data.get('description', '')}</span>  "
            f"<span style='color:#484f58;'>{data['template']}</span>"
        )
        # Pre-fill custom dork
        self.custom_dork.setText(data['template'])

    def _run_search(self):
        target = self.target_input.text().strip()
        dork_template = self.custom_dork.text().strip()
        if not target:
            self.status_log.append("⚠️  Enter a target")
            return
        if not dork_template:
            self.status_log.append("⚠️  Select or enter a dork template")
            return

        query = build_dork_query(dork_template, target)
        self._execute_queries([query])

    def _run_custom_dork(self):
        target = self.target_input.text().strip()
        dork = self.custom_dork.text().strip()
        if not dork:
            self.status_log.append("⚠️  Enter a custom dork")
            return
        query = build_dork_query(dork, target) if target else dork
        self._execute_queries([query])

    def _run_bulk_search(self):
        target = self.bulk_target.text().strip() or self.target_input.text().strip()
        if not target:
            self.bulk_progress.append("⚠️  Enter a target")
            return

        queries_data = generate_dork_queries(target)
        queries = [q['query'] for q in queries_data]

        self.bulk_progress.append(f"⚡ Running {len(queries)} dork queries for: {target}")
        self._execute_queries(queries, bulk_mode=True)

    def _execute_queries(self, queries: list, bulk_mode: bool = False):
        engine = self.engine_combo.currentText().lower()

        self._worker = DorkWorker(queries, engine=engine, max_results=10, delay=2.0)
        self._worker.result_ready.connect(lambda r: self._on_result(r, bulk_mode))
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self.search_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_log.append(f"🔍 Executing {len(queries)} query/queries via {engine}...")
        self.status_message.emit(f"Running dork search via {engine}...")

        # Add Google links
        google_html = "<div style='padding:12px;'>"
        google_html += "<h3 style='color:#00f5ff; margin-bottom:12px;'>Open in Google</h3>"
        for q in queries[:30]:
            url = get_google_url(q)
            google_html += f"<div style='margin-bottom:8px;'>"
            google_html += f"<a href='{url}' style='color:#58a6ff; font-size:11px; font-family:monospace;'>{q[:100]}</a>"
            google_html += "</div>"
        google_html += "</div>"
        self.google_links.setHtml(google_html)

    def _on_result(self, result, bulk_mode=False):
        for item in result.results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            query_item = QTableWidgetItem(result.query[:60])
            query_item.setForeground(QColor("#8b949e"))
            query_item.setFont(QFont("Ubuntu Mono", 9))
            self.results_table.setItem(row, 0, query_item)

            title_item = QTableWidgetItem(item.get('title', '')[:60])
            title_item.setForeground(QColor("#c9d1d9"))
            self.results_table.setItem(row, 1, title_item)

            url_item = QTableWidgetItem(item.get('url', ''))
            url_item.setForeground(QColor("#58a6ff"))
            self.results_table.setItem(row, 2, url_item)

            snip_item = QTableWidgetItem(item.get('snippet', '')[:80])
            snip_item.setForeground(QColor("#8b949e"))
            self.results_table.setItem(row, 3, snip_item)

            eng_item = QTableWidgetItem(result.engine)
            eng_item.setForeground(QColor("#a78bfa"))
            self.results_table.setItem(row, 4, eng_item)

        if bulk_mode:
            self.bulk_progress.append(
                f"  ✅ {result.engine}: '{result.query[:50]}' → {result.total_found} results"
            )

    def _on_progress(self, msg: str):
        self.status_log.append(f"  ↳ {msg}")
        if hasattr(self, 'bulk_progress'):
            self.bulk_progress.append(f"  ↳ {msg}")

    def _on_finished(self):
        total = self.results_table.rowCount()
        self.status_log.append(f"✅ Complete! {total} results found")
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_message.emit(f"Dork search complete: {total} results")
        self.results_tabs.setCurrentIndex(0)

    def _stop_search(self):
        if self._worker:
            self._worker.stop()
            self.status_log.append("⛔ Stopped")
            self.search_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _open_result_url(self, index):
        row = index.row()
        url_item = self.results_table.item(row, 2)
        if url_item:
            url = url_item.text()
            if url.startswith('http'):
                QDesktopServices.openUrl(QUrl(url))

    def _open_in_google(self):
        target = self.target_input.text().strip()
        dork = self.custom_dork.text().strip()
        if not dork:
            return
        query = build_dork_query(dork, target) if target else dork
        url = get_google_url(query)
        QDesktopServices.openUrl(QUrl(url))
