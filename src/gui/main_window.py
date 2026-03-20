"""
Inspector Rabbit - Main Application Window
"""

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QSizePolicy, QStatusBar,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QApplication,
    QScrollArea
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QLinearGradient, QPen, QAction

from .styles import MAIN_STYLE, SIDEBAR_STYLE
from .dashboard_widget import DashboardWidget
from .username_widget import UsernameWidget
from .domain_widget import DomainWidget
from .email_widget import EmailWidget
from .dorks_widget import DorksWidget
from .graph_widget import GraphWidget
from .crawler_widget import CrawlerWidget
from .settings_widget import SettingsWidget
from .ip_widget import IpWidget
from .phone_widget import PhoneWidget
from .cert_widget import CertWidget
from .metadata_widget import MetadataWidget
from .paste_widget import PasteWidget
from .timeline_widget import TimelineWidget
from .counter_surveillance_widget import CounterSurveillanceWidget
from .reverse_image_widget import ReverseImageWidget
from .breach_widget import BreachWidget
from .social_widget import SocialWidget
from .geo_widget import GeoWidget
from .darkweb_widget import DarkWebWidget
from .evidence_widget import EvidenceWidget
from .netdiag_widget import NetDiagWidget
from .batch_widget import BatchWidget
from .case_widget import CaseWidget


NAV_ITEMS = [
    ("🏠", "Dashboard",    "dashboard"),
    ("👤", "Username",     "username"),
    ("🌐", "Domain",       "domain"),
    ("✉️",  "Email",        "email"),
    ("🔍", "Dorks",        "dorks"),
    ("🖥️", "IP Intel",     "ip"),
    ("📞", "Phone",        "phone"),
    ("🔐", "Cert CT",      "cert"),
    ("📄", "Metadata",     "metadata"),
    ("📋", "Pastes",       "pastes"),
    ("🖼️", "Rev. Image",   "revimage"),
    ("💀", "Breach Agg",   "breach"),
    ("👥", "Social OSINT", "social"),
    ("🕷️",  "Crawler",     "crawler"),
    ("🕸️",  "Graph",       "graph"),
    ("📅", "Timeline",     "timeline"),
    ("🗺️", "Geo Map",      "geo"),
    ("📦", "Batch",        "batch"),
    ("📂", "Cases",        "cases"),
    ("🛡️",  "Counter Sur", "countersur"),
    ("🌑", "Dark Web",     "darkweb"),
    ("🔬", "Evidence",     "evidence"),
    ("🔌", "Net Diag",     "netdiag"),
    ("⚙️",  "Settings",    "settings"),
]

# Sidebar groups — references page names from NAV_ITEMS
SIDEBAR_GROUPS = [
    (None, ["dashboard"]),
    ("INTELLIGENCE", [
        "username", "domain", "email", "dorks",
        "ip", "phone", "cert", "metadata", "pastes",
        "revimage", "breach", "social",
    ]),
    ("ANALYSIS", [
        "crawler", "graph", "timeline", "geo", "batch", "cases",
    ]),
    ("SECURITY", [
        "countersur", "darkweb", "evidence", "netdiag",
    ]),
    ("SYSTEM", ["settings"]),
]


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setStyleSheet(SIDEBAR_STYLE)

        self._btns: dict[int, QPushButton] = {}   # NAV_ITEMS index → button
        _name_to_idx = {name: i for i, (_, _, name) in enumerate(NAV_ITEMS)}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Logo area ─────────────────────────────────────────────────────────
        logo_frame = QWidget()
        logo_frame.setStyleSheet("background: transparent;")
        ll = QHBoxLayout(logo_frame)
        ll.setContentsMargins(14, 14, 14, 14)
        ll.setSpacing(10)

        rabbit_lbl = QLabel("🐇")
        rabbit_lbl.setFont(QFont("Ubuntu", 20))
        rabbit_lbl.setStyleSheet("border: none; background: transparent;")
        ll.addWidget(rabbit_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_lbl = QLabel("Inspector Rabbit")
        name_lbl.setObjectName("logoLabel")
        name_lbl.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        ver_lbl = QLabel("OSINT SUITE  ·  v1.5.0")
        ver_lbl.setObjectName("logoSubLabel")
        ver_lbl.setFont(QFont("Ubuntu", 8))
        text_col.addWidget(name_lbl)
        text_col.addWidget(ver_lbl)
        ll.addLayout(text_col, 1)
        outer.addWidget(logo_frame)

        # ── Divider ───────────────────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: #1a2030; margin: 0;")
        div.setFixedHeight(1)
        outer.addWidget(div)

        # ── Scrollable nav ────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: #070b12; width: 3px; border: none; }
            QScrollBar::handle:vertical {
                background: #1a2030; border-radius: 1px; min-height: 16px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        nav = QWidget()
        nav.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 6, 0, 12)
        nav_layout.setSpacing(0)

        for section_title, page_names in SIDEBAR_GROUPS:
            if section_title:
                sec = QLabel(section_title)
                sec.setObjectName("sidebarSection")
                sec.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
                nav_layout.addWidget(sec)

            for page_name in page_names:
                if page_name not in _name_to_idx:
                    continue
                idx = _name_to_idx[page_name]
                emoji, label, _ = NAV_ITEMS[idx]

                btn = QPushButton(f"  {emoji}  {label}")
                btn.setObjectName("sidebarBtn")
                btn.setCheckable(True)
                btn.setFixedHeight(36)
                btn.setFont(QFont("Ubuntu", 12))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _chk, i=idx: self._on_click(i))
                self._btns[idx] = btn
                nav_layout.addWidget(btn)

        nav_layout.addStretch()
        scroll.setWidget(nav)
        outer.addWidget(scroll, 1)

        # Select dashboard by default
        if 0 in self._btns:
            self._btns[0].setChecked(True)

    def _on_click(self, idx: int):
        self.select(idx)
        self.page_changed.emit(idx)

    def select(self, idx: int):
        for i, btn in self._btns.items():
            btn.setChecked(i == idx)

    # Backwards-compat property used by navigate_to()
    @property
    def buttons(self):
        return [self._btns[i] for i in sorted(self._btns)]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inspector Rabbit — Advanced OSINT Suite")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)
        self.setStyleSheet(MAIN_STYLE)

        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._connect_signals()

        # Status ticker
        self._ticker = QTimer()
        self._ticker.timeout.connect(self._tick_status)
        self._ticker.start(5000)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Page stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { border: none; }")
        main_layout.addWidget(self.stack, 1)

        # Pages (order must match NAV_ITEMS)
        self.dashboard        = DashboardWidget()
        self.username_page    = UsernameWidget()
        self.domain_page      = DomainWidget()
        self.email_page       = EmailWidget()
        self.dorks_page       = DorksWidget()
        self.ip_page          = IpWidget()
        self.phone_page       = PhoneWidget()
        self.cert_page        = CertWidget()
        self.metadata_page    = MetadataWidget()
        self.paste_page       = PasteWidget()
        self.revimage_page    = ReverseImageWidget()
        self.breach_page      = BreachWidget()
        self.social_page      = SocialWidget()
        self.crawler_page     = CrawlerWidget()
        self.graph_page       = GraphWidget()
        self.timeline_page    = TimelineWidget()
        self.geo_page         = GeoWidget()
        self.batch_page       = BatchWidget()
        self.cases_page       = CaseWidget()
        self.countersur_page  = CounterSurveillanceWidget()
        self.darkweb_page     = DarkWebWidget()
        self.evidence_page    = EvidenceWidget()
        self.netdiag_page     = NetDiagWidget()
        self.settings_page    = SettingsWidget()

        # Order MUST match NAV_ITEMS exactly
        for page in [
            self.dashboard,       # 0  dashboard
            self.username_page,   # 1  username
            self.domain_page,     # 2  domain
            self.email_page,      # 3  email
            self.dorks_page,      # 4  dorks
            self.ip_page,         # 5  ip
            self.phone_page,      # 6  phone
            self.cert_page,       # 7  cert
            self.metadata_page,   # 8  metadata
            self.paste_page,      # 9  pastes
            self.revimage_page,   # 10 revimage
            self.breach_page,     # 11 breach
            self.social_page,     # 12 social
            self.crawler_page,    # 13 crawler
            self.graph_page,      # 14 graph
            self.timeline_page,   # 15 timeline
            self.geo_page,        # 16 geo
            self.batch_page,      # 17 batch
            self.cases_page,      # 18 cases
            self.countersur_page, # 19 countersur
            self.darkweb_page,    # 20 darkweb
            self.evidence_page,   # 21 evidence
            self.netdiag_page,    # 22 netdiag
            self.settings_page,   # 23 settings
        ]:
            self.stack.addWidget(page)

    def _setup_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background: #010409;
                border-bottom: 1px solid #21262d;
                color: #8b949e;
                font-size: 12px;
            }
            QMenuBar::item:selected {
                background: #161b22;
                color: #00f5ff;
                border-radius: 4px;
            }
            QMenu {
                background: #161b22;
                border: 1px solid #21262d;
                color: #c9d1d9;
            }
            QMenu::item:selected {
                background: #1f6feb;
                color: #ffffff;
            }
        """)

        # File menu
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Report...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_report)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        clear_graph = QAction("Clear Graph", self)
        clear_graph.triggered.connect(self._clear_graph)
        tools_menu.addAction(clear_graph)
        export_graph = QAction("Export Graph as PNG", self)
        export_graph.triggered.connect(self._export_graph)
        tools_menu.addAction(export_graph)
        tools_menu.addSeparator()
        clear_timeline = QAction("Clear Timeline", self)
        clear_timeline.triggered.connect(lambda: self.timeline_page._clear_timeline())
        tools_menu.addAction(clear_timeline)

        # Navigate menu
        nav_menu = menubar.addMenu("Navigate")
        for i, (emoji, label, name) in enumerate(NAV_ITEMS):
            act = QAction(f"{emoji}  {label}", self)
            act.triggered.connect(lambda checked, idx=i: self._navigate(idx))
            nav_menu.addAction(act)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About Inspector Rabbit", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background: #010409;
                border-top: 1px solid #21262d;
                color: #484f58;
                font-size: 11px;
            }
        """)
        self._status_label = QLabel("🐇 Inspector Rabbit — Ready")
        self.statusbar.addWidget(self._status_label)
        self._activity_label = QLabel("")
        self._activity_label.setStyleSheet("color: #00f5ff;")
        self.statusbar.addPermanentWidget(self._activity_label)

    def _connect_signals(self):
        self.sidebar.page_changed.connect(self.stack.setCurrentIndex)

        # Dashboard navigation — cards and quick-action buttons
        self.dashboard.navigate_to.connect(self.navigate_to)

        # send_to_graph wiring
        for page in [
            self.username_page, self.domain_page, self.email_page,
            self.ip_page, self.phone_page, self.cert_page,
            self.revimage_page, self.breach_page, self.social_page,
            self.geo_page, self.evidence_page, self.netdiag_page,
            self.batch_page,
        ]:
            if hasattr(page, 'send_to_graph'):
                page.send_to_graph.connect(self._add_to_graph)

        # status_message wiring — statusbar + counter surveillance terminal
        osint_pages = [
            ('username',  self.username_page),
            ('domain',    self.domain_page),
            ('email',     self.email_page),
            ('dorks',     self.dorks_page),
            ('crawler',   self.crawler_page),
            ('ip',        self.ip_page),
            ('phone',     self.phone_page),
            ('cert',      self.cert_page),
            ('metadata',  self.metadata_page),
            ('pastes',    self.paste_page),
            ('timeline',  self.timeline_page),
            ('revimage',  self.revimage_page),
            ('breach',    self.breach_page),
            ('social',    self.social_page),
            ('geo',       self.geo_page),
            ('darkweb',   self.darkweb_page),
            ('evidence',  self.evidence_page),
            ('netdiag',   self.netdiag_page),
            ('batch',     self.batch_page),
            ('cases',     self.cases_page),
        ]
        for mod_name, page in osint_pages:
            if hasattr(page, 'status_message'):
                page.status_message.connect(self._set_status)
                # Relay scan activity into the Counter Surveillance terminal
                page.status_message.connect(
                    lambda m, mn=mod_name, pg=page: self._relay_to_countersur(mn, pg, m)
                )

        self.countersur_page.status_message.connect(self._set_status)

        # Timeline auto-capture from OSINT pages
        for mod_name, page in osint_pages:
            if hasattr(page, 'status_message'):
                page.status_message.connect(
                    lambda m, mn=mod_name, pg=page: self._log_to_timeline(mn, pg, m)
                )

        # Settings propagated to all pages that accept them
        self.settings_page.settings_changed.connect(self._apply_settings)

    def _relay_to_countersur(self, mod_name: str, page, message: str):
        """Relay OSINT module activity to the Counter Surveillance terminal."""
        if not message or message.startswith('🐇 Inspector Rabbit'):
            return
        target = self._extract_target(page)
        self.countersur_page.log_scan_event(mod_name, target or '—', message)

    def _log_to_timeline(self, ev_type: str, page, message: str):
        """Auto-capture status messages as timeline events."""
        target = self._extract_target(page)
        if message and not message.startswith('🐇 Inspector Rabbit'):
            self.timeline_page.add_event(ev_type, target or '—', message)

    @staticmethod
    def _extract_target(page) -> str:
        for attr in ('ip_input', 'domain_input', 'email_input', 'query_input',
                     'url_input', 'phone_input', 'username_input'):
            widget = getattr(page, attr, None)
            if widget and hasattr(widget, 'text'):
                val = widget.text().strip()
                if val:
                    return val
        return ''

    def _navigate(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.sidebar.select(idx)

    def _add_to_graph(self, data: dict):
        self.graph_page.add_data(data)
        self._set_status(f"Added to graph: {data.get('label', 'node')}")

    def _clear_graph(self):
        self.graph_page.clear_graph()
        self._set_status("Graph cleared")

    def _export_graph(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Graph", os.path.expanduser("~/inspector_rabbit_graph.png"),
            "PNG Images (*.png)"
        )
        if path:
            self.graph_page.export_image(path)
            self._set_status(f"Graph exported: {path}")

    def _export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", os.path.expanduser("~/inspector_rabbit_report.html"),
            "HTML Reports (*.html);;JSON (*.json);;PDF (*.pdf)"
        )
        if path:
            self._set_status(f"Report saved: {path}")

    def _apply_settings(self, settings: dict):
        for page in [
            self.username_page, self.domain_page, self.email_page,
            self.ip_page, self.phone_page, self.cert_page,
            self.metadata_page, self.paste_page,
            self.revimage_page, self.breach_page, self.social_page,
            self.geo_page, self.darkweb_page, self.evidence_page,
            self.netdiag_page, self.batch_page, self.cases_page,
        ]:
            if hasattr(page, 'apply_settings'):
                page.apply_settings(settings)
        self._set_status("Settings applied to all modules")

    def _show_about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About Inspector Rabbit")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText("""
        <div style='text-align:center; color:#c9d1d9;'>
        <h2 style='color:#00f5ff;'>🐇 Inspector Rabbit</h2>
        <p style='color:#8b949e;'>Advanced OSINT Intelligence Suite</p>
        <br>
        <p><b>Version:</b> 1.5.0</p>
        <p><b>Modules:</b> 24 OSINT + 4 Counter-Surveillance capabilities</p>
        <p><b>Purpose:</b> Educational &amp; Authorized Security Research</p>
        <br>
        <p style='color:#f85149; font-size:11px;'>
        ⚠️ For educational and authorized use only.<br>
        Unauthorized use against systems you don't own may be illegal.
        </p>
        </div>
        """)
        msg.setStyleSheet("QMessageBox { background: #0d1117; color: #c9d1d9; }")
        msg.exec()

    def _set_status(self, msg: str):
        self._status_label.setText(f"🐇 {msg}")
        self._activity_label.setText("●")
        QTimer.singleShot(3000, lambda: self._activity_label.setText(""))

    def _tick_status(self):
        current = self.stack.currentIndex()
        page_names = [item[1] for item in NAV_ITEMS]
        if current < len(page_names):
            self._status_label.setText(f"🐇 Inspector Rabbit — {page_names[current]}")

    def navigate_to(self, page_name: str):
        for i, (_, _, name) in enumerate(NAV_ITEMS):
            if name == page_name:
                self._navigate(i)
                break

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Quit Inspector Rabbit",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
