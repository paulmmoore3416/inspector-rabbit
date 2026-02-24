"""
Inspector Rabbit - Settings Widget
API keys, preferences, and configuration
"""

import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QGroupBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QTextEdit,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


SETTINGS_FILE = os.path.expanduser("~/.inspector_rabbit_settings.json")

DEFAULT_SETTINGS = {
    'shodan_api_key': '',
    'hibp_api_key': '',
    'max_threads': 20,
    'request_timeout': 10,
    'crawl_delay': 0.5,
    'max_crawl_pages': 50,
    'max_crawl_depth': 3,
    'auto_graph': True,
    'show_found_only': False,
    'dork_engine': 'DuckDuckGo',
    'dork_delay': 2.0,
}


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, 'r') as f:
            saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        pass


class ApiKeyField(QFrame):
    def __init__(self, label: str, placeholder: str, help_url: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        lbl_row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        lbl_row.addWidget(lbl)
        lbl_row.addStretch()
        if help_url:
            help_lbl = QLabel(f'<a href="{help_url}" style="color:#58a6ff; font-size:11px;">Get API Key →</a>')
            help_lbl.setOpenExternalLinks(True)
            help_lbl.setStyleSheet("border: none; background: transparent;")
            lbl_row.addWidget(help_lbl)
        layout.addLayout(lbl_row)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setFixedHeight(38)
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input)

        toggle_btn = QPushButton("👁 Show")
        toggle_btn.setFixedHeight(28)
        toggle_btn.setFixedWidth(72)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #8b949e;
                font-size: 11px;
            }
            QPushButton:hover { color: #c9d1d9; }
        """)
        toggle_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._toggle_btn = toggle_btn

    def _toggle_visibility(self):
        if self.input.echoMode() == QLineEdit.EchoMode.Password:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_btn.setText("🔒 Hide")
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_btn.setText("👁 Show")

    def get_value(self) -> str:
        return self.input.text().strip()

    def set_value(self, v: str):
        self.input.setText(v)


class SettingsWidget(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()
        self._setup_ui()
        self._load_into_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Topbar
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #010409; border-bottom: 1px solid #21262d; }")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("⚙️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Settings & Configuration")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("API keys · Scan parameters · Export preferences")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_settings)
        bl.addWidget(save_btn)
        main_layout.addWidget(bar)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # ===== API Keys Section =====
        layout.addWidget(self._section_header("🔑 API Keys"))

        api_grid_layout = QVBoxLayout()
        api_grid_layout.setSpacing(12)

        self.shodan_key = ApiKeyField(
            "Shodan API Key",
            "Enter your Shodan API key...",
            "https://account.shodan.io"
        )
        api_grid_layout.addWidget(self.shodan_key)

        self.hibp_key = ApiKeyField(
            "HaveIBeenPwned API Key",
            "Enter your HIBP API key...",
            "https://haveibeenpwned.com/API/Key"
        )
        api_grid_layout.addWidget(self.hibp_key)

        layout.addLayout(api_grid_layout)

        # ===== Username Checker =====
        layout.addWidget(self._section_header("👤 Username Checker"))
        user_frame = self._card_frame()
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(16, 16, 16, 16)
        user_layout.setSpacing(12)

        threads_row = QHBoxLayout()
        threads_row.addWidget(QLabel("Concurrent threads:"))
        threads_row.addStretch()
        self.max_threads = QSpinBox()
        self.max_threads.setRange(1, 100)
        self.max_threads.setValue(20)
        self.max_threads.setFixedWidth(80)
        threads_row.addWidget(self.max_threads)
        user_layout.addLayout(threads_row)

        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Request timeout (sec):"))
        timeout_row.addStretch()
        self.request_timeout = QSpinBox()
        self.request_timeout.setRange(1, 60)
        self.request_timeout.setValue(10)
        self.request_timeout.setFixedWidth(80)
        timeout_row.addWidget(self.request_timeout)
        user_layout.addLayout(timeout_row)

        self.auto_graph_check = QCheckBox("Automatically add found profiles to graph")
        self.auto_graph_check.setChecked(True)
        user_layout.addWidget(self.auto_graph_check)

        layout.addWidget(user_frame)

        # ===== Dorks Engine =====
        layout.addWidget(self._section_header("🔍 Dorks Engine"))
        dork_frame = self._card_frame()
        dork_layout = QVBoxLayout(dork_frame)
        dork_layout.setContentsMargins(16, 16, 16, 16)
        dork_layout.setSpacing(12)

        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Default search engine:"))
        engine_row.addStretch()
        self.dork_engine = QComboBox()
        self.dork_engine.addItems(["DuckDuckGo", "Bing"])
        self.dork_engine.setFixedWidth(140)
        engine_row.addWidget(self.dork_engine)
        dork_layout.addLayout(engine_row)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay between searches (sec):"))
        delay_row.addStretch()
        self.dork_delay = QDoubleSpinBox()
        self.dork_delay.setRange(0.5, 30.0)
        self.dork_delay.setSingleStep(0.5)
        self.dork_delay.setValue(2.0)
        self.dork_delay.setFixedWidth(80)
        delay_row.addWidget(self.dork_delay)
        dork_layout.addLayout(delay_row)

        layout.addWidget(dork_frame)

        # ===== Web Crawler =====
        layout.addWidget(self._section_header("🕷️ Web Crawler"))
        crawl_frame = self._card_frame()
        crawl_layout = QVBoxLayout(crawl_frame)
        crawl_layout.setContentsMargins(16, 16, 16, 16)
        crawl_layout.setSpacing(12)

        for label, attr, min_v, max_v, default, fixed_w in [
            ("Default max pages:", "crawl_max_pages", 1, 500, 50, 80),
            ("Default max depth:", "crawl_max_depth", 1, 10, 3, 80),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addStretch()
            spin = QSpinBox()
            spin.setRange(min_v, max_v)
            spin.setValue(default)
            spin.setFixedWidth(fixed_w)
            row.addWidget(spin)
            setattr(self, attr, spin)
            crawl_layout.addLayout(row)

        delay_row2 = QHBoxLayout()
        delay_row2.addWidget(QLabel("Default crawl delay (sec):"))
        delay_row2.addStretch()
        self.crawl_delay = QDoubleSpinBox()
        self.crawl_delay.setRange(0.0, 10.0)
        self.crawl_delay.setSingleStep(0.1)
        self.crawl_delay.setValue(0.5)
        self.crawl_delay.setFixedWidth(80)
        delay_row2.addWidget(self.crawl_delay)
        crawl_layout.addLayout(delay_row2)

        layout.addWidget(crawl_frame)

        # ===== About =====
        layout.addWidget(self._section_header("ℹ️ About"))
        about_frame = self._card_frame()
        about_layout = QVBoxLayout(about_frame)
        about_layout.setContentsMargins(16, 16, 16, 16)
        about_html = QTextEdit()
        about_html.setReadOnly(True)
        about_html.setFixedHeight(120)
        about_html.setStyleSheet("QTextEdit { background: transparent; border: none; color: #8b949e; }")
        about_html.setHtml("""
        <div style='color:#c9d1d9;'>
        <b style='color:#00f5ff;'>🐇 Inspector Rabbit v1.0.0</b><br>
        Advanced Open Source Intelligence Suite<br><br>
        <span style='color:#8b949e; font-size:11px;'>
        Inspired by: Sherlock, Maltego, SpiderFoot, Shodan, Recon-ng, Google Dorks<br>
        Built with: Python, PyQt6, aiohttp, dnspython, python-whois<br><br>
        ⚠️ For educational and authorized security research only.
        </span>
        </div>
        """)
        about_layout.addWidget(about_html)
        layout.addWidget(about_frame)

        layout.addStretch()

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #e6edf3;")
        return lbl

    def _card_frame(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 10px;
            }
            QLabel { color: #c9d1d9; background: transparent; border: none; }
        """)
        return f

    def _load_into_ui(self):
        s = self._settings
        self.shodan_key.set_value(s.get('shodan_api_key', ''))
        self.hibp_key.set_value(s.get('hibp_api_key', ''))
        self.max_threads.setValue(s.get('max_threads', 20))
        self.request_timeout.setValue(s.get('request_timeout', 10))
        self.auto_graph_check.setChecked(s.get('auto_graph', True))
        idx = self.dork_engine.findText(s.get('dork_engine', 'DuckDuckGo'))
        if idx >= 0:
            self.dork_engine.setCurrentIndex(idx)
        self.dork_delay.setValue(s.get('dork_delay', 2.0))
        self.crawl_max_pages.setValue(s.get('max_crawl_pages', 50))
        self.crawl_max_depth.setValue(s.get('max_crawl_depth', 3))
        self.crawl_delay.setValue(s.get('crawl_delay', 0.5))

    def _save_settings(self):
        self._settings = {
            'shodan_api_key': self.shodan_key.get_value(),
            'hibp_api_key': self.hibp_key.get_value(),
            'max_threads': self.max_threads.value(),
            'request_timeout': self.request_timeout.value(),
            'auto_graph': self.auto_graph_check.isChecked(),
            'dork_engine': self.dork_engine.currentText(),
            'dork_delay': self.dork_delay.value(),
            'max_crawl_pages': self.crawl_max_pages.value(),
            'max_crawl_depth': self.crawl_max_depth.value(),
            'crawl_delay': self.crawl_delay.value(),
        }
        save_settings(self._settings)
        self.settings_changed.emit(self._settings)

        msg = QMessageBox(self)
        msg.setWindowTitle("Settings Saved")
        msg.setText("✅ Settings saved successfully!")
        msg.setStyleSheet("QMessageBox { background: #0d1117; color: #c9d1d9; }")
        msg.exec()

    def get_settings(self) -> dict:
        return self._settings.copy()
