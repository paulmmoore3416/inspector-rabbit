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


NAV_ITEMS = [
    ("🏠", "Dashboard",   "dashboard"),
    ("👤", "Username",    "username"),
    ("🌐", "Domain",      "domain"),
    ("✉️",  "Email",       "email"),
    ("🔍", "Dorks",       "dorks"),
    ("🖥️", "IP Intel",    "ip"),
    ("📞", "Phone",       "phone"),
    ("🔐", "Cert CT",     "cert"),
    ("📄", "Metadata",    "metadata"),
    ("📋", "Pastes",      "pastes"),
    ("🕷️",  "Crawler",    "crawler"),
    ("🕸️",  "Graph",      "graph"),
    ("📅", "Timeline",    "timeline"),
    ("⚙️",  "Settings",   "settings"),
]


class SidebarButton(QPushButton):
    def __init__(self, emoji: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarBtn")
        self.setCheckable(True)
        self.setFixedHeight(60)
        self.setText(f"{emoji}\n{label}")
        self.setFont(QFont("Ubuntu", 9))
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(88)
        self.setStyleSheet(SIDEBAR_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Logo area
        logo_frame = QWidget()
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 10, 0, 10)
        logo_label = QLabel("🐇")
        logo_label.setObjectName("logoLabel")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFont(QFont("Ubuntu", 26))
        logo_sub = QLabel("OSINT")
        logo_sub.setObjectName("logoSubLabel")
        logo_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_sub.setFont(QFont("Ubuntu", 8, QFont.Weight.Bold))
        logo_sub.setStyleSheet("color: #00f5ff; letter-spacing: 3px; font-size: 8px;")
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(logo_sub)
        outer.addWidget(logo_frame)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: #21262d; margin: 0 8px;")
        divider.setFixedHeight(1)
        outer.addWidget(divider)
        outer.addSpacing(4)

        # Scrollable nav area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #010409; width: 4px; border: none;
            }
            QScrollBar::handle:vertical {
                background: #21262d; border-radius: 2px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.buttons = []
        for i, (emoji, label, _) in enumerate(NAV_ITEMS):
            btn = SidebarButton(emoji, label)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            nav_layout.addWidget(btn)
            self.buttons.append(btn)

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        outer.addWidget(scroll, 1)

        # Version label
        ver_label = QLabel("v1.1.0")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_label.setStyleSheet("color: #21262d; font-size: 10px; padding: 6px;")
        outer.addWidget(ver_label)

        # Activate first button
        self.buttons[0].setChecked(True)

    def _on_click(self, idx: int):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == idx)
        self.page_changed.emit(idx)


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
        self.dashboard      = DashboardWidget()
        self.username_page  = UsernameWidget()
        self.domain_page    = DomainWidget()
        self.email_page     = EmailWidget()
        self.dorks_page     = DorksWidget()
        self.ip_page        = IpWidget()
        self.phone_page     = PhoneWidget()
        self.cert_page      = CertWidget()
        self.metadata_page  = MetadataWidget()
        self.paste_page     = PasteWidget()
        self.crawler_page   = CrawlerWidget()
        self.graph_page     = GraphWidget()
        self.timeline_page  = TimelineWidget()
        self.settings_page  = SettingsWidget()

        for page in [
            self.dashboard, self.username_page, self.domain_page,
            self.email_page, self.dorks_page,
            self.ip_page, self.phone_page, self.cert_page,
            self.metadata_page, self.paste_page,
            self.crawler_page, self.graph_page,
            self.timeline_page, self.settings_page,
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
        ]:
            if hasattr(page, 'send_to_graph'):
                page.send_to_graph.connect(self._add_to_graph)

        # status_message wiring
        for page in [
            self.username_page, self.domain_page, self.email_page,
            self.dorks_page, self.crawler_page,
            self.ip_page, self.phone_page, self.cert_page,
            self.metadata_page, self.paste_page, self.timeline_page,
        ]:
            if hasattr(page, 'status_message'):
                page.status_message.connect(self._set_status)

        # Timeline auto-capture from OSINT pages
        self.username_page.status_message.connect(
            lambda m: self._log_to_timeline('username', self.username_page, m))
        self.domain_page.status_message.connect(
            lambda m: self._log_to_timeline('domain', self.domain_page, m))
        self.email_page.status_message.connect(
            lambda m: self._log_to_timeline('email', self.email_page, m))
        self.ip_page.status_message.connect(
            lambda m: self._log_to_timeline('ip', self.ip_page, m))
        self.phone_page.status_message.connect(
            lambda m: self._log_to_timeline('phone', self.phone_page, m))
        self.cert_page.status_message.connect(
            lambda m: self._log_to_timeline('cert', self.cert_page, m))
        self.metadata_page.status_message.connect(
            lambda m: self._log_to_timeline('metadata', self.metadata_page, m))
        self.paste_page.status_message.connect(
            lambda m: self._log_to_timeline('paste', self.paste_page, m))
        self.dorks_page.status_message.connect(
            lambda m: self._log_to_timeline('dork', self.dorks_page, m))
        self.crawler_page.status_message.connect(
            lambda m: self._log_to_timeline('crawler', self.crawler_page, m))

        # Settings
        self.settings_page.settings_changed.connect(self._apply_settings)

    def _log_to_timeline(self, ev_type: str, page, message: str):
        """Auto-capture status messages as timeline events."""
        # Extract target from the page if possible
        target = ''
        for attr in ('ip_input', 'domain_input', 'email_input', 'query_input',
                     'url_input', 'phone_input', 'username_input'):
            widget = getattr(page, attr, None)
            if widget and hasattr(widget, 'text'):
                val = widget.text().strip()
                if val:
                    target = val
                    break
        if message and not message.startswith('🐇 Inspector Rabbit'):
            self.timeline_page.add_event(ev_type, target or '—', message)

    def _navigate(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.sidebar.buttons):
            btn.setChecked(i == idx)

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
        <p><b>Version:</b> 1.1.0</p>
        <p><b>Modules:</b> 14 OSINT capabilities</p>
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
