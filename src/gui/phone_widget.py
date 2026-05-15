"""
Inspector Rabbit - Phone OSINT Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QTabWidget, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

from ..modules.phone_osint import PhoneOsintThread, generate_phone_variants, analyze_phone
from .components import apply_page_header_style


REGIONS = [
    ("US", "United States (+1)"), ("GB", "United Kingdom (+44)"),
    ("CA", "Canada (+1)"), ("AU", "Australia (+61)"),
    ("DE", "Germany (+49)"), ("FR", "France (+33)"),
    ("IN", "India (+91)"), ("JP", "Japan (+81)"),
    ("CN", "China (+86)"), ("BR", "Brazil (+55)"),
    ("MX", "Mexico (+52)"), ("RU", "Russia (+7)"),
    ("IT", "Italy (+39)"), ("ES", "Spain (+34)"),
    ("KR", "South Korea (+82)"), ("NL", "Netherlands (+31)"),
]

TYPE_COLORS = {
    'MOBILE': "#3fb950",
    'FIXED_LINE': "#60a5fa",
    'VOIP': "#a78bfa",
    'TOLL_FREE': "#fbbf24",
    'UNKNOWN': "#8b949e",
}


class PhoneWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        apply_page_header_style(bar, "#22d3ee")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("📞")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Phone Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Carrier · Country · Line Type · Format Variants · Search Links")
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

        self._lbl("PHONE NUMBER", lay)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1 (555) 123-4567")
        self.phone_input.setFixedHeight(42)
        self.phone_input.setFont(QFont("Ubuntu", 13))
        self.phone_input.returnPressed.connect(self._analyze)
        lay.addWidget(self.phone_input)

        self._lbl("DEFAULT REGION", lay)
        self.region_combo = QComboBox()
        for code, name in REGIONS:
            self.region_combo.addItem(name, code)
        self.region_combo.setFixedHeight(38)
        lay.addWidget(self.region_combo)

        self.analyze_btn = QPushButton("📞  Analyze Number")
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.setFixedHeight(42)
        self.analyze_btn.clicked.connect(self._analyze)
        lay.addWidget(self.analyze_btn)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)
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
        self.log.setMinimumHeight(150)
        lay.addWidget(self.log)

        lay.addStretch()

        graph_btn = QPushButton("🕸️ Send to Graph")
        graph_btn.setFixedHeight(36)
        graph_btn.clicked.connect(self._send_to_graph)
        lay.addWidget(graph_btn)

        copy_btn = QPushButton("📋 Copy E.164")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(self._copy_e164)
        lay.addWidget(copy_btn)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # Overview
        self.overview = QTextEdit()
        self.overview.setReadOnly(True)
        self.overview.setStyleSheet("QTextEdit { background: #0d1117; border: none; padding: 16px; }")
        self.tabs.addTab(self.overview, "📋 Overview")

        # Variants
        self.variants_table = self._make_table(["Format Variant"])
        self.tabs.addTab(self.variants_table, "🔀 Format Variants")

        # Search Links
        self.links_table = self._make_table(["Source", "Description", "URL"])
        self.links_table.doubleClicked.connect(self._open_link)
        self.tabs.addTab(self.links_table, "🔍 Search Links")

        self.overview.setHtml("""
        <div style='padding:24px; text-align:center; color:#8b949e;'>
        <div style='font-size:48px;'>📞</div>
        <h2 style='color:#e6edf3;'>Phone Intelligence</h2>
        <p>Enter a phone number above and click Analyze.</p>
        </div>""")

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

    def _analyze(self):
        phone = self.phone_input.text().strip()
        if not phone:
            self.log.append("⚠️  Enter a phone number")
            return

        region = self.region_combo.currentData() or "US"
        self.log.clear()
        self.log.append(f"📞 Analyzing: {phone} (region: {region})")

        self.variants_table.setRowCount(0)
        self.links_table.setRowCount(0)

        self._thread = PhoneOsintThread(phone, region)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.error.connect(self._on_error)
        self._thread.start()
        self.analyze_btn.setEnabled(False)
        self.status_message.emit(f"Analyzing phone {phone}...")

    def _on_error(self, error):
        self.log.append(f"❌ {error}")
        self.analyze_btn.setEnabled(True)

    def _on_result(self, result):
        self._result = result
        self.analyze_btn.setEnabled(True)
        self.log.append("✅ Analysis complete!")

        if result.error:
            self.overview.setHtml(
                f"<div style='padding:24px; color:#f85149;'>❌ Error: {result.error}</div>"
            )
            return

        # Determine type color
        num_type = result.number_type
        type_color = TYPE_COLORS.get(num_type, "#8b949e")

        # Validity badge
        if result.is_valid:
            valid_badge = "<span style='background:#1a3a2a; color:#3fb950; padding:3px 12px; border-radius:10px; font-size:12px;'>✅ VALID</span>"
        elif result.is_possible:
            valid_badge = "<span style='background:#2a2a10; color:#e3b341; padding:3px 12px; border-radius:10px; font-size:12px;'>⚠️ POSSIBLE</span>"
        else:
            valid_badge = "<span style='background:#2a1515; color:#f85149; padding:3px 12px; border-radius:10px; font-size:12px;'>❌ INVALID</span>"

        html = f"""
        <div style='padding:20px; color:#c9d1d9;'>
        <div style='margin-bottom:16px;'>{valid_badge}
        <span style='background:{type_color}22; color:{type_color}; padding:3px 12px;
              border-radius:10px; font-size:12px; margin-left:8px; border:1px solid {type_color}44;'
        >{num_type}</span></div>

        <div style='font-size:28px; font-weight:bold; color:#00f5ff; margin-bottom:20px;'>
        {result.formatted_international or result.raw_input}
        </div>

        <table style='width:100%; border-collapse:collapse;'>
        <tr style='background:#161b22;'>
          <th style='padding:10px; text-align:left; color:#8b949e; font-size:11px; border-bottom:1px solid #21262d;'>FIELD</th>
          <th style='padding:10px; text-align:left; color:#8b949e; font-size:11px; border-bottom:1px solid #21262d;'>VALUE</th>
        </tr>
        """
        rows = [
            ("National Format", result.formatted_national),
            ("International Format", result.formatted_international),
            ("E.164 Format", result.formatted_e164),
            ("RFC3966 Format", result.formatted_rfc3966),
            ("Country Code", f"+{result.country_code}"),
            ("Country", result.country_name),
            ("Region/Area", result.area_description),
            ("Carrier", result.carrier or "Unknown"),
            ("Timezone(s)", ', '.join(result.timezone) if result.timezone else "Unknown"),
        ]
        for i, (field, value) in enumerate(rows):
            bg = "#0d1117" if i % 2 else "#161b22"
            html += f"""<tr style='background:{bg};'>
              <td style='padding:9px; color:#8b949e; font-size:12px; border-bottom:1px solid #21262d;'>{field}</td>
              <td style='padding:9px; color:#c9d1d9; font-size:12px; border-bottom:1px solid #21262d;
                  font-family:monospace;'>{value or "—"}</td></tr>"""
        html += "</table></div>"
        self.overview.setHtml(html)

        # Variants
        variants = generate_phone_variants(result.raw_input)
        for v in variants:
            row = self.variants_table.rowCount()
            self.variants_table.insertRow(row)
            item = QTableWidgetItem(v)
            item.setFont(QFont("Ubuntu Mono", 11))
            item.setForeground(QColor("#00f5ff"))
            self.variants_table.setItem(row, 0, item)

        # Search links
        for link in result.search_urls:
            row = self.links_table.rowCount()
            self.links_table.insertRow(row)
            self.links_table.setItem(row, 0, QTableWidgetItem(link['name']))
            self.links_table.setItem(row, 1, QTableWidgetItem(link['description']))
            url_item = QTableWidgetItem(link['url'])
            url_item.setForeground(QColor("#58a6ff"))
            self.links_table.setItem(row, 2, url_item)

        self.status_message.emit(
            f"Phone analyzed: {result.formatted_international or result.raw_input}"
        )

    def _open_link(self, index):
        row = index.row()
        url_item = self.links_table.item(row, 2)
        if url_item and url_item.text().startswith('http'):
            QDesktopServices.openUrl(QUrl(url_item.text()))

    def _copy_e164(self):
        if self._result and self._result.formatted_e164:
            QApplication.clipboard().setText(self._result.formatted_e164)
            self.log.append(f"📋 Copied: {self._result.formatted_e164}")

    def _send_to_graph(self):
        if not self._result:
            return
        r = self._result
        display = r.formatted_international or r.raw_input
        self.send_to_graph.emit({
            'type': 'phone',
            'id': f"phone_{r.formatted_e164 or r.raw_input}",
            'label': f"{display}\n{r.carrier or r.country_name}",
        })

    def apply_settings(self, s):
        pass
