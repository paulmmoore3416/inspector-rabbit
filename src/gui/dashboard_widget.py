"""
Inspector Rabbit - Dashboard Widget
Home screen with stats, quick actions, and recent activity
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient


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
        top_row.addWidget(icon_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        val_label = QLabel(value)
        val_label.setFont(QFont("Ubuntu", 26, QFont.Weight.Bold))
        val_label.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        layout.addWidget(val_label)

        lbl_label = QLabel(label)
        lbl_label.setFont(QFont("Ubuntu", 11))
        lbl_label.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        layout.addWidget(lbl_label)

        self.val_label = val_label

    def set_value(self, v: str):
        self.val_label.setText(v)


class FeatureCard(QFrame):
    def __init__(self, icon: str, title: str, description: str,
                 action_label: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#card {{
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 12px;
            }}
            QFrame#card:hover {{
                border: 1px solid {color}55;
                background: #1a1f2a;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Ubuntu", 28))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Ubuntu", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #8b949e; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        btn = QPushButton(action_label)
        btn.setObjectName("primaryBtn")
        btn.setFixedHeight(34)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}22;
                border: 1px solid {color}44;
                color: {color};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {color}33;
                border: 1px solid {color};
            }}
        """)
        layout.addWidget(btn)
        self.action_btn = btn


class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        # Animate stats
        self._timer = QTimer()
        self._timer.singleShot(200, self._animate_stats)

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

        # ===== Header =====
        header = self._build_header()
        layout.addWidget(header)

        # ===== Stats Row =====
        stats_label = QLabel("CAPABILITIES")
        stats_label.setObjectName("sectionLabel")
        stats_label.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        stats_label.setStyleSheet("color: #484f58; letter-spacing: 2px; font-size: 10px;")
        layout.addWidget(stats_label)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.stat_sites = StatCard("100+", "Sites Monitored", "#00f5ff", "🌐")
        self.stat_modules = StatCard("6", "OSINT Modules", "#a78bfa", "🔧")
        self.stat_dns = StatCard("8", "DNS Record Types", "#34d399", "📡")
        self.stat_dorks = StatCard("60+", "Dork Templates", "#fb923c", "🔍")
        self.stat_exports = StatCard("3", "Export Formats", "#60a5fa", "📄")
        self.stat_viz = StatCard("Live", "Graph Visualization", "#f472b6", "🕸️")

        cards = [
            self.stat_sites, self.stat_modules, self.stat_dns,
            self.stat_dorks, self.stat_exports, self.stat_viz
        ]
        for i, card in enumerate(cards):
            stats_grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(stats_grid)

        # ===== Features =====
        feat_label = QLabel("MODULES")
        feat_label.setStyleSheet("color: #484f58; letter-spacing: 2px; font-size: 10px; font-weight: 700;")
        layout.addWidget(feat_label)

        feat_grid = QGridLayout()
        feat_grid.setSpacing(16)

        features = [
            ("👤", "Username Search", "Hunt usernames across 100+ social platforms simultaneously with async checking.", "Launch Search →", "#00f5ff"),
            ("🌐", "Domain Intelligence", "WHOIS, DNS records, SSL certs, subdomain enumeration, Shodan integration.", "Analyze Domain →", "#a78bfa"),
            ("✉️", "Email OSINT", "Validate emails, SMTP verification, breach detection, Gravatar lookup.", "Investigate Email →", "#34d399"),
            ("🔍", "Google Dorks", "60+ pre-built dork templates across 6 categories with live search execution.", "Launch Dorks →", "#fb923c"),
            ("🕷️", "Web Crawler", "Spider websites to extract emails, phones, social links, and form data.", "Start Crawling →", "#60a5fa"),
            ("🕸️", "Network Graph", "Visualize relationships between entities with interactive force-directed graph.", "Open Graph →", "#f472b6"),
        ]

        for i, (icon, title, desc, action, color) in enumerate(features):
            card = FeatureCard(icon, title, desc, action, color)
            feat_grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(feat_grid)

        # ===== Disclaimer =====
        disc_frame = QFrame()
        disc_frame.setObjectName("card")
        disc_frame.setStyleSheet("""
            QFrame#card {
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
            "<b style='color:#e3b341;'>Educational & Authorized Use Only</b><br>"
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

        # Left text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title = QLabel("🐇 Inspector Rabbit")
        title.setFont(QFont("Ubuntu", 28, QFont.Weight.Black))
        title.setStyleSheet("color: #00f5ff;  border: none; background: transparent;")
        text_layout.addWidget(title)

        subtitle = QLabel("Advanced Open Source Intelligence Suite")
        subtitle.setFont(QFont("Ubuntu", 13))
        subtitle.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        text_layout.addWidget(subtitle)

        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(8)
        for tag in ["Sherlock", "Maltego", "SpiderFoot", "Shodan", "Recon-ng", "Dorks"]:
            tag_lbl = QLabel(tag)
            tag_lbl.setStyleSheet("""
                color: #8b949e;
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 3px 10px;
                font-size: 11px;
            """)
            tags_layout.addWidget(tag_lbl)
        tags_layout.addStretch()
        text_layout.addLayout(tags_layout)

        layout.addLayout(text_layout, 1)

        # Right - big emoji
        rabbit = QLabel("🐇")
        rabbit.setFont(QFont("Ubuntu", 64))
        rabbit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rabbit.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(rabbit)

        return header

    def _animate_stats(self):
        # Stats are static for now, but this is where we'd animate counters
        pass
