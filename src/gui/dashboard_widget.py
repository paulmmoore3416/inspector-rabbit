"""
Inspector Rabbit - Dashboard Widget  v1.5.0
Professional redesign: clean hero, refined stat cards, per-module feature
cards, and a quick-action toolbar. No custom paintEvent — pure QSS.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


# ── Hero Banner ────────────────────────────────────────────────────────────────

class HeroBanner(QFrame):
    """Clean, professional hero — gradient background, no paint noise."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(148)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0d1628, stop:0.5 #0f1d35, stop:1 #0a1220);
                border: 1px solid #1e2a3a;
                border-radius: 10px;
            }
        """)
        self._build_content()

    def _build_content(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 22, 28, 22)
        layout.setSpacing(20)

        # ── Left: text ────────────────────────────────────────────────────────
        text_col = QVBoxLayout()
        text_col.setSpacing(7)

        title = QLabel("Inspector Rabbit")
        title.setFont(QFont("Ubuntu", 26, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0; border: none; background: transparent;")
        text_col.addWidget(title)

        subtitle = QLabel(
            "Advanced Open Source Intelligence Suite  ·  v1.4.0  ·  24 Modules"
        )
        subtitle.setFont(QFont("Ubuntu", 12))
        subtitle.setStyleSheet(
            "color: #475569; border: none; background: transparent;"
        )
        text_col.addWidget(subtitle)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_row.setContentsMargins(0, 0, 0, 0)
        for text, color in [
            ("OSINT",         "#3b82f6"),
            ("PASSIVE RECON", "#8b5cf6"),
            ("COUNTER-SURV",  "#ef4444"),
            ("OPEN SOURCE",   "#10b981"),
        ]:
            badge = QLabel(text)
            badge.setStyleSheet(f"""
                color: {color};
                background: {color}18;
                border: 1px solid {color}40;
                border-radius: 4px;
                padding: 2px 9px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            """)
            tags_row.addWidget(badge)
        tags_row.addStretch()
        text_col.addLayout(tags_row)

        layout.addLayout(text_col, 1)

        # ── Right: rabbit emoji ───────────────────────────────────────────────
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
                background: #111827;
                border: 1px solid #1e2a3a;
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
            QFrame#statCard:hover {{
                background: #1a2233;
                border: 1px solid #2d3f55;
                border-left: 3px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 18))
        icon_lbl.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        top.addWidget(icon_lbl)
        top.addStretch()

        self.val_lbl = QLabel(value)
        self.val_lbl.setFont(QFont("Ubuntu", 24, QFont.Weight.Bold))
        self.val_lbl.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        top.addWidget(self.val_lbl)
        layout.addLayout(top)

        layout.addStretch()

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #475569; font-size: 10px; font-weight: 700; "
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
                background: #111827;
                border: 1px solid #1e2a3a;
                border-top: 2px solid {color}66;
                border-radius: 8px;
            }}
            QFrame#featureCard:hover {{
                background: #1a2233;
                border: 1px solid #2d3f55;
                border-top: 2px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        # Icon + title row
        hr = QHBoxLayout()
        hr.setSpacing(8)
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 22))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        hr.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        hr.addWidget(title_lbl, 1)
        layout.addLayout(hr)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #64748b; font-size: 11px; "
            "border: none; background: transparent;"
        )
        layout.addWidget(desc_lbl)
        layout.addStretch()

        self.action_btn = QPushButton(action_label)
        self.action_btn.setFixedHeight(28)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}14;
                border: 1px solid {color}38;
                color: {color};
                border-radius: 5px;
                padding: 2px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {color}28;
                border: 1px solid {color}77;
            }}
            QPushButton:pressed {{
                background: {color}3c;
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
    accent.setStyleSheet("background: #3b82f6; border-radius: 1px;")
    h.addWidget(accent)

    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #475569; font-size: 10px; font-weight: 700; "
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
            ("100+",  "Sites Checked",      "#06b6d4", "🌐"),
            ("24+",   "OSINT Modules",       "#8b5cf6", "🔧"),
            ("8",     "DNS Record Types",    "#10b981", "📡"),
            ("60+",   "Dork Templates",      "#f59e0b", "🔍"),
            ("3",     "Export Formats",      "#3b82f6", "📄"),
            ("Live",  "Graph Visualization", "#ec4899", "🕸️"),
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
             "Launch →", "#06b6d4", "username"),
            ("🌐", "Domain Intelligence",
             "WHOIS · DNS · SSL · subdomains · headers · Shodan.",
             "Analyze →", "#8b5cf6", "domain"),
            ("✉️", "Email OSINT",
             "Validate · SMTP verify · HIBP breach check · Gravatar.",
             "Investigate →", "#10b981", "email"),
            ("🔍", "Google Dorks",
             "60+ dork templates across 6 categories with live search.",
             "Launch →", "#f59e0b", "dorks"),
            ("🖥️", "IP Intelligence",
             "Geolocation · port scan · RBL blacklists · Shodan · RDAP.",
             "Lookup →", "#ef4444", "ip"),
            ("📞", "Phone OSINT",
             "Carrier · country · timezone · format variants · search links.",
             "Analyze →", "#22d3ee", "phone"),
            ("🔐", "Certificate Transparency",
             "crt.sh CT log search · subdomain discovery via SSL certs.",
             "Search →", "#fbbf24", "cert"),
            ("📄", "Metadata Extractor",
             "EXIF from images · GPS coordinates · PDF/DOCX author data.",
             "Extract →", "#fb923c", "metadata"),
            ("📋", "Paste & Leak Scanner",
             "GitHub · HackerNews · Reddit · Pastebin — credential search.",
             "Scan →", "#ec4899", "pastes"),
            ("🖼️", "Reverse Image Search",
             "Load image, preview EXIF/GPS, launch Google Lens · TinEye · Yandex.",
             "Analyze →", "#d946ef", "revimage"),
            ("💀", "Breach Aggregator",
             "HIBP · LeakCheck · BreachDirectory — consolidated severity scoring.",
             "Check →", "#f87171", "breach"),
            ("👥", "Social Profile OSINT",
             "GitHub · Reddit APIs + profile links for 7 platforms.",
             "Scan →", "#4ade80", "social"),
            ("🕷️", "Web Crawler",
             "Spider sites to extract emails, phones, and social links.",
             "Crawl →", "#60a5fa", "crawler"),
            ("🕸️", "Network Graph",
             "Maltego-style force-directed relationship visualization.",
             "Open →", "#ec4899", "graph"),
            ("📅", "Investigation Timeline",
             "Chronological event log — auto-captures all scan findings.",
             "View →", "#818cf8", "timeline"),
            ("🗺️", "GeoIP Map Tracker",
             "Batch-resolve IPs and plot on a dark world-map scatter chart.",
             "Track →", "#06b6d4", "geo"),
            ("📦", "Batch Processor",
             "Upload CSV of targets, run any OSINT module in bulk.",
             "Batch →", "#94a3b8", "batch"),
            ("📂", "Case Manager",
             "Full investigation lifecycle: notes · status · PDF/JSON export.",
             "Open →", "#f59e0b", "cases"),
            ("🛡️", "Counter Surveillance",
             "Connection Guard · Traffic Monitor · Scan Detector · DNS Leak.",
             "Monitor →", "#ef4444", "countersur"),
            ("🌑", "Dark Web Monitor",
             "Ahmia · Intelligence X · psbdmp · DarkSearch exposure scanning.",
             "Scan →", "#a855f7", "darkweb"),
            ("🔬", "Evidence Capture",
             "SHA-256/MD5 page archiving with JSON bundles and headers.",
             "Capture →", "#38bdf8", "evidence"),
            ("🔌", "Network Diagnostics",
             "Ping · traceroute · port banner grab · rDNS · fingerprinting.",
             "Run →", "#fb923c", "netdiag"),
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
                background: #111827;
                border: 1px solid #1e2a3a;
                border-radius: 8px;
            }
        """)
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(16, 10, 16, 10)
        qa_layout.setSpacing(8)

        for label, page, color in [
            ("🔎  Username",   "username",  "#06b6d4"),
            ("🌐  Domain",     "domain",    "#8b5cf6"),
            ("🖥️  IP Lookup",  "ip",        "#ef4444"),
            ("📋  Leaks",      "pastes",    "#ec4899"),
            ("🗺️  Geo Map",    "geo",       "#06b6d4"),
            ("📅  Timeline",   "timeline",  "#818cf8"),
            ("📂  Cases",      "cases",     "#f59e0b"),
            ("🛡️  Monitor",    "countersur","#ef4444"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}10;
                    border: 1px solid {color}2a;
                    color: {color};
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {color}20;
                    border: 1px solid {color}66;
                }}
                QPushButton:pressed {{ background: {color}30; }}
            """)
            btn.clicked.connect(lambda _c, p=page: self.navigate_to.emit(p))
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)

        # ── Disclaimer ────────────────────────────────────────────────────────
        disc = QFrame()
        disc.setStyleSheet("""
            QFrame {
                background: #140e04;
                border: 1px solid #92400e33;
                border-radius: 8px;
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
            "<b style='color:#f59e0b;'>Educational &amp; Authorized Use Only</b><br>"
            "<span style='color:#64748b; font-size:12px;'>"
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
