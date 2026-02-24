"""
Inspector Rabbit - Certificate Transparency Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.cert_transparency import CertTransparencyThread


class CertWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._result = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #010409; border-bottom: 1px solid #21262d; }")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("🔐")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Certificate Transparency")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Search crt.sh CT logs · Subdomain discovery via certificates · Issuer timeline")
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

        self._lbl("DOMAIN", lay)
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        self.domain_input.setFixedHeight(42)
        self.domain_input.setFont(QFont("Ubuntu", 12))
        self.domain_input.returnPressed.connect(self._start)
        lay.addWidget(self.domain_input)

        self.start_btn = QPushButton("🔐  Search CT Logs")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(self._start)
        lay.addWidget(self.start_btn)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet("""
            QTextEdit { background:#010409; border:1px solid #21262d; border-radius:8px;
                        color:#3fb950; font-family:'Ubuntu Mono',monospace; font-size:11px; }
        """)
        self.log.setMinimumHeight(220)
        lay.addWidget(self.log)

        lay.addStretch()

        copy_subs_btn = QPushButton("📋 Copy Subdomains")
        copy_subs_btn.setFixedHeight(36)
        copy_subs_btn.clicked.connect(self._copy_subdomains)
        lay.addWidget(copy_subs_btn)

        graph_btn = QPushButton("🕸️ Send to Graph")
        graph_btn.setFixedHeight(36)
        graph_btn.clicked.connect(self._send_to_graph)
        lay.addWidget(graph_btn)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # Subdomains tab
        self.sub_table = self._make_table(["Subdomain Found via CT"])
        self.tabs.addTab(self.sub_table, "🌿 Subdomains (0)")

        # Certificates tab
        self.cert_table = self._make_table(["ID", "Common Name", "Issuer", "Not Before", "Not After", "Logged At"])
        self.tabs.addTab(self.cert_table, "📜 Certificates (0)")

        # Issuers tab
        self.issuer_table = self._make_table(["Certificate Authority", "Count"])
        self.tabs.addTab(self.issuer_table, "🏢 Issuers")

        # Timeline
        self.timeline_table = self._make_table(["Date", "Common Name", "Issuer"])
        self.tabs.addTab(self.timeline_table, "📅 Timeline")

        return panel

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
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
        domain = self.domain_input.text().strip()
        if not domain:
            self.log.append("⚠️  Enter a domain")
            return

        self.log.clear()
        for t in [self.sub_table, self.cert_table, self.issuer_table, self.timeline_table]:
            t.setRowCount(0)
        self.log.append(f"🐇 Querying CT logs for: {domain}")

        self._thread = CertTransparencyThread(domain)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.start()
        self.start_btn.setEnabled(False)
        self.status_message.emit(f"Searching CT logs for {domain}...")

    def _on_result(self, result):
        self._result = result
        self.start_btn.setEnabled(True)

        if result.error:
            self.log.append(f"❌ {result.error}")
            return

        self.log.append(f"✅ Found {result.total_certs} certs, {len(result.unique_subdomains)} subdomains!")

        # Subdomains
        for sub in result.unique_subdomains:
            row = self.sub_table.rowCount()
            self.sub_table.insertRow(row)
            item = QTableWidgetItem(sub)
            item.setForeground(QColor("#3fb950"))
            item.setFont(QFont("Ubuntu Mono", 10))
            self.sub_table.setItem(row, 0, item)
        idx = self.tabs.indexOf(self.sub_table)
        self.tabs.setTabText(idx, f"🌿 Subdomains ({len(result.unique_subdomains)})")

        # Certificates
        for cert in result.certificates[:200]:
            row = self.cert_table.rowCount()
            self.cert_table.insertRow(row)
            self.cert_table.setItem(row, 0, QTableWidgetItem(str(cert.id)))
            cn_item = QTableWidgetItem(cert.common_name)
            cn_item.setForeground(QColor("#00f5ff"))
            self.cert_table.setItem(row, 1, cn_item)
            self.cert_table.setItem(row, 2, QTableWidgetItem(cert.issuer_name))
            self.cert_table.setItem(row, 3, QTableWidgetItem(cert.not_before[:10]))
            self.cert_table.setItem(row, 4, QTableWidgetItem(cert.not_after[:10]))
            self.cert_table.setItem(row, 5, QTableWidgetItem(cert.logged_at[:16]))
        idx = self.tabs.indexOf(self.cert_table)
        self.tabs.setTabText(idx, f"📜 Certificates ({len(result.certificates)})")

        # Issuers
        for issuer, count in result.issuers.items():
            row = self.issuer_table.rowCount()
            self.issuer_table.insertRow(row)
            self.issuer_table.setItem(row, 0, QTableWidgetItem(issuer))
            count_item = QTableWidgetItem(str(count))
            count_item.setForeground(QColor("#a78bfa"))
            count_item.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
            self.issuer_table.setItem(row, 1, count_item)

        # Timeline
        for entry in result.timeline[:100]:
            row = self.timeline_table.rowCount()
            self.timeline_table.insertRow(row)
            self.timeline_table.setItem(row, 0, QTableWidgetItem(entry['date'][:16]))
            self.timeline_table.setItem(row, 1, QTableWidgetItem(entry['common_name']))
            self.timeline_table.setItem(row, 2, QTableWidgetItem(entry['issuer']))

        self.tabs.setCurrentIndex(0)
        self.status_message.emit(
            f"CT scan: {len(result.unique_subdomains)} subdomains, {result.total_certs} certs"
        )

    def _copy_subdomains(self):
        if self._result and self._result.unique_subdomains:
            QApplication.clipboard().setText('\n'.join(self._result.unique_subdomains))
            self.log.append(f"📋 Copied {len(self._result.unique_subdomains)} subdomains")

    def _send_to_graph(self):
        if not self._result:
            return
        domain = self._result.domain
        self.send_to_graph.emit({'type': 'domain', 'id': f"domain_{domain}", 'label': domain})
        for sub in self._result.unique_subdomains[:20]:
            self.send_to_graph.emit({
                'type': 'domain', 'id': f"domain_{sub}", 'label': sub,
                'parent': f"domain_{domain}", 'edge_label': 'CT subdomain',
            })

    def apply_settings(self, s):
        pass
