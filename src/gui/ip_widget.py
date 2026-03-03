"""
Inspector Rabbit - IP Intelligence Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QTreeWidget,
    QTreeWidgetItem, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.ip_intel import IpIntelThread
from .components import apply_page_header_style


class IpWidget(QWidget):
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

        bar = QFrame()
        apply_page_header_style(bar, "#f87171")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("🖥️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("IP Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Geolocation · ASN · Reverse DNS · Port Scan · Blacklist Check · Shodan")
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

        left = self._build_left()
        content.addWidget(left)
        right = self._build_right()
        content.addWidget(right, 1)

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(12)

        self._lbl("TARGET IP / DOMAIN", lay)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("8.8.8.8 or example.com")
        self.target_input.setFixedHeight(42)
        self.target_input.setFont(QFont("Ubuntu", 12))
        self.target_input.returnPressed.connect(self._start)
        lay.addWidget(self.target_input)

        self.start_btn = QPushButton("🖥️  Analyze IP")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(self._start)
        lay.addWidget(self.start_btn)

        lay.addWidget(self._sep())
        self._lbl("OPTIONS", lay)

        self.do_ports = QCheckBox("Port scan (common ports)")
        self.do_ports.setChecked(True)
        lay.addWidget(self.do_ports)

        self.do_blacklists = QCheckBox("Blacklist check (8 RBLs)")
        self.do_blacklists.setChecked(True)
        lay.addWidget(self.do_blacklists)

        self.do_shodan = QCheckBox("Shodan lookup")
        self.do_shodan.setChecked(False)
        lay.addWidget(self.do_shodan)

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
        self.log.setMinimumHeight(180)
        lay.addWidget(self.log)

        lay.addStretch()

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

        # Geo tab
        self.geo_tree = QTreeWidget()
        self.geo_tree.setHeaderLabels(["Field", "Value"])
        self.geo_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.geo_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.geo_tree, "🌍 Geolocation")

        # Ports tab
        self.ports_table = self._make_table(["Port", "Service", "State", "Banner"])
        self.tabs.addTab(self.ports_table, "🔌 Open Ports (0)")

        # Blacklists tab
        self.bl_table = self._make_table(["RBL Server", "Status"])
        self.tabs.addTab(self.bl_table, "⛔ Blacklists (0)")

        # Shodan tab
        self.shodan_tree = QTreeWidget()
        self.shodan_tree.setHeaderLabels(["Field", "Value"])
        self.shodan_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.shodan_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.shodan_tree, "🛰️ Shodan")

        # Placeholder
        self.geo_tree.addTopLevelItem(QTreeWidgetItem(
            ["", "Enter an IP address or hostname and click Analyze IP"]
        ))
        return panel

    def _make_table(self, headers) -> QTableWidget:
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
        target = self.target_input.text().strip()
        if not target:
            self.log.append("⚠️  Enter an IP or domain")
            return

        self.log.clear()
        self.geo_tree.clear()
        self.ports_table.setRowCount(0)
        self.bl_table.setRowCount(0)
        self.shodan_tree.clear()
        self.log.append(f"🐇 Analyzing: {target}")

        shodan_key = self._settings.get('shodan_api_key', '')
        self._thread = IpIntelThread(
            target,
            shodan_api_key=shodan_key if self.do_shodan.isChecked() else "",
            do_port_scan=self.do_ports.isChecked(),
            do_blacklists=self.do_blacklists.isChecked()
        )
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.error.connect(lambda e: self.log.append(f"❌ {e}"))
        self._thread.start()
        self.start_btn.setEnabled(False)
        self.status_message.emit(f"Analyzing {target}...")

    def _on_result(self, result):
        self._result = result
        self.start_btn.setEnabled(True)
        self.log.append("✅ IP intelligence complete!")

        # Geo
        if result.geo:
            g = result.geo
            pairs = [
                ("Target", result.target),
                ("Resolved IP", result.resolved_ip),
                ("Reverse DNS", '\n'.join(result.reverse_dns) if result.reverse_dns else "N/A"),
                ("Country", f"{g.country} ({g.country_code})"),
                ("Region", g.region),
                ("City", g.city),
                ("Coordinates", f"{g.lat}, {g.lon}"),
                ("ISP", g.isp),
                ("Organization", g.org),
                ("ASN", g.asn),
                ("Timezone", g.timezone),
                ("Mobile", "Yes" if g.mobile else "No"),
                ("Proxy/VPN", "⚠️  Yes" if g.proxy else "No"),
                ("Hosting/DC", "Yes" if g.hosting else "No"),
                ("Abuse Contacts", '\n'.join(result.abuse_contacts) if result.abuse_contacts else "N/A"),
            ]
            for field, value in pairs:
                item = QTreeWidgetItem([field, str(value)])
                if field == "Proxy/VPN" and g.proxy:
                    item.setForeground(1, QColor("#e3b341"))
                    item.setForeground(0, QColor("#e3b341"))
                self.geo_tree.addTopLevelItem(item)

            if g.lat and g.lon:
                maps_item = QTreeWidgetItem(["Maps Link",
                    f"https://maps.google.com/?q={g.lat},{g.lon}"])
                maps_item.setForeground(1, QColor("#58a6ff"))
                self.geo_tree.addTopLevelItem(maps_item)
            self.geo_tree.expandAll()

        # Open ports
        for p in result.open_ports:
            row = self.ports_table.rowCount()
            self.ports_table.insertRow(row)
            port_item = QTableWidgetItem(str(p['port']))
            port_item.setForeground(QColor("#f87171"))
            port_item.setFont(QFont("Ubuntu Mono", 10, QFont.Weight.Bold))
            self.ports_table.setItem(row, 0, port_item)
            self.ports_table.setItem(row, 1, QTableWidgetItem(p['service']))
            ok_item = QTableWidgetItem("OPEN")
            ok_item.setForeground(QColor("#f85149"))
            self.ports_table.setItem(row, 2, ok_item)
            self.ports_table.setItem(row, 3, QTableWidgetItem(p.get('banner', '')[:60]))

        idx = self.tabs.indexOf(self.ports_table)
        self.tabs.setTabText(idx, f"🔌 Open Ports ({len(result.open_ports)})")

        # Blacklists
        listed_count = 0
        for rbl, listed in result.blacklists.items():
            row = self.bl_table.rowCount()
            self.bl_table.insertRow(row)
            self.bl_table.setItem(row, 0, QTableWidgetItem(rbl))
            if listed:
                listed_count += 1
                status = QTableWidgetItem("⛔ LISTED")
                status.setForeground(QColor("#f85149"))
            else:
                status = QTableWidgetItem("✅ Clean")
                status.setForeground(QColor("#3fb950"))
            self.bl_table.setItem(row, 1, status)
        idx = self.tabs.indexOf(self.bl_table)
        self.tabs.setTabText(idx, f"⛔ Blacklists ({listed_count} listed)")

        # Shodan
        if result.shodan_data and 'error' not in result.shodan_data:
            for key, value in result.shodan_data.items():
                if key == 'services':
                    svc_item = QTreeWidgetItem(["Services", f"{len(value)} found"])
                    for svc in value:
                        child = QTreeWidgetItem([
                            f":{svc['port']}/{svc['transport']}",
                            f"{svc['product']} {svc['version']}".strip()
                        ])
                        svc_item.addChild(child)
                    self.shodan_tree.addTopLevelItem(svc_item)
                elif isinstance(value, list):
                    item = QTreeWidgetItem([key, ', '.join(str(v) for v in value[:10])])
                    self.shodan_tree.addTopLevelItem(item)
                else:
                    self.shodan_tree.addTopLevelItem(QTreeWidgetItem([key, str(value)]))
            self.shodan_tree.expandAll()
        elif result.shodan_data.get('error'):
            self.shodan_tree.addTopLevelItem(
                QTreeWidgetItem(["Status", result.shodan_data['error']])
            )

        self.status_message.emit(f"IP analysis complete: {result.resolved_ip}")

    def _send_to_graph(self):
        if not self._result:
            return
        r = self._result
        self.send_to_graph.emit({
            'type': 'ip',
            'id': f"ip_{r.resolved_ip}",
            'label': f"{r.resolved_ip}\n{r.geo.city if r.geo else ''}",
        })
        if r.geo and r.geo.asn:
            self.send_to_graph.emit({
                'type': 'domain',
                'id': f"asn_{r.geo.asn}",
                'label': r.geo.asn,
                'parent': f"ip_{r.resolved_ip}",
                'edge_label': 'ASN',
            })

    def apply_settings(self, s):
        self._settings = s
