"""
Inspector Rabbit - Social Profile Intelligence Widget
Scan social platforms for a username and aggregate public profile data.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGridLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

from ..modules.social_scraper import SocialScrapeThread
from .components import apply_page_header_style


ACCENT = "#4ade80"

PLATFORM_ICONS = {
    'github':    '🐙',
    'reddit':    '🤖',
    'twitter':   '🐦',
    'instagram': '📸',
    'tiktok':    '🎵',
    'youtube':   '▶️',
    'twitch':    '🎮',
}

PLATFORM_COLORS = {
    'GitHub':    '#c9d1d9',
    'Reddit':    '#ff4500',
    'Twitter/X': '#1da1f2',
    'Instagram': '#e1306c',
    'TikTok':    '#69c9d0',
    'YouTube':   '#ff0000',
    'Twitch':    '#9146ff',
}


class SocialWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._profiles = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        bar = QFrame()
        apply_page_header_style(bar, ACCENT)
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)

        icon = QLabel("👤")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Social Profile Intelligence")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("GitHub · Reddit · Twitter · Instagram · TikTok · YouTube · Twitch")
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
        content.addWidget(self._build_left())
        content.addWidget(self._build_right(), 1)

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(10)

        self._lbl("USERNAME", lay)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("target_username")
        self.username_input.setFixedHeight(42)
        self.username_input.setFont(QFont("Ubuntu", 12))
        self.username_input.returnPressed.connect(self._start)
        lay.addWidget(self.username_input)

        self.scan_btn = QPushButton("🔍  Scan Profiles")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.clicked.connect(self._start)
        lay.addWidget(self.scan_btn)

        lay.addWidget(self._sep())
        self._lbl("PLATFORMS", lay)

        platforms = [
            ("github",    "🐙 GitHub"),
            ("reddit",    "🤖 Reddit"),
            ("twitter",   "🐦 Twitter / X"),
            ("instagram", "📸 Instagram"),
            ("tiktok",    "🎵 TikTok"),
            ("youtube",   "▶️  YouTube"),
            ("twitch",    "🎮 Twitch"),
        ]

        self._platform_checks = {}
        for key, label in platforms:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet("color: #c9d1d9; font-size: 12px;")
            lay.addWidget(cb)
            self._platform_checks[key] = cb

        # Select / deselect all
        row = QHBoxLayout()
        all_btn = QPushButton("All")
        all_btn.setFixedHeight(28)
        all_btn.clicked.connect(lambda: self._set_all_checks(True))
        none_btn = QPushButton("None")
        none_btn.setFixedHeight(28)
        none_btn.clicked.connect(lambda: self._set_all_checks(False))
        row.addWidget(all_btn)
        row.addWidget(none_btn)
        lay.addLayout(row)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet(f"""
            QTextEdit {{
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: {ACCENT};
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }}
        """)
        self.log.setMinimumHeight(120)
        lay.addWidget(self.log)

        lay.addStretch()

        self.profile_count_label = QLabel("Profiles found: 0")
        self.profile_count_label.setStyleSheet("color: #484f58; font-size: 12px; border: none;")
        lay.addWidget(self.profile_count_label)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # --- Tab 1: Profiles table ---
        cols = ["Platform", "Username", "Display Name", "Followers", "Posts", "Bio", "URL"]
        self.profile_table = self._make_table(cols)
        self.profile_table.setColumnWidth(0, 100)
        self.profile_table.setColumnWidth(1, 120)
        self.profile_table.setColumnWidth(2, 130)
        self.profile_table.setColumnWidth(3, 80)
        self.profile_table.setColumnWidth(4, 60)
        self.profile_table.doubleClicked.connect(self._open_url_from_table)
        self.profile_table.clicked.connect(self._on_row_selected)
        self.tabs.addTab(self.profile_table, "👤 Profiles (0)")

        # --- Tab 2: Details ---
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet(
            "QTextEdit { background: #0d1117; border: none; padding: 16px; }"
        )
        self.details_text.setHtml(self._placeholder_html())
        self.tabs.addTab(self.details_text, "📋 Details")

        # --- Tab 3: Open Profiles ---
        self.tabs.addTab(self._build_open_profiles_tab(), "🔗 Open Profiles")

        return panel

    def _build_open_profiles_tab(self) -> QWidget:
        self._open_profiles_widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #0d1117; }"
        )

        self._open_profiles_inner = QWidget()
        self._open_profiles_inner.setStyleSheet("background: #0d1117;")
        self._open_profiles_grid = QGridLayout(self._open_profiles_inner)
        self._open_profiles_grid.setContentsMargins(16, 16, 16, 16)
        self._open_profiles_grid.setSpacing(12)

        self._placeholder_open = QLabel("Scan a username to see profile links here.")
        self._placeholder_open.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_open.setStyleSheet("color: #484f58; font-size: 12px; border: none;")
        self._open_profiles_grid.addWidget(self._placeholder_open, 0, 0)

        scroll.setWidget(self._open_profiles_inner)

        outer = QVBoxLayout(self._open_profiles_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return self._open_profiles_widget

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_table(self, headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSortingEnabled(False)
        return t

    def _lbl(self, text: str, lay):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(l)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _placeholder_html(self) -> str:
        return """
        <div style='padding:24px; color:#8b949e; text-align:center;'>
          <div style='font-size:48px; margin-bottom:12px;'>👤</div>
          <h2 style='color:#e6edf3;'>Social Profile Intelligence</h2>
          <p>Select a row in the Profiles tab to see full details here.</p>
        </div>
        """

    def _set_all_checks(self, state: bool):
        for cb in self._platform_checks.values():
            cb.setChecked(state)

    def _get_selected_platforms(self) -> list:
        return [k for k, cb in self._platform_checks.items() if cb.isChecked()]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start(self):
        username = self.username_input.text().strip()
        if not username:
            self.log.append("⚠️  Enter a username")
            return

        platforms = self._get_selected_platforms()
        if not platforms:
            self.log.append("⚠️  Select at least one platform")
            return

        self.log.clear()
        self._profiles = []
        self.profile_table.setRowCount(0)
        self.details_text.setHtml(self._placeholder_html())
        self._clear_open_profiles_grid()

        self.profile_count_label.setText("Profiles found: scanning...")
        self.scan_btn.setEnabled(False)
        self.log.append(f"🐇 Scanning: {username} on {len(platforms)} platform(s)")

        self._thread = SocialScrapeThread(username, platforms)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.profile_found.connect(self._on_profile)
        self._thread.done.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"Scanning social profiles for: {username}")

    def _clear_open_profiles_grid(self):
        while self._open_profiles_grid.count():
            item = self._open_profiles_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_profile(self, profile: dict):
        self._profiles.append(profile)

        platform = profile.get('platform', '')
        username = profile.get('username', '')
        display = profile.get('display_name', '')
        followers = profile.get('followers', '—')
        posts = profile.get('posts', '—')
        bio = (profile.get('bio', '') or '')[:80]
        url = profile.get('url', '')
        color = QColor(PLATFORM_COLORS.get(platform, '#c9d1d9'))

        # Profiles table row
        row = self.profile_table.rowCount()
        self.profile_table.insertRow(row)

        plat_item = QTableWidgetItem(platform)
        plat_item.setForeground(color)
        plat_item.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        self.profile_table.setItem(row, 0, plat_item)

        user_item = QTableWidgetItem(username)
        user_item.setForeground(QColor("#e6edf3"))
        self.profile_table.setItem(row, 1, user_item)

        self.profile_table.setItem(row, 2, QTableWidgetItem(display))

        fol_item = QTableWidgetItem(followers)
        fol_item.setForeground(QColor("#8b949e"))
        self.profile_table.setItem(row, 3, fol_item)

        posts_item = QTableWidgetItem(posts)
        posts_item.setForeground(QColor("#8b949e"))
        self.profile_table.setItem(row, 4, posts_item)

        self.profile_table.setItem(row, 5, QTableWidgetItem(bio))

        url_item = QTableWidgetItem(url)
        url_item.setForeground(QColor("#4ade80"))
        self.profile_table.setItem(row, 6, url_item)

        count = self.profile_table.rowCount()
        self.tabs.setTabText(0, f"👤 Profiles ({count})")
        self.profile_count_label.setText(f"Profiles found: {count}")

        # Open Profiles grid button
        self._add_open_button(profile)

    def _add_open_button(self, profile: dict):
        url = profile.get('url', '')
        platform = profile.get('platform', '')
        username = profile.get('username', '')
        color = PLATFORM_COLORS.get(platform, '#4ade80')
        icon = PLATFORM_ICONS.get(platform.lower().split('/')[0], '🌐')

        btn = QPushButton(f"{icon}  {platform}\n@{username}")
        btn.setFixedHeight(64)
        btn.setFont(QFont("Ubuntu", 10))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: #0d1117;
                border: 1px solid {color}44;
                border-radius: 10px;
                color: {color};
                font-weight: 600;
                text-align: center;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background: #161b22;
                border: 1px solid {color};
                color: #e6edf3;
            }}
        """)
        if url:
            btn.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        else:
            btn.setEnabled(False)

        # Remove placeholder if present
        for i in range(self._open_profiles_grid.count()):
            item = self._open_profiles_grid.itemAt(i)
            if item and item.widget() is self._placeholder_open:
                self._open_profiles_grid.removeWidget(self._placeholder_open)
                self._placeholder_open.hide()
                break

        count = self._open_profiles_grid.count()
        row = count // 3
        col = count % 3
        self._open_profiles_grid.addWidget(btn, row, col)

    def _on_done(self, summary: dict):
        self.scan_btn.setEnabled(True)
        found = summary.get('found', 0)
        errors = summary.get('errors', 0)
        self.log.append(f"✅ Done — {found} profile(s) found, {errors} error(s)")
        self.profile_count_label.setText(f"Profiles found: {found}")
        self.status_message.emit(f"Social scan: {found} profiles found")

        if found > 0:
            self.tabs.setCurrentIndex(0)

    def _open_url_from_table(self, index):
        url_col = 6
        item = self.profile_table.item(index.row(), url_col)
        if item and item.text().startswith('http'):
            QDesktopServices.openUrl(QUrl(item.text()))

    def _on_row_selected(self, index):
        row = index.row()
        if row < 0 or row >= len(self._profiles):
            return
        profile = self._profiles[row]
        self._show_profile_details(profile)

    def _show_profile_details(self, profile: dict):
        platform = profile.get('platform', '')
        username = profile.get('username', '')
        display = profile.get('display_name', '')
        bio = profile.get('bio', '') or ''
        followers = profile.get('followers', '—')
        following = profile.get('following', '—')
        posts = profile.get('posts', '—')
        verified = profile.get('verified', '—')
        url = profile.get('url', '')
        avatar = profile.get('avatar_url', '')
        created = profile.get('created_at', '')
        location = profile.get('location', '')
        extra = profile.get('extra', {})
        color = PLATFORM_COLORS.get(platform, '#4ade80')

        html = f"""
        <div style='padding:20px; color:#c9d1d9;'>
          <h2 style='color:{color}; margin-bottom:4px;'>
            {platform} &mdash; @{username}
          </h2>
        """

        if display:
            html += f"<p style='color:#e6edf3; font-size:16px; margin:0 0 8px;'>{display}</p>"

        if bio:
            html += f"""
            <div style='background:#161b22; border:1px solid #21262d; border-radius:8px;
                         padding:10px 14px; margin-bottom:16px; color:#8b949e; font-size:12px;'>
              {bio}
            </div>"""

        html += """
          <table style='width:100%; border-collapse:collapse; margin-bottom:16px;'>
            <tr style='background:#161b22;'>
              <th style='padding:8px 12px; text-align:left; color:#484f58; font-size:10px;
                          letter-spacing:1px; border-bottom:1px solid #21262d;'>FIELD</th>
              <th style='padding:8px 12px; text-align:left; color:#484f58; font-size:10px;
                          letter-spacing:1px; border-bottom:1px solid #21262d;'>VALUE</th>
            </tr>
        """

        fields = [
            ("URL",       url),
            ("Followers", followers),
            ("Following", following),
            ("Posts",     posts),
            ("Verified",  verified),
            ("Location",  location),
            ("Joined",    created),
            ("Avatar",    avatar),
        ]

        for i, (k, v) in enumerate(fields):
            if not v or v == '—':
                continue
            bg = "#0d1117" if i % 2 else "#161b22"
            if k == 'URL' and v.startswith('http'):
                val_html = f"<a style='color:#4ade80;' href='{v}'>{v}</a>"
            else:
                val_html = str(v)
            html += f"""
            <tr style='background:{bg};'>
              <td style='padding:8px 12px; color:#8b949e; font-size:12px;
                          border-bottom:1px solid #21262d;'>{k}</td>
              <td style='padding:8px 12px; color:#c9d1d9; font-size:12px;
                          border-bottom:1px solid #21262d;'>{val_html}</td>
            </tr>"""

        html += "</table>"

        if extra:
            html += """
            <div style='margin-bottom:8px;'>
              <span style='color:#484f58; font-size:10px; font-weight:700; letter-spacing:1px;'>
                EXTRA DATA
              </span>
            </div>
            <table style='width:100%; border-collapse:collapse;'>
            """
            for i, (k, v) in enumerate(extra.items()):
                bg = "#0d1117" if i % 2 else "#161b22"
                html += f"""
                <tr style='background:{bg};'>
                  <td style='padding:6px 12px; color:#8b949e; font-size:11px;
                              border-bottom:1px solid #21262d;'>{k}</td>
                  <td style='padding:6px 12px; color:#c9d1d9; font-size:11px;
                              border-bottom:1px solid #21262d;'>{v}</td>
                </tr>"""
            html += "</table>"

        html += "</div>"
        self.details_text.setHtml(html)
        self.tabs.setCurrentIndex(1)

    def apply_settings(self, s):
        pass
