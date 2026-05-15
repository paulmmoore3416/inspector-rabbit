"""
Inspector Rabbit - Email OSINT Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QGroupBox, QGridLayout,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.email_osint import EmailOsintThread, EmailPatternThread
from .components import apply_page_header_style


def _status_badge(text: str, good: bool) -> str:
    color = "#3fb950" if good else "#f85149"
    bg = "#1a3a2a" if good else "#2a1515"
    icon = "✅" if good else "❌"
    return f"<span style='color:{color}; background:{bg}; border-radius:6px; padding:2px 10px; font-size:12px;'>{icon} {text}</span>"


class EmailWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._result = None
        self._pattern_thread = None
        self._settings = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Topbar
        bar = QFrame()
        apply_page_header_style(bar, "#34d399")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)

        icon = QLabel("✉️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Email Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Validation · SMTP verification · Breach detection · Pattern generation")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        # Main content
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        layout.addLayout(content_layout, 1)

        # Left panel
        left = self._build_left_panel()
        content_layout.addWidget(left)

        # Right panel
        right = self._build_right_panel()
        content_layout.addWidget(right, 1)

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)

        self._lbl("EMAIL INVESTIGATION", layout)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("target@example.com")
        self.email_input.setFixedHeight(42)
        self.email_input.setFont(QFont("Ubuntu", 12))
        self.email_input.returnPressed.connect(self._start_investigation)
        layout.addWidget(self.email_input)

        self.investigate_btn = QPushButton("🔍  Investigate Email")
        self.investigate_btn.setObjectName("primaryBtn")
        self.investigate_btn.setFixedHeight(42)
        self.investigate_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.investigate_btn.clicked.connect(self._start_investigation)
        layout.addWidget(self.investigate_btn)

        layout.addWidget(self._sep())
        self._lbl("OPTIONS", layout)

        self.smtp_check = QCheckBox("SMTP verification")
        self.smtp_check.setChecked(True)
        layout.addWidget(self.smtp_check)

        layout.addWidget(self._sep())
        self._lbl("EMAIL PATTERN GENERATOR", layout)

        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("First name")
        self.first_name.setFixedHeight(36)
        layout.addWidget(self.first_name)

        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Last name")
        self.last_name.setFixedHeight(36)
        layout.addWidget(self.last_name)

        self.company_domain = QLineEdit()
        self.company_domain.setPlaceholderText("company.com")
        self.company_domain.setFixedHeight(36)
        layout.addWidget(self.company_domain)

        gen_btn = QPushButton("⚡  Generate Patterns")
        gen_btn.setFixedHeight(38)
        gen_btn.clicked.connect(self._generate_patterns)
        layout.addWidget(gen_btn)

        layout.addWidget(self._sep())
        self._lbl("STATUS", layout)
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMinimumHeight(120)
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
        layout.addWidget(self.status_log)
        layout.addStretch()

        graph_btn = QPushButton("🕸️ Send to Graph")
        graph_btn.setFixedHeight(36)
        graph_btn.clicked.connect(self._send_to_graph)
        layout.addWidget(graph_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Overview tab
        self.overview = QTextEdit()
        self.overview.setReadOnly(True)
        self.overview.setStyleSheet("QTextEdit { background: #0d1117; border: none; padding: 16px; }")
        self.tabs.addTab(self.overview, "📊 Overview")

        # MX Records tab
        self.mx_table = self._make_table(["MX Server", "Priority"])
        self.tabs.addTab(self.mx_table, "📡 MX Records")

        # Breaches tab
        self.breaches_text = QTextEdit()
        self.breaches_text.setReadOnly(True)
        self.breaches_text.setStyleSheet("QTextEdit { background: #0d1117; border: none; padding: 16px; }")
        self.tabs.addTab(self.breaches_text, "🚨 Breach Data")

        # Patterns tab
        self.patterns_table = self._make_table(["Email Pattern"])
        self.tabs.addTab(self.patterns_table, "🔀 Email Patterns")

        # Placeholder overview
        self.overview.setHtml("""
        <div style='padding:24px; color:#8b949e; text-align:center;'>
        <div style='font-size:48px; margin-bottom:16px;'>✉️</div>
        <h2 style='color:#e6edf3;'>Email Intelligence</h2>
        <p>Enter an email address and click Investigate to begin analysis.</p>
        <br>
        <div style='text-align:left; max-width:400px; margin:0 auto;'>
        <p style='color:#c9d1d9; margin-bottom:8px;'>This module will check:</p>
        <ul style='color:#8b949e;'>
        <li>Email format validation</li>
        <li>DNS MX record verification</li>
        <li>SMTP mailbox verification</li>
        <li>Disposable email detection</li>
        <li>Gravatar profile lookup</li>
        <li>HaveIBeenPwned breach check (requires API key)</li>
        </ul>
        </div>
        </div>
        """)

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

    def _lbl(self, text: str, layout):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(l)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _start_investigation(self):
        email = self.email_input.text().strip()
        if not email:
            self.status_log.append("⚠️  Enter an email address")
            return

        self.status_log.clear()
        self.status_log.append(f"🐇 Investigating: {email}")
        self.overview.setHtml(f"<div style='padding:16px; color:#8b949e;'>🔍 Investigating {email}...</div>")
        self.mx_table.setRowCount(0)
        self.breaches_text.clear()

        hibp_key = self._settings.get('hibp_api_key', '')
        self._thread = EmailOsintThread(
            email,
            hibp_api_key=hibp_key,
            verify_smtp_flag=self.smtp_check.isChecked()
        )
        self._thread.progress.connect(lambda m: self.status_log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.error.connect(lambda e: self.status_log.append(f"❌ {e}"))
        self._thread.start()

        self.investigate_btn.setEnabled(False)
        self.status_message.emit(f"Investigating {email}...")

    def _on_result(self, result):
        self._result = result
        self.investigate_btn.setEnabled(True)
        self.status_log.append("✅ Investigation complete!")
        self.status_message.emit(f"Email investigation complete")

        # Build overview
        html = f"""
        <div style='padding:20px; color:#c9d1d9;'>
        <h2 style='color:#00f5ff; margin-bottom:20px;'>✉️ {result.email}</h2>

        <div style='display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap;'>
          <span style='background:#21262d; border-radius:8px; padding:8px 16px; font-size:12px;'>
            Format: {_status_badge('Valid', result.valid_format) if result.valid_format else _status_badge('Invalid', False)}
          </span>
          <span style='background:#21262d; border-radius:8px; padding:8px 16px; font-size:12px;'>
            Domain: {_status_badge('Exists', result.domain_exists) if result.domain_exists else _status_badge('No MX', False)}
          </span>
          <span style='background:#21262d; border-radius:8px; padding:8px 16px; font-size:12px;'>
            Disposable: {_status_badge('Yes', False) if result.disposable else _status_badge('No', True)}
          </span>
          <span style='background:#21262d; border-radius:8px; padding:8px 16px; font-size:12px;'>
            Gravatar: {_status_badge('Found', True) if result.gravatar_exists else _status_badge('None', False)}
          </span>
        </div>

        <table style='width:100%; border-collapse:collapse;'>
        <tr style='background:#161b22;'>
          <th style='padding:10px; text-align:left; color:#8b949e; font-size:11px; border-bottom:1px solid #21262d;'>FIELD</th>
          <th style='padding:10px; text-align:left; color:#8b949e; font-size:11px; border-bottom:1px solid #21262d;'>VALUE</th>
        </tr>
        """

        rows = [
            ("SMTP Valid", "✅ Mailbox confirmed" if result.smtp_valid else f"❌ {result.smtp_message}"),
            ("Gravatar Hash", result.gravatar_hash),
            ("Gravatar URL", f"https://www.gravatar.com/avatar/{result.gravatar_hash}" if result.gravatar_hash else "N/A"),
            ("MX Servers", f"{len(result.mx_records)} found"),
            ("Breaches", f"🚨 {len(result.breaches)} breach(es) found" if result.breaches else "✅ No breaches found"),
        ]

        for i, (field, value) in enumerate(rows):
            bg = "#0d1117" if i % 2 else "#161b22"
            html += f"""
            <tr style='background:{bg};'>
              <td style='padding:10px; color:#8b949e; font-size:12px; border-bottom:1px solid #21262d;'>{field}</td>
              <td style='padding:10px; color:#c9d1d9; font-size:12px; border-bottom:1px solid #21262d;'>{value}</td>
            </tr>
            """

        if result.breach_error:
            html += f"""
            <tr><td colspan='2' style='padding:10px; color:#e3b341; font-size:11px;'>
            ℹ️ {result.breach_error}</td></tr>
            """

        html += "</table></div>"
        self.overview.setHtml(html)

        # MX Records
        self.mx_table.setRowCount(0)
        for mx in result.mx_records:
            row = self.mx_table.rowCount()
            self.mx_table.insertRow(row)
            item = QTableWidgetItem(mx)
            item.setForeground(QColor("#00f5ff"))
            self.mx_table.setItem(row, 0, item)

        # Breaches
        if result.breaches:
            breach_html = f"<div style='padding:16px;'><h3 style='color:#f85149; margin-bottom:16px;'>🚨 {len(result.breaches)} Breach(es) Found</h3>"
            for breach in result.breaches:
                name = breach.get('Name', 'Unknown')
                date = breach.get('BreachDate', 'Unknown')
                desc = breach.get('Description', '')
                domain = breach.get('Domain', '')
                breach_html += f"""
                <div style='background:#1c0a0a; border:1px solid #f8514944; border-radius:8px; padding:14px; margin-bottom:10px;'>
                  <div style='color:#f85149; font-weight:bold;'>{name}</div>
                  <div style='color:#8b949e; font-size:11px; margin-top:4px;'>Date: {date} | Domain: {domain}</div>
                  <div style='color:#c9d1d9; font-size:11px; margin-top:6px;'>{desc[:200]}</div>
                </div>"""
            self.breaches_text.setHtml(breach_html + "</div>")
        else:
            self.breaches_text.setHtml("""
            <div style='padding:24px; text-align:center; color:#3fb950;'>
            <div style='font-size:48px;'>✅</div>
            <h3>No breaches found</h3>
            <p style='color:#8b949e; font-size:12px;'>
            """ + (result.breach_error or "This email was not found in known breach databases") + """
            </p>
            </div>""")

    def _generate_patterns(self):
        first = self.first_name.text().strip()
        last = self.last_name.text().strip()
        domain = self.company_domain.text().strip()

        if not first or not last or not domain:
            self.status_log.append("⚠️  Enter first name, last name, and domain")
            return

        self.status_log.append(f"⚡  Generating patterns for {first} {last} @ {domain}...")

        self._pattern_thread = EmailPatternThread(first, last, domain)
        self._pattern_thread.result_ready.connect(self._on_patterns)
        self._pattern_thread.start()

    def _on_patterns(self, patterns: list):
        self.patterns_table.setRowCount(0)
        for pattern in patterns:
            row = self.patterns_table.rowCount()
            self.patterns_table.insertRow(row)
            item = QTableWidgetItem(pattern)
            item.setForeground(QColor("#34d399"))
            item.setFont(QFont("Ubuntu Mono", 11))
            self.patterns_table.setItem(row, 0, item)
        self.status_log.append(f"✅  Generated {len(patterns)} email patterns")
        idx = self.tabs.indexOf(self.patterns_table)
        self.tabs.setTabText(idx, f"🔀 Patterns ({len(patterns)})")
        self.tabs.setCurrentIndex(idx)

    def _send_to_graph(self):
        if not self._result:
            return
        r = self._result
        self.send_to_graph.emit({
            'type': 'email',
            'id': f"email_{r.email}",
            'label': r.email,
        })
        if r.gravatar_exists:
            self.send_to_graph.emit({
                'type': 'identity',
                'id': f"gravatar_{r.gravatar_hash}",
                'label': f"Gravatar\n{r.gravatar_hash[:12]}...",
                'parent': f"email_{r.email}",
                'edge_label': 'has gravatar',
            })
        self.status_log.append("🕸️ Sent to graph")

    def apply_settings(self, settings: dict):
        self._settings = settings
