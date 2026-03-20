"""
Inspector Rabbit - Dashboard Widget  v1.5.0
Space Gray theme: clean hero, refined stat cards, per-module feature cards.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


# ── Space Gray accent palette (matches styles.py) ─────────────────────────────
_BLUE   = "#0a84ff"
_TEAL   = "#5ac8fa"
_GREEN  = "#30d158"
_ORANGE = "#ff9f0a"
_RED    = "#ff453a"
_PURPLE = "#bf5af2"
_PINK   = "#ff375f"
_YELLOW = "#ffd60a"
_INDIGO = "#5e5ce6"
_MINT   = "#63e6be"
_BROWN  = "#a2845e"
_GRAY   = "#8e8e93"


# ── Hero Banner ────────────────────────────────────────────────────────────────

class HeroBanner(QFrame):
    """Space Gray hero — warm dark gradient, no paint noise."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(148)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1c1c20, stop:0.5 #222226, stop:1 #18181c);
                border: 1px solid #38383a;
                border-radius: 12px;
            }
        """)
        self._build_content()

    def _build_content(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 22, 28, 22)
        layout.setSpacing(20)

        text_col = QVBoxLayout()
        text_col.setSpacing(7)

        title = QLabel("Inspector Rabbit")
        title.setFont(QFont("Ubuntu", 26, QFont.Weight.Bold))
        title.setStyleSheet("color: #f5f5f7; border: none; background: transparent;")
        text_col.addWidget(title)

        subtitle = QLabel("Advanced Open Source Intelligence Suite  ·  v1.5.0  ·  24 Modules")
        subtitle.setFont(QFont("Ubuntu", 12))
        subtitle.setStyleSheet("color: #636366; border: none; background: transparent;")
        text_col.addWidget(subtitle)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_row.setContentsMargins(0, 0, 0, 0)
        for text, color in [
            ("OSINT",         _BLUE),
            ("PASSIVE RECON", _PURPLE),
            ("COUNTER-SURV",  _RED),
            ("OPEN SOURCE",   _GREEN),
        ]:
            badge = QLabel(text)
            badge.setStyleSheet(f"""
                color: {color};
                background: {color}1a;
                border: 1px solid {color}44;
                border-radius: 5px;
                padding: 2px 9px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            """)
            tags_row.addWidget(badge)
        tags_row.addStretch()
        text_col.addLayout(tags_row)

        layout.addLayout(text_col, 1)

        rabbit = QLabel("🐇")
        rabbit.setFont(QFont("Ubuntu", 68))
        rabbit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rabbit.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(rabbit)


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, value: str, label: str, color: str, icon: str = "",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(112)
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: #2c2c2e;
                border: 1px solid #38383a;
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
            QFrame#statCard:hover {{
                background: #3a3a3c;
                border: 1px solid #48484a;
                border-left: 3px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 18))
        icon_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        top.addWidget(icon_lbl)
        top.addStretch()

        self.val_lbl = QLabel(value)
        self.val_lbl.setFont(QFont("Ubuntu", 24, QFont.Weight.Bold))
        self.val_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        top.addWidget(self.val_lbl)
        layout.addLayout(top)

        layout.addStretch()

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #636366; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1px; border: none; background: transparent;"
        )
        layout.addWidget(lbl)

    def set_value(self, v: str):
        self.val_lbl.setText(v)


# ── Feature Card ───────────────────────────────────────────────────────────────

class FeatureCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, icon: str, title: str, description: str,
                 action_label: str, color: str, page_name: str, parent=None):
        super().__init__(parent)
        self._page_name = page_name
        self.setObjectName("featureCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(188)
        self.setStyleSheet(f"""
            QFrame#featureCard {{
                background: #2c2c2e;
                border: 1px solid #38383a;
                border-top: 2px solid {color}66;
                border-radius: 10px;
            }}
            QFrame#featureCard:hover {{
                background: #3a3a3c;
                border: 1px solid #48484a;
                border-top: 2px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        hr = QHBoxLayout()
        hr.setSpacing(8)
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 22))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        hr.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        hr.addWidget(title_lbl, 1)
        layout.addLayout(hr)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #636366; font-size: 11px; border: none; background: transparent;"
        )
        layout.addWidget(desc_lbl)
        layout.addStretch()

        self.action_btn = QPushButton(action_label)
        self.action_btn.setFixedHeight(28)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}18;
                border: 1px solid {color}44;
                color: {color};
                border-radius: 6px;
                padding: 2px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {color}30;
                border: 1px solid {color}88;
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
        self.clicked.emit(self._page_name)
        super().mousePressEvent(event)


# ── Section Label ─────────────────────────────────────────────────────────────

def _section_label(text: str) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)

    accent = QFrame()
    accent.setFixedSize(3, 13)
    accent.setStyleSheet("background: #0a84ff; border-radius: 1px;")
    h.addWidget(accent)

    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #48484a; font-size: 10px; font-weight: 700; "
        "letter-spacing: 1.2px; background: transparent;"
    )
    h.addWidget(lbl)
    h.addStretch()
    return row


# ── Dashboard Widget ───────────────────────────────────────────────────────────

class DashboardWidget(QWidget):
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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── Hero ──────────────────────────────────────────────────────────────
        layout.addWidget(HeroBanner())

        # ── Stats ─────────────────────────────────────────────────────────────
        layout.addWidget(_section_label("CAPABILITIES"))

        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)
        for i, (val, lbl, col, ico) in enumerate([
            ("100+", "Sites Checked",      _TEAL,   "🌐"),
            ("24+",  "OSINT Modules",      _PURPLE, "🔧"),
            ("8",    "DNS Record Types",   _GREEN,  "📡"),
            ("60+",  "Dork Templates",     _ORANGE, "🔍"),
            ("3",    "Export Formats",     _BLUE,   "📄"),
            ("Live", "Graph Visualization",_PINK,   "🕸️"),
        ]):
            stats_grid.addWidget(StatCard(val, lbl, col, ico), i // 3, i % 3)
        layout.addLayout(stats_grid)

        # ── Modules ───────────────────────────────────────────────────────────
        layout.addWidget(_section_label("MODULES — click any card to open"))

        feat_grid = QGridLayout()
        feat_grid.setSpacing(10)

        features = [
            ("👤", "Username Hunt",
             "Async search across 100+ social platforms simultaneously.",
             "Launch →", _TEAL, "username"),
            ("🌐", "Domain Intelligence",
             "WHOIS · DNS · SSL · subdomains · headers · Shodan.",
             "Analyze →", _PURPLE, "domain"),
            ("✉️", "Email OSINT",
             "Validate · SMTP verify · HIBP breach check · Gravatar.",
             "Investigate →", _GREEN, "email"),
            ("🔍", "Google Dorks",
             "60+ dork templates across 6 categories with live search.",
             "Launch →", _ORANGE, "dorks"),
            ("🖥️", "IP Intelligence",
             "Geolocation · port scan · RBL blacklists · Shodan · RDAP.",
             "Lookup →", _RED, "ip"),
            ("📞", "Phone OSINT",
             "Carrier · country · timezone · format variants · search links.",
             "Analyze →", _TEAL, "phone"),
            ("🔐", "Certificate Transparency",
             "crt.sh CT log search · subdomain discovery via SSL certs.",
             "Search →", _YELLOW, "cert"),
            ("📄", "Metadata Extractor",
             "EXIF from images · GPS coordinates · PDF/DOCX author data.",
             "Extract →", _ORANGE, "metadata"),
            ("📋", "Paste & Leak Scanner",
             "GitHub · HackerNews · Reddit · Pastebin — credential search.",
             "Scan →", _PINK, "pastes"),
            ("🖼️", "Reverse Image Search",
             "Load image, preview EXIF/GPS, launch Google Lens · TinEye · Yandex.",
             "Analyze →", _PURPLE, "revimage"),
            ("💀", "Breach Aggregator",
             "HIBP · LeakCheck · BreachDirectory — consolidated severity scoring.",
             "Check →", _RED, "breach"),
            ("👥", "Social Profile OSINT",
             "GitHub · Reddit APIs + profile links for 7 platforms.",
             "Scan →", _GREEN, "social"),
            ("🕷️", "Web Crawler",
             "Spider sites to extract emails, phones, and social links.",
             "Crawl →", _BLUE, "crawler"),
            ("🕸️", "Network Graph",
             "Maltego-style force-directed relationship visualization.",
             "Open →", _PINK, "graph"),
            ("📅", "Investigation Timeline",
             "Chronological event log — auto-captures all scan findings.",
             "View →", _INDIGO, "timeline"),
            ("🗺️", "GeoIP Map Tracker",
             "Batch-resolve IPs and plot on a dark world-map scatter chart.",
             "Track →", _TEAL, "geo"),
            ("📦", "Batch Processor",
             "Upload CSV of targets, run any OSINT module in bulk.",
             "Batch →", _GRAY, "batch"),
            ("📂", "Case Manager",
             "Full investigation lifecycle: notes · status · PDF/JSON export.",
             "Open →", _ORANGE, "cases"),
            ("🛡️", "Counter Surveillance",
             "Connection Guard · Traffic Monitor · Scan Detector · DNS Leak.",
             "Monitor →", _RED, "countersur"),
            ("🌑", "Dark Web Monitor",
             "Ahmia · Intelligence X · psbdmp · DarkSearch exposure scanning.",
             "Scan →", _PURPLE, "darkweb"),
            ("🔬", "Evidence Capture",
             "SHA-256/MD5 page archiving with JSON bundles and headers.",
             "Capture →", _TEAL, "evidence"),
            ("🔌", "Network Diagnostics",
             "Ping · traceroute · port banner grab · rDNS · fingerprinting.",
             "Run →", _ORANGE, "netdiag"),
        ]

        for i, (icon, title, desc, action, color, page) in enumerate(features):
            card = FeatureCard(icon, title, desc, action, color, page)
            card.clicked.connect(self.navigate_to)
            feat_grid.addWidget(card, i // 4, i % 4)

        layout.addLayout(feat_grid)

        # ── Quick actions ─────────────────────────────────────────────────────
        layout.addWidget(_section_label("QUICK ACTIONS"))

        qa_frame = QFrame()
        qa_frame.setStyleSheet("""
            QFrame {
                background: #2c2c2e;
                border: 1px solid #38383a;
                border-radius: 10px;
            }
        """)
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(16, 10, 16, 10)
        qa_layout.setSpacing(8)

        for label, page, color in [
            ("🔎  Username",  "username",  _TEAL),
            ("🌐  Domain",    "domain",    _PURPLE),
            ("🖥️  IP Lookup", "ip",        _RED),
            ("📋  Leaks",     "pastes",    _PINK),
            ("🗺️  Geo Map",   "geo",       _TEAL),
            ("📅  Timeline",  "timeline",  _INDIGO),
            ("📂  Cases",     "cases",     _ORANGE),
            ("🛡️  Monitor",   "countersur",_RED),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}14;
                    border: 1px solid {color}33;
                    color: {color};
                    border-radius: 7px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {color}28;
                    border: 1px solid {color}77;
                }}
                QPushButton:pressed {{ background: {color}3c; }}
            """)
            btn.clicked.connect(lambda _c, p=page: self.navigate_to.emit(p))
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)

        # ── Disclaimer ────────────────────────────────────────────────────────
        disc = QFrame()
        disc.setStyleSheet("""
            QFrame {
                background: #1e1a10;
                border: 1px solid #ff9f0a33;
                border-radius: 10px;
            }
        """)
        dl = QHBoxLayout(disc)
        dl.setContentsMargins(16, 12, 16, 12)
        dl.setSpacing(12)

        warn = QLabel("⚠️")
        warn.setFont(QFont("Ubuntu", 16))
        warn.setStyleSheet("border: none; background: transparent;")
        dl.addWidget(warn)

        disc_text = QLabel(
            "<b style='color:#ff9f0a;'>Educational &amp; Authorized Use Only</b><br>"
            "<span style='color:#636366; font-size:12px;'>"
            "Inspector Rabbit is designed for security research, CTF competitions, "
            "and authorized penetration testing. Only investigate targets you have "
            "explicit permission to examine."
            "</span>"
        )
        disc_text.setWordWrap(True)
        disc_text.setStyleSheet("border: none; background: transparent;")
        dl.addWidget(disc_text, 1)

        layout.addWidget(disc)
        layout.addStretch()
