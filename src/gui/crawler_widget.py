"""
Inspector Rabbit - Web Crawler Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QDoubleSpinBox,
    QCheckBox, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.web_crawler import CrawlerThread


class CrawlerWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._result = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Topbar
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #010409; border-bottom: 1px solid #21262d; }")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("🕷️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Web Crawler / Spider")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Extract emails · Phone numbers · Social links · Forms · Links")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        # Content
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        layout.addLayout(content_layout, 1)

        left = self._build_left_panel()
        content_layout.addWidget(left)

        right = self._build_right_panel()
        content_layout.addWidget(right, 1)

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)

        self._lbl("SEED URL", layout)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setFixedHeight(42)
        self.url_input.setFont(QFont("Ubuntu", 12))
        layout.addWidget(self.url_input)

        self.start_btn = QPushButton("🕷️  Start Crawling")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.start_btn.clicked.connect(self._start_crawl)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⛔  Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.clicked.connect(self._stop_crawl)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        layout.addWidget(self._sep())
        self._lbl("CRAWLER SETTINGS", layout)

        # Max pages
        max_pages_row = QHBoxLayout()
        max_pages_row.addWidget(QLabel("Max pages:"))
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 500)
        self.max_pages.setValue(50)
        self.max_pages.setFixedWidth(80)
        max_pages_row.addWidget(self.max_pages)
        max_pages_row.addStretch()
        layout.addLayout(max_pages_row)

        # Max depth
        max_depth_row = QHBoxLayout()
        max_depth_row.addWidget(QLabel("Max depth:"))
        self.max_depth = QSpinBox()
        self.max_depth.setRange(1, 10)
        self.max_depth.setValue(3)
        self.max_depth.setFixedWidth(80)
        max_depth_row.addWidget(self.max_depth)
        max_depth_row.addStretch()
        layout.addLayout(max_depth_row)

        # Delay
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay (sec):"))
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0.0, 10.0)
        self.delay.setSingleStep(0.1)
        self.delay.setValue(0.5)
        self.delay.setFixedWidth(80)
        delay_row.addWidget(self.delay)
        delay_row.addStretch()
        layout.addLayout(delay_row)

        self.same_domain = QCheckBox("Same domain only")
        self.same_domain.setChecked(True)
        layout.addWidget(self.same_domain)

        layout.addWidget(self._sep())
        self._lbl("PROGRESS", layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        layout.addWidget(self.progress_bar)

        self.pages_lbl = QLabel("0 pages crawled")
        self.pages_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.pages_lbl)

        layout.addWidget(self._sep())
        self._lbl("LIVE FINDINGS", layout)

        self.emails_lbl = QLabel("Emails: 0")
        self.emails_lbl.setStyleSheet("color: #3fb950; font-weight: 700;")
        layout.addWidget(self.emails_lbl)

        self.phones_lbl = QLabel("Phones: 0")
        self.phones_lbl.setStyleSheet("color: #fb923c; font-weight: 700;")
        layout.addWidget(self.phones_lbl)

        self.social_lbl = QLabel("Social: 0")
        self.social_lbl.setStyleSheet("color: #a78bfa; font-weight: 700;")
        layout.addWidget(self.social_lbl)

        layout.addStretch()

        copy_emails_btn = QPushButton("📋 Copy Emails")
        copy_emails_btn.setFixedHeight(36)
        copy_emails_btn.clicked.connect(self._copy_emails)
        layout.addWidget(copy_emails_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Activity log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: none;
                color: #3fb950;
                padding: 12px;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        self.tabs.addTab(self.log, "📋 Activity Log")

        # Emails table
        self.email_table = self._make_table(["Email Address", "Found On Page"])
        self.tabs.addTab(self.email_table, "✉️ Emails (0)")

        # Phones table
        self.phone_table = self._make_table(["Phone Number", "Found On Page"])
        self.tabs.addTab(self.phone_table, "📞 Phones (0)")

        # Social links
        self.social_table = self._make_table(["Platform", "Profile URL", "Found On"])
        self.tabs.addTab(self.social_table, "📱 Social Links (0)")

        # All links
        self.links_table = self._make_table(["URL", "Title", "Status", "Depth"])
        self.tabs.addTab(self.links_table, "🔗 Pages Crawled (0)")

        # Forms
        self.forms_table = self._make_table(["Page URL", "Method", "Action", "Inputs"])
        self.tabs.addTab(self.forms_table, "📝 Forms (0)")

        return panel

    def _make_table(self, headers) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
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

    def _start_crawl(self):
        url = self.url_input.text().strip()
        if not url:
            self.log.append("⚠️  Enter a seed URL")
            return

        # Clear results
        for t in [self.email_table, self.phone_table, self.social_table,
                   self.links_table, self.forms_table]:
            t.setRowCount(0)
        self.log.clear()
        self.log.append(f"🕷️  Starting crawl: {url}")
        self.progress_bar.setRange(0, 0)  # indeterminate

        self._thread = CrawlerThread(
            url,
            max_pages=self.max_pages.value(),
            max_depth=self.max_depth.value(),
            same_domain_only=self.same_domain.isChecked(),
            delay=self.delay.value()
        )
        self._thread.page_crawled.connect(self._on_page)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(lambda e: self.log.append(f"❌ {e}"))
        self._thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_message.emit(f"Crawling {url}...")

    def _stop_crawl(self):
        if self._thread:
            self._thread.stop()
            self.log.append("⛔  Crawl stopped")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def _on_page(self, page):
        # Add to pages table
        row = self.links_table.rowCount()
        self.links_table.insertRow(row)
        url_item = QTableWidgetItem(page.url[:100])
        url_item.setForeground(QColor("#58a6ff"))
        self.links_table.setItem(row, 0, url_item)
        self.links_table.setItem(row, 1, QTableWidgetItem(page.title[:60]))
        status_item = QTableWidgetItem(str(page.status_code))
        if page.status_code == 200:
            status_item.setForeground(QColor("#3fb950"))
        elif page.status_code >= 400:
            status_item.setForeground(QColor("#f85149"))
        self.links_table.setItem(row, 2, status_item)
        self.links_table.setItem(row, 3, QTableWidgetItem(str(page.depth)))

        # Add emails
        for email in page.emails:
            erow = self.email_table.rowCount()
            self.email_table.insertRow(erow)
            e_item = QTableWidgetItem(email)
            e_item.setForeground(QColor("#3fb950"))
            self.email_table.setItem(erow, 0, e_item)
            self.email_table.setItem(erow, 1, QTableWidgetItem(page.url[:80]))

        # Add phones
        for phone in page.phones:
            prow = self.phone_table.rowCount()
            self.phone_table.insertRow(prow)
            p_item = QTableWidgetItem(phone)
            p_item.setForeground(QColor("#fb923c"))
            self.phone_table.setItem(prow, 0, p_item)
            self.phone_table.setItem(prow, 1, QTableWidgetItem(page.url[:80]))

        # Add social
        for platform, links in page.social_links.items():
            for link in links:
                srow = self.social_table.rowCount()
                self.social_table.insertRow(srow)
                self.social_table.setItem(srow, 0, QTableWidgetItem(platform))
                link_item = QTableWidgetItem(link)
                link_item.setForeground(QColor("#a78bfa"))
                self.social_table.setItem(srow, 1, link_item)
                self.social_table.setItem(srow, 2, QTableWidgetItem(page.url[:60]))

        # Add forms
        for form in page.forms:
            frow = self.forms_table.rowCount()
            self.forms_table.insertRow(frow)
            self.forms_table.setItem(frow, 0, QTableWidgetItem(page.url[:80]))
            self.forms_table.setItem(frow, 1, QTableWidgetItem(form.get('method', '')))
            self.forms_table.setItem(frow, 2, QTableWidgetItem(form.get('action', '')[:60]))
            inputs = ', '.join(
                i.get('name', i.get('type', '')) for i in form.get('inputs', [])[:5]
            )
            self.forms_table.setItem(frow, 3, QTableWidgetItem(inputs))

        # Update stats
        pages_count = self.links_table.rowCount()
        emails_count = self.email_table.rowCount()
        phones_count = self.phone_table.rowCount()
        social_count = self.social_table.rowCount()

        self.pages_lbl.setText(f"{pages_count} pages crawled")
        self.emails_lbl.setText(f"Emails: {emails_count}")
        self.phones_lbl.setText(f"Phones: {phones_count}")
        self.social_lbl.setText(f"Social: {social_count}")

        # Update tab labels
        idx = self.tabs.indexOf(self.email_table)
        self.tabs.setTabText(idx, f"✉️ Emails ({emails_count})")
        idx = self.tabs.indexOf(self.phone_table)
        self.tabs.setTabText(idx, f"📞 Phones ({phones_count})")
        idx = self.tabs.indexOf(self.social_table)
        self.tabs.setTabText(idx, f"📱 Social ({social_count})")
        idx = self.tabs.indexOf(self.links_table)
        self.tabs.setTabText(idx, f"🔗 Pages ({pages_count})")

    def _on_finished(self, result):
        self._result = result
        self.log.append(
            f"\n🏁 Crawl complete!\n"
            f"   📄 Pages: {result.pages_crawled}\n"
            f"   ✉️  Emails: {len(result.all_emails)}\n"
            f"   📞 Phones: {len(result.all_phones)}\n"
            f"   📱 Social: {sum(len(v) for v in result.all_social.values())}\n"
            f"   🔗 Links: {len(result.all_links)}"
        )
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_message.emit(
            f"Crawl complete: {result.pages_crawled} pages, {len(result.all_emails)} emails"
        )

    def _copy_emails(self):
        if not self._result:
            return
        emails = '\n'.join(self._result.all_emails)
        if emails:
            QApplication.clipboard().setText(emails)
            self.log.append(f"📋 Copied {len(self._result.all_emails)} emails to clipboard")
