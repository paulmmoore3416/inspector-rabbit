"""
Inspector Rabbit - Domain Intelligence Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QTextEdit, QCheckBox, QTreeWidget,
    QTreeWidgetItem, QSplitter, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

from ..modules.domain_intel import DomainIntelThread
from ..modules.report_generator import generate_domain_report, save_html_report, save_json_report
from .components import apply_page_header_style


class DomainWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._result = None
        self._settings = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        topbar = self._build_topbar()
        layout.addWidget(topbar)

        # Content
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        layout.addLayout(content_layout, 1)

        # Left panel
        left = self._build_left_panel()
        content_layout.addWidget(left)

        # Right panel with tabs
        right = self._build_right_panel()
        content_layout.addWidget(right, 1)

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        apply_page_header_style(bar, "#a78bfa")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        QLabel("🌐").setFont(QFont("Ubuntu", 22))
        icon = QLabel("🌐")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(0)
        t1 = QLabel("Domain Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("WHOIS · DNS · SSL · Subdomains · Shodan · Technologies")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        layout.addLayout(vl)
        layout.addStretch()
        return bar

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)

        self._section_lbl("TARGET DOMAIN", layout)
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        self.domain_input.setFixedHeight(42)
        self.domain_input.setFont(QFont("Ubuntu", 12))
        self.domain_input.returnPressed.connect(self._start_lookup)
        layout.addWidget(self.domain_input)

        self.lookup_btn = QPushButton("🔍  Analyze Domain")
        self.lookup_btn.setObjectName("primaryBtn")
        self.lookup_btn.setFixedHeight(42)
        self.lookup_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.lookup_btn.clicked.connect(self._start_lookup)
        layout.addWidget(self.lookup_btn)

        self.stop_btn = QPushButton("⛔  Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.clicked.connect(self._stop_lookup)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        layout.addWidget(self._sep())
        self._section_lbl("OPTIONS", layout)

        self.do_subdomains = QCheckBox("Enumerate subdomains")
        self.do_subdomains.setChecked(True)
        layout.addWidget(self.do_subdomains)

        self.do_shodan = QCheckBox("Shodan lookup")
        self.do_shodan.setChecked(False)
        layout.addWidget(self.do_shodan)

        layout.addWidget(self._sep())
        self._section_lbl("STATUS", layout)
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
        self.status_log.setMinimumHeight(150)
        layout.addWidget(self.status_log)

        layout.addStretch()
        layout.addWidget(self._sep())

        export_btn = QPushButton("📄 Export HTML")
        export_btn.setFixedHeight(36)
        export_btn.clicked.connect(self._export_html)
        layout.addWidget(export_btn)

        json_btn = QPushButton("💾 Export JSON")
        json_btn.setFixedHeight(36)
        json_btn.clicked.connect(self._export_json)
        layout.addWidget(json_btn)

        graph_btn = QPushButton("🕸️ Send to Graph")
        graph_btn.setFixedHeight(36)
        graph_btn.clicked.connect(self._send_to_graph)
        layout.addWidget(graph_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)

        # WHOIS tab
        self.whois_tree = QTreeWidget()
        self.whois_tree.setHeaderLabels(["Field", "Value"])
        self.whois_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.whois_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.whois_tree, "📋 WHOIS")

        # DNS tab
        self.dns_table = self._make_table(["Type", "Value", "TTL"])
        self.tabs.addTab(self.dns_table, "📡 DNS Records")

        # SSL tab
        self.ssl_tree = QTreeWidget()
        self.ssl_tree.setHeaderLabels(["Field", "Value"])
        self.ssl_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ssl_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.ssl_tree, "🔒 SSL/TLS")

        # Headers tab
        self.headers_table = self._make_table(["Header", "Value"])
        self.tabs.addTab(self.headers_table, "🔤 HTTP Headers")

        # Subdomains tab
        self.subdomain_table = self._make_table(["Subdomain"])
        self.tabs.addTab(self.subdomain_table, "🌿 Subdomains")

        # Technologies tab
        self.tech_widget = QTextEdit()
        self.tech_widget.setReadOnly(True)
        self.tech_widget.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: none;
                color: #c9d1d9;
                padding: 12px;
            }
        """)
        self.tabs.addTab(self.tech_widget, "⚙️ Technologies")

        # Shodan tab
        self.shodan_tree = QTreeWidget()
        self.shodan_tree.setHeaderLabels(["Field", "Value"])
        self.shodan_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.shodan_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.shodan_tree, "🛰️ Shodan")

        # Robots tab
        self.robots_text = QTextEdit()
        self.robots_text.setReadOnly(True)
        self.robots_text.setFont(QFont("Ubuntu Mono", 10))
        self.robots_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: none;
                color: #c9d1d9;
                padding: 12px;
                font-family: 'Ubuntu Mono', monospace;
            }
        """)
        self.tabs.addTab(self.robots_text, "🤖 Robots.txt")

        # History tab
        self.history_table = self._make_table(["IP Address", "Location", "Owner", "Last Checked"])
        self.tabs.addTab(self.history_table, "📅 History")

        return panel

    def _make_table(self, headers) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return t

    def _section_lbl(self, text: str, layout):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(lbl)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _start_lookup(self):
        domain = self.domain_input.text().strip()
        if not domain:
            self.status_log.append("⚠️  Enter a domain name")
            return

        self._clear_results()
        self.status_log.clear()
        self.status_log.append(f"🐇 Starting domain intelligence for: {domain}")

        shodan_key = self._settings.get('shodan_api_key', '')
        do_sub = self.do_subdomains.isChecked()
        do_shodan = self.do_shodan.isChecked() and bool(shodan_key)

        self._thread = DomainIntelThread(domain, shodan_key if do_shodan else "", do_sub)
        self._thread.progress.connect(lambda m: self.status_log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.error.connect(self._on_error)
        self._thread.start()

        self.lookup_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_message.emit(f"Analyzing {domain}...")

    def _stop_lookup(self):
        if self._thread and self._thread.isRunning():
            self._thread.terminate()
            self.status_log.append("⛔  Stopped")
            self.lookup_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _clear_results(self):
        self.whois_tree.clear()
        self.dns_table.setRowCount(0)
        self.ssl_tree.clear()
        self.headers_table.setRowCount(0)
        self.subdomain_table.setRowCount(0)
        self.tech_widget.clear()
        self.shodan_tree.clear()
        self.robots_text.clear()
        self.history_table.setRowCount(0)

    def _on_result(self, result):
        self._result = result
        self.lookup_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_log.append("\n✅ Domain intelligence complete!")

        # WHOIS
        if result.whois and not result.whois.error:
            w = result.whois
            pairs = [
                ("Registrar", w.registrar),
                ("Created", w.creation_date),
                ("Expires", w.expiration_date),
                ("Updated", w.updated_date),
                ("Registrant", w.registrant_name),
                ("Organization", w.registrant_org),
                ("Email", w.registrant_email),
                ("Country", w.registrant_country),
            ]
            for field, value in pairs:
                if value:
                    item = QTreeWidgetItem([field, str(value)[:200]])
                    self.whois_tree.addTopLevelItem(item)
            ns_item = QTreeWidgetItem(["Name Servers", ""])
            for ns in w.name_servers:
                ns_item.addChild(QTreeWidgetItem(["", ns]))
            self.whois_tree.addTopLevelItem(ns_item)
            self.whois_tree.expandAll()
            self.tabs.setCurrentIndex(0)

        # DNS
        for record in result.dns_records:
            row = self.dns_table.rowCount()
            self.dns_table.insertRow(row)
            type_item = QTableWidgetItem(record.record_type)
            type_item.setForeground(QColor("#00f5ff"))
            type_item.setFont(QFont("Ubuntu Mono", 10, QFont.Weight.Bold))
            self.dns_table.setItem(row, 0, type_item)
            self.dns_table.setItem(row, 1, QTableWidgetItem(record.value))
            self.dns_table.setItem(row, 2, QTableWidgetItem(str(record.ttl)))

        # SSL
        if result.ssl_info and not result.ssl_info.error:
            s = result.ssl_info
            pairs = [
                ("Subject", str(s.subject)),
                ("Issuer", str(s.issuer)),
                ("Version", str(s.version)),
                ("Valid From", s.not_before),
                ("Valid Until", s.not_after),
                ("Serial", s.serial_number),
            ]
            for field, value in pairs:
                self.ssl_tree.addTopLevelItem(QTreeWidgetItem([field, value]))
            if s.san:
                san_item = QTreeWidgetItem(["Subject Alt Names", f"{len(s.san)} entries"])
                for san in s.san:
                    san_item.addChild(QTreeWidgetItem(["", san]))
                self.ssl_tree.addTopLevelItem(san_item)
            self.ssl_tree.expandAll()

        # Headers
        for key, value in result.http_headers.items():
            if key.startswith('_'):
                continue
            row = self.headers_table.rowCount()
            self.headers_table.insertRow(row)
            k_item = QTableWidgetItem(key)
            k_item.setForeground(QColor("#a78bfa"))
            k_item.setFont(QFont("Ubuntu Mono", 10))
            self.headers_table.setItem(row, 0, k_item)
            self.headers_table.setItem(row, 1, QTableWidgetItem(str(value)[:200]))

        # Subdomains
        for sub in sorted(result.subdomains):
            row = self.subdomain_table.rowCount()
            self.subdomain_table.insertRow(row)
            item = QTableWidgetItem(sub)
            item.setForeground(QColor("#3fb950"))
            self.subdomain_table.setItem(row, 0, item)

        if result.subdomains:
            idx = self.tabs.indexOf(self.subdomain_table)
            self.tabs.setTabText(idx, f"🌿 Subdomains ({len(result.subdomains)})")

        # History
        for entry in result.domain_history:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            ip_item = QTableWidgetItem(entry['ip'])
            ip_item.setForeground(QColor("#00f5ff"))
            self.history_table.setItem(row, 0, ip_item)
            self.history_table.setItem(row, 1, QTableWidgetItem(entry['location']))
            self.history_table.setItem(row, 2, QTableWidgetItem(entry['owner']))
            self.history_table.setItem(row, 3, QTableWidgetItem(entry['last_checked']))

        # Technologies
        if result.technologies:
            html = "<div style='padding:12px;'>"
            html += "<h3 style='color:#a78bfa; margin-bottom:12px;'>Detected Technologies</h3>"
            for tech in result.technologies:
                color = "#00f5ff" if ":" in tech else "#3fb950"
                html += f"<div style='display:inline-block; background:#21262d; border:1px solid #30363d; border-radius:6px; padding:4px 12px; margin:4px; color:{color}; font-size:12px;'>{tech}</div>"
            html += "</div>"
            self.tech_widget.setHtml(html)

        # Shodan
        if result.shodan_data and 'error' not in result.shodan_data:
            for key, value in result.shodan_data.items():
                if isinstance(value, list):
                    item = QTreeWidgetItem([key, f"{len(value)} items"])
                    for v in value[:10]:
                        item.addChild(QTreeWidgetItem(["", str(v)]))
                else:
                    self.shodan_tree.addTopLevelItem(QTreeWidgetItem([key, str(value)]))
            self.shodan_tree.expandAll()
        elif 'error' in result.shodan_data:
            self.shodan_tree.addTopLevelItem(
                QTreeWidgetItem(["Status", result.shodan_data['error']])
            )

        # Robots
        if result.robots_txt:
            self.robots_text.setPlainText(result.robots_txt)

        self.status_message.emit(f"Domain analysis complete: {result.domain}")

    def _on_error(self, error: str):
        self.status_log.append(f"❌ Error: {error}")
        self.lookup_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _send_to_graph(self):
        if not self._result:
            return
        r = self._result

        self.send_to_graph.emit({
            'type': 'domain',
            'id': f"domain_{r.domain}",
            'label': r.domain,
        })

        for ip in r.ip_addresses[:5]:
            self.send_to_graph.emit({
                'type': 'ip',
                'id': f"ip_{ip}",
                'label': ip,
                'parent': f"domain_{r.domain}",
                'edge_label': 'resolves to',
            })

        for sub in r.subdomains[:20]:
            self.send_to_graph.emit({
                'type': 'domain',
                'id': f"domain_{sub}",
                'label': sub,
                'parent': f"domain_{r.domain}",
                'edge_label': 'subdomain',
            })

        self.status_log.append(f"🕸️ Sent domain data to graph")

    def _export_html(self):
        if not self._result:
            self.status_log.append("⚠️  No results to export")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML Report",
            f"{self._result.domain}_report.html", "HTML (*.html)"
        )
        if path:
            html = generate_domain_report(self._result)
            save_html_report(html, path)
            self.status_log.append(f"📄 Report saved: {path}")

    def _export_json(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON",
            f"{self._result.domain}_data.json", "JSON (*.json)"
        )
        if path:
            save_json_report(self._result.__dict__, path)
            self.status_log.append(f"💾 JSON saved: {path}")

    def apply_settings(self, settings: dict):
        self._settings = settings
