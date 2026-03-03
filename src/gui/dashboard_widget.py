"""
Inspector Rabbit - Dashboard Widget
Home screen with stats, quick actions, and feature navigation
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    def __init__(self, value: str, label: str, color: str = "#00f5ff",
                 icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(110)
        self.setStyleSheet(f"""
            QFrame#card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #161b22, stop:1 #0d1117);
                border: 1px solid #21262d;
                border-radius: 12px;
            }}
            QFrame#card:hover {{
                border: 1px solid {color}44;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Ubuntu", 22))
        icon_label.setStyleSheet("border: none; background: transparent;")
        top_row.addWidget(icon_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.val_label = QLabel(value)
        self.val_label.setFont(QFont("Ubuntu", 26, QFont.Weight.Bold))
        self.val_label.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        layout.addWidget(self.val_label)

        lbl_label = QLabel(label)
        lbl_label.setFont(QFont("Ubuntu", 11))
        lbl_label.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        layout.addWidget(lbl_label)

    def set_value(self, v: str):
        self.val_label.setText(v)


class FeatureCard(QFrame):
    """Feature card that emits a navigation signal when the action button is clicked."""

    clicked = pyqtSignal(str)   # emits page_name

    def __init__(self, icon: str, title: str, description: str,
                 action_label: str, color: str, page_name: str, parent=None):
        super().__init__(parent)
        self._page_name = page_name
        self.setObjectName("featureCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)
        self.setStyleSheet(f"""
            QFrame#featureCard {{
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 12px;
            }}
            QFrame#featureCard:hover {{
                border: 1px solid {color}55;
                background: #1a1f2a;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 26))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; border: none; background: transparent;"
        )
        layout.addWidget(desc_lbl)

        layout.addStretch()

        self.action_btn = QPushButton(action_label)
        self.action_btn.setFixedHeight(32)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}18;
                border: 1px solid {color}44;
                color: {color};
                border-radius: 8px;
                padding: 4px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {color}30;
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background: {color}44;
            }}
        """)
        self.action_btn.clicked.connect(self._on_click)
        layout.addWidget(self.action_btn)

    def _on_click(self):
        self.clicked.emit(self._page_name)

    def mousePressEvent(self, event):
        """Clicking anywhere on the card also navigates."""
        self.clicked.emit(self._page_name)
        super().mousePressEvent(event)


class DashboardWidget(QWidget):
    """Dashboard home screen. Emits navigate_to(page_name) when a card is activated."""

    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(28)

        # ── Header ───────────────────────────────────────────────────────────
        layout.addWidget(self._build_header())

        # ── Stats row ─────────────────────────────────────────────────────────
        stats_label = QLabel("CAPABILITIES")
        stats_label.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        stats_label.setStyleSheet("color: #484f58; letter-spacing: 2px; font-size: 10px;")
        layout.addWidget(stats_label)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)

        stat_data = [
            ("100+",  "Sites Checked",      "#00f5ff", "🌐"),
            ("15+",   "OSINT Modules",       "#a78bfa", "🔧"),
            ("8",     "DNS Record Types",    "#34d399", "📡"),
            ("60+",   "Dork Templates",      "#fb923c", "🔍"),
            ("3",     "Export Formats",      "#60a5fa", "📄"),
            ("Live",  "Graph Visualization", "#f472b6", "🕸️"),
        ]
        for i, (val, lbl, col, ico) in enumerate(stat_data):
            stats_grid.addWidget(StatCard(val, lbl, col, ico), i // 3, i % 3)

        layout.addLayout(stats_grid)

        # ── Feature cards ─────────────────────────────────────────────────────
        feat_label = QLabel("MODULES — click any card to open")
        feat_label.setStyleSheet(
            "color: #484f58; letter-spacing: 2px; font-size: 10px; font-weight: 700;"
        )
        layout.addWidget(feat_label)

        feat_grid = QGridLayout()
        feat_grid.setSpacing(14)

        # (icon, title, description, button_label, color, page_name)
        features = [
            ("👤", "Username Hunt",
             "Async search across 100+ social platforms simultaneously.",
             "Launch Search →", "#00f5ff", "username"),

            ("🌐", "Domain Intelligence",
             "WHOIS · DNS · SSL · subdomains · headers · Shodan.",
             "Analyze Domain →", "#a78bfa", "domain"),

            ("✉️", "Email OSINT",
             "Validate · SMTP verify · HIBP breach check · Gravatar.",
             "Investigate Email →", "#34d399", "email"),

            ("🔍", "Google Dorks",
             "60+ dork templates across 6 categories with live search.",
             "Launch Dorks →", "#fb923c", "dorks"),

            ("🖥️", "IP Intelligence",
             "Geolocation · port scan · RBL blacklists · Shodan · RDAP.",
             "Lookup IP →", "#f87171", "ip"),

            ("📞", "Phone OSINT",
             "Carrier · country · timezone · format variants · search links.",
             "Analyze Phone →", "#22d3ee", "phone"),

            ("🔐", "Certificate Transparency",
             "crt.sh CT log search · subdomain discovery via SSL certs.",
             "Search Certs →", "#fbbf24", "cert"),

            ("📄", "Metadata Extractor",
             "EXIF from images · GPS coordinates · PDF/DOCX author data.",
             "Extract Metadata →", "#fb923c", "metadata"),

            ("📋", "Paste & Leak Scanner",
             "GitHub · HackerNews · Reddit · Pastebin — exposed credential search.",
             "Scan Pastes →", "#f472b6", "pastes"),

            ("🕷️", "Web Crawler",
             "Spider sites to extract emails, phones, and social links.",
             "Start Crawling →", "#60a5fa", "crawler"),

            ("🕸️", "Network Graph",
             "Maltego-style force-directed relationship visualization.",
             "Open Graph →", "#f472b6", "graph"),

            ("📅", "Investigation Timeline",
             "Chronological event log — auto-captures all scan findings.",
             "View Timeline →", "#818cf8", "timeline"),

            ("🛡️", "Counter Surveillance",
             "Connection Guard · Traffic Monitor · Scan Detector · DNS Leak — "
             "watch who's watching you with live metrics & kill-switch.",
             "Open Monitor →", "#f85149", "countersur"),
        ]

        for i, (icon, title, desc, action, color, page) in enumerate(features):
            card = FeatureCard(icon, title, desc, action, color, page)
            card.clicked.connect(self.navigate_to)
            feat_grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(feat_grid)

        # ── Quick actions bar ─────────────────────────────────────────────────
        qa_label = QLabel("QUICK ACTIONS")
        qa_label.setStyleSheet(
            "color: #484f58; letter-spacing: 2px; font-size: 10px; font-weight: 700;"
        )
        layout.addWidget(qa_label)

        qa_frame = QFrame()
        qa_frame.setStyleSheet(
            "QFrame { background: #161b22; border: 1px solid #21262d; border-radius: 12px; }"
        )
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(20, 14, 20, 14)
        qa_layout.setSpacing(12)

        quick_actions = [
            ("🔎 New Username Search",  "username",  "#00f5ff"),
            ("🌐 Analyze Domain",        "domain",    "#a78bfa"),
            ("🖥️ IP Lookup",             "ip",        "#f87171"),
            ("📋 Scan for Leaks",        "pastes",    "#f472b6"),
            ("🕸️ Open Graph",            "graph",     "#f472b6"),
            ("📅 View Timeline",         "timeline",  "#818cf8"),
        ]
        for label, page, color in quick_actions:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}14;
                    border: 1px solid {color}33;
                    color: {color};
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {color}28;
                    border: 1px solid {color}88;
                }}
                QPushButton:pressed {{
                    background: {color}3c;
                }}
            """)
            btn.clicked.connect(lambda _checked, p=page: self.navigate_to.emit(p))
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)

        # ── Disclaimer ────────────────────────────────────────────────────────
        disc_frame = QFrame()
        disc_frame.setStyleSheet("""
            QFrame {
                background: #1c1208;
                border: 1px solid #e3b34133;
                border-radius: 12px;
            }
        """)
        disc_layout = QHBoxLayout(disc_frame)
        disc_layout.setContentsMargins(20, 14, 20, 14)

        warn_icon = QLabel("⚠️")
        warn_icon.setFont(QFont("Ubuntu", 18))
        warn_icon.setStyleSheet("border: none; background: transparent;")
        disc_layout.addWidget(warn_icon)

        disc_text = QLabel(
            "<b style='color:#e3b341;'>Educational &amp; Authorized Use Only</b><br>"
            "<span style='color:#8b949e; font-size:12px;'>"
            "Inspector Rabbit is designed for security research, CTF competitions, "
            "and authorized penetration testing. Only investigate targets you have "
            "explicit permission to examine. Unauthorized OSINT may violate privacy "
            "laws and computer crime statutes."
            "</span>"
        )
        disc_text.setWordWrap(True)
        disc_text.setStyleSheet("border: none; background: transparent;")
        disc_layout.addWidget(disc_text, 1)

        layout.addWidget(disc_frame)
        layout.addStretch()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.5 #1e1b4b, stop:1 #0f172a);
                border: 1px solid #2d2f6b;
                border-radius: 16px;
            }
        """)
        header.setFixedHeight(140)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title = QLabel("🐇 Inspector Rabbit")
        title.setFont(QFont("Ubuntu", 28, QFont.Weight.Black))
        title.setStyleSheet("color: #00f5ff; border: none; background: transparent;")
        text_layout.addWidget(title)

        subtitle = QLabel("Advanced Open Source Intelligence Suite  ·  v1.2.0  ·  15 Modules + Counter Surveillance")
        subtitle.setFont(QFont("Ubuntu", 12))
        subtitle.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        text_layout.addWidget(subtitle)

        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(8)
        for tag in ["Sherlock", "Maltego", "SpiderFoot", "Shodan", "Recon-ng", "Dorks", "Cert CT", "Timeline"]:
            tag_lbl = QLabel(tag)
            tag_lbl.setStyleSheet("""
                color: #8b949e;
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 3px 10px;
                font-size: 10px;
            """)
            tags_layout.addWidget(tag_lbl)
        tags_layout.addStretch()
        text_layout.addLayout(tags_layout)

        layout.addLayout(text_layout, 1)

        rabbit = QLabel("🐇")
        rabbit.setFont(QFont("Ubuntu", 64))
        rabbit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rabbit.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(rabbit)

        return header
