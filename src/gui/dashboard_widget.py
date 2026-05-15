"""
Inspector Rabbit - Dashboard Widget  v1.3.0
Redesigned home screen with custom-painted hero, accented stat cards,
per-module feature cards, and quick-action bar.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient
)


# ── Hero Banner ────────────────────────────────────────────────────────────────

class HeroBanner(QFrame):
    """
    Custom-painted hero frame. Draws a deep-space gradient with a dot-grid
    overlay, radial cyan glow, corner HUD brackets, and a gradient border line
    along the bottom — all behind whatever child layout is placed inside.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(170)
        self._build_content()

    def _build_content(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 28, 32, 28)
        layout.setSpacing(24)

        # — Text column —
        text_col = QVBoxLayout()
        text_col.setSpacing(8)

        title = QLabel("🐇  Inspector Rabbit")
        title.setFont(QFont("Ubuntu", 30, QFont.Weight.Black))
        title.setStyleSheet("color: #00f5ff; border: none; background: transparent;")
        text_col.addWidget(title)

        subtitle = QLabel(
            "Advanced Open Source Intelligence Suite  ·  v1.3.0  ·  16 Modules"
        )
        subtitle.setFont(QFont("Ubuntu", 12))
        subtitle.setStyleSheet(
            "color: #6e7681; border: none; background: transparent;"
        )
        text_col.addWidget(subtitle)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_row.setContentsMargins(0, 0, 0, 0)
        for text, color in [
            ("OSINT",          "#00f5ff"),
            ("PASSIVE RECON",  "#a78bfa"),
            ("COUNTER-SURV",   "#f85149"),
            ("OPEN SOURCE",    "#3fb950"),
        ]:
            badge = QLabel(text)
            badge.setStyleSheet(f"""
                color: {color};
                background: {color}18;
                border: 1px solid {color}44;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            """)
            tags_row.addWidget(badge)
        tags_row.addStretch()
        text_col.addLayout(tags_row)

        layout.addLayout(text_col, 1)

        # — Rabbit emoji —
        rabbit = QLabel("🐇")
        rabbit.setFont(QFont("Ubuntu", 78))
        rabbit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rabbit.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(rabbit)

    # ── Custom painting ────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # 1. Deep gradient background
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor(0x05, 0x09, 0x14))
        bg.setColorAt(0.45, QColor(0x0a, 0x0e, 0x1c))
        bg.setColorAt(1.0, QColor(0x06, 0x0a, 0x14))
        painter.fillRect(self.rect(), QBrush(bg))

        # 2. Dot grid (cyan, very faint)
        painter.setPen(QPen(QColor(0, 245, 255, 22), 1.2))
        spacing = 26
        for x in range(0, w + spacing, spacing):
            for y in range(0, h + spacing, spacing):
                painter.drawPoint(x, y)

        # 3. Radial glow — top-right quadrant
        glow = QRadialGradient(w * 0.82, h * 0.05, w * 0.55)
        glow.setColorAt(0.0, QColor(0, 245, 255, 38))
        glow.setColorAt(0.45, QColor(0, 245, 255, 10))
        glow.setColorAt(1.0, QColor(0, 245, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        r = int(w * 0.55)
        painter.drawEllipse(int(w * 0.82) - r, int(h * 0.05) - r, r * 2, r * 2)

        # 4. Corner HUD brackets
        pen = QPen(QColor(0, 245, 255, 70), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        m, s = 14, 24   # margin, arm length
        corners = [
            (m,     m,     1,  1),
            (w - m, m,    -1,  1),
            (m,     h - m, 1, -1),
            (w - m, h - m,-1, -1),
        ]
        for px, py, dx, dy in corners:
            painter.drawLine(px, py, px + dx * s, py)
            painter.drawLine(px, py, px, py + dy * s)

        # 5. Bottom border — cyan gradient line
        border = QLinearGradient(0, 0, w, 0)
        border.setColorAt(0.0, QColor(0, 245, 255, 0))
        border.setColorAt(0.2, QColor(0, 245, 255, 110))
        border.setColorAt(0.8, QColor(0, 245, 255, 110))
        border.setColorAt(1.0, QColor(0, 245, 255, 0))
        painter.setBrush(QBrush(border))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, h - 1, w, 1)

        painter.end()
        super().paintEvent(event)


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Stat card with a coloured left-stripe accent and large value label."""

    def __init__(self, value: str, label: str, color: str = "#00f5ff",
                 icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(118)
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: #0d1117;
                border: 1px solid #21262d;
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
            QFrame#statCard:hover {{
                background: #111820;
                border: 1px solid {color}44;
                border-left: 3px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(2)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 20))
        icon_lbl.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        top.addWidget(icon_lbl)
        top.addStretch()

        self.val_label = QLabel(value)
        self.val_label.setFont(QFont("Ubuntu", 26, QFont.Weight.Bold))
        self.val_label.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        top.addWidget(self.val_label)
        layout.addLayout(top)

        layout.addStretch()

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #484f58; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1px; border: none; background: transparent;"
        )
        layout.addWidget(lbl)

    def set_value(self, v: str):
        self.val_label.setText(v)


# ── Feature Card ───────────────────────────────────────────────────────────────

class FeatureCard(QFrame):
    """
    Module feature card. Emits clicked(page_name) when the action button
    is pressed or anywhere on the card is clicked.
    """
    clicked = pyqtSignal(str)

    def __init__(self, icon: str, title: str, description: str,
                 action_label: str, color: str, page_name: str, parent=None):
        super().__init__(parent)
        self._page_name = page_name
        self.setObjectName("featureCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(195)
        self.setStyleSheet(f"""
            QFrame#featureCard {{
                background: #0d1117;
                border: 1px solid #21262d;
                border-top: 3px solid {color}77;
                border-radius: 10px;
            }}
            QFrame#featureCard:hover {{
                background: #111820;
                border: 1px solid {color}44;
                border-top: 3px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Icon + title row
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        header_row.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )
        header_row.addWidget(title_lbl, 1)
        layout.addLayout(header_row)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color: #6e7681; font-size: 11px; "
            "border: none; background: transparent; line-height: 1.4;"
        )
        layout.addWidget(desc_lbl)

        layout.addStretch()

        self.action_btn = QPushButton(action_label)
        self.action_btn.setFixedHeight(30)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}16;
                border: 1px solid {color}40;
                color: {color};
                border-radius: 7px;
                padding: 3px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {color}2c;
                border: 1px solid {color}88;
            }}
            QPushButton:pressed {{
                background: {color}40;
            }}
        """)
        self.action_btn.clicked.connect(self._on_click)
        layout.addWidget(self.action_btn)

    def _on_click(self):
        self.clicked.emit(self._page_name)

    def mousePressEvent(self, event):
        self.clicked.emit(self._page_name)
        super().mousePressEvent(event)


# ── Section Divider ────────────────────────────────────────────────────────────

def _section_label(text: str) -> QWidget:
    """Styled section divider label."""
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(10)

    accent = QFrame()
    accent.setFixedSize(3, 14)
    accent.setStyleSheet("background: #00f5ff; border-radius: 1px;")
    h.addWidget(accent)

    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #484f58; font-size: 10px; font-weight: 700; "
        "letter-spacing: 1.5px; background: transparent;"
    )
    h.addWidget(lbl)
    h.addStretch()
    return row


# ── Dashboard Widget ───────────────────────────────────────────────────────────

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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(24)

        # ── Hero banner ────────────────────────────────────────────────────────
        layout.addWidget(HeroBanner())

        # ── Stat strip ────────────────────────────────────────────────────────
        layout.addWidget(_section_label("CAPABILITIES"))

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        stats_grid.setContentsMargins(0, 0, 0, 0)

        stat_data = [
            ("100+",  "Sites Checked",      "#00f5ff", "🌐"),
            ("16+",   "OSINT Modules",       "#a78bfa", "🔧"),
            ("8",     "DNS Record Types",    "#34d399", "📡"),
            ("60+",   "Dork Templates",      "#fb923c", "🔍"),
            ("3",     "Export Formats",      "#60a5fa", "📄"),
            ("Live",  "Graph Visualization", "#f472b6", "🕸️"),
        ]
        for i, (val, lbl, col, ico) in enumerate(stat_data):
            stats_grid.addWidget(StatCard(val, lbl, col, ico), i // 3, i % 3)
        layout.addLayout(stats_grid)

        # ── Feature cards ─────────────────────────────────────────────────────
        layout.addWidget(_section_label("MODULES — click any card to open"))

        feat_grid = QGridLayout()
        feat_grid.setSpacing(12)
        feat_grid.setContentsMargins(0, 0, 0, 0)

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

            ("🕵️‍♂️", "Dark Web Search",
             "Search onion services via public gateways without Tor proxy.",
             "Start Deep Search →", "#7c3aed", "darkweb"),

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
             "watch who's watching you.",
             "Open Monitor →", "#f85149", "countersur"),
        ]

        for i, (icon, title, desc, action, color, page) in enumerate(features):
            card = FeatureCard(icon, title, desc, action, color, page)
            card.clicked.connect(self.navigate_to)
            feat_grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(feat_grid)

        # ── Quick actions ─────────────────────────────────────────────────────
        layout.addWidget(_section_label("QUICK ACTIONS"))

        qa_frame = QFrame()
        qa_frame.setStyleSheet("""
            QFrame {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 10px;
            }
        """)
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(18, 12, 18, 12)
        qa_layout.setSpacing(10)

        quick_actions = [
            ("🔎  Username Search",  "username",  "#00f5ff"),
            ("🌐  Analyze Domain",   "domain",    "#a78bfa"),
            ("🖥️  IP Lookup",        "ip",        "#f87171"),
            ("📋  Scan for Leaks",   "pastes",    "#f472b6"),
            ("🕸️  Open Graph",       "graph",     "#f472b6"),
            ("📅  View Timeline",    "timeline",  "#818cf8"),
        ]
        for label, page, color in quick_actions:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}12;
                    border: 1px solid {color}30;
                    color: {color};
                    border-radius: 8px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {color}24;
                    border: 1px solid {color}77;
                }}
                QPushButton:pressed {{
                    background: {color}38;
                }}
            """)
            btn.clicked.connect(lambda _checked, p=page: self.navigate_to.emit(p))
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)

        # ── Disclaimer ────────────────────────────────────────────────────────
        disc_frame = QFrame()
        disc_frame.setStyleSheet("""
            QFrame {
                background: #120c04;
                border: 1px solid #e3b34130;
                border-radius: 10px;
            }
        """)
        disc_layout = QHBoxLayout(disc_frame)
        disc_layout.setContentsMargins(18, 12, 18, 12)
        disc_layout.setSpacing(14)

        warn_icon = QLabel("⚠️")
        warn_icon.setFont(QFont("Ubuntu", 18))
        warn_icon.setStyleSheet("border: none; background: transparent;")
        disc_layout.addWidget(warn_icon)

        disc_text = QLabel(
            "<b style='color:#e3b341;'>Educational &amp; Authorized Use Only</b><br>"
            "<span style='color:#6e7681; font-size:12px;'>"
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
