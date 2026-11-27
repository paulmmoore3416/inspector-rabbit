"""
Inspector Rabbit - Evidence Capture Widget
Capture, hash, and archive web page evidence.
"""

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

from ..modules.evidence_capture import EvidenceCaptureThread, list_evidence, EVIDENCE_DIR
from .components import apply_page_header_style

ACCENT = "#38bdf8"


class EvidenceWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._last_result = None
        self._captures: list[dict] = []
        self._setup_ui()
        self._reload_existing()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        topbar = self._build_topbar()
        layout.addWidget(topbar)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        layout.addLayout(content, 1)

        content.addWidget(self._build_left_panel())
        content.addWidget(self._build_right_panel(), 1)

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        apply_page_header_style(bar, ACCENT)
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        bl.setSpacing(16)

        icon = QLabel("📸")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(0)
        t1 = QLabel("Evidence Capture")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Archive web pages · Cryptographic hashing · Header preservation · Audit trail")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        return bar

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(290)
        panel.setStyleSheet("QFrame { background: #010409; border-right: 1px solid #21262d; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)

        self._sec("TARGET URL", layout)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/page")
        self.url_input.setFixedHeight(42)
        self.url_input.setFont(QFont("Ubuntu", 11))
        self.url_input.returnPressed.connect(self._start_capture)
        layout.addWidget(self.url_input)

        self.capture_btn = QPushButton("📸  Capture Evidence")
        self.capture_btn.setObjectName("primaryBtn")
        self.capture_btn.setFixedHeight(42)
        self.capture_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.capture_btn.clicked.connect(self._start_capture)
        layout.addWidget(self.capture_btn)

        layout.addWidget(self._sep())
        self._sec("HASHES (last capture)", layout)

        sha_row = QHBoxLayout()
        sha_lbl = QLabel("SHA256:")
        sha_lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        sha_lbl.setFixedWidth(54)
        self.sha256_lbl = QLabel("—")
        self.sha256_lbl.setFont(QFont("Ubuntu Mono", 9))
        self.sha256_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 9px;")
        self.sha256_lbl.setWordWrap(True)
        sha_row.addWidget(sha_lbl)
        sha_row.addWidget(self.sha256_lbl, 1)
        layout.addLayout(sha_row)

        md5_row = QHBoxLayout()
        md5_lbl = QLabel("MD5:")
        md5_lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        md5_lbl.setFixedWidth(54)
        self.md5_lbl = QLabel("—")
        self.md5_lbl.setFont(QFont("Ubuntu Mono", 9))
        self.md5_lbl.setStyleSheet("color: #3fb950; font-size: 9px;")
        self.md5_lbl.setWordWrap(True)
        md5_row.addWidget(md5_lbl)
        md5_row.addWidget(self.md5_lbl, 1)
        layout.addLayout(md5_row)

        layout.addWidget(self._sep())
        self._sec("STATUS", layout)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setFont(QFont("Ubuntu Mono", 10))
        self.status_log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: #3fb950;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        self.status_log.setMinimumHeight(140)
        layout.addWidget(self.status_log)

        layout.addStretch()
        layout.addWidget(self._sep())

        self.open_dir_btn = QPushButton("📂 Open Evidence Dir")
        self.open_dir_btn.setFixedHeight(36)
        self.open_dir_btn.clicked.connect(self._open_evidence_dir)
        layout.addWidget(self.open_dir_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)

        # Tab 1: Captured
        self.capture_table = self._make_table(
            ["Timestamp", "URL", "Title", "SHA256", "Status", "Size"]
        )
        self.capture_table.setColumnWidth(0, 140)
        self.capture_table.setColumnWidth(3, 130)
        self.capture_table.setColumnWidth(4, 60)
        self.capture_table.setColumnWidth(5, 80)
        self.capture_table.cellDoubleClicked.connect(self._on_row_double_click)
        self.tabs.addTab(self.capture_table, "📋 Captured")

        # Tab 2: Headers
        self.headers_view = QTextEdit()
        self.headers_view.setReadOnly(True)
        self.headers_view.setFont(QFont("Ubuntu Mono", 10))
        self.headers_view.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: none;
                color: #c9d1d9;
                padding: 12px;
                font-family: 'Ubuntu Mono', monospace;
            }
        """)
        self.tabs.addTab(self.headers_view, "🔤 Headers")

        # Tab 3: Evidence Log
        self.evidence_log = QTextEdit()
        self.evidence_log.setReadOnly(True)
        self.evidence_log.setFont(QFont("Ubuntu Mono", 10))
        self.evidence_log.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: none;
                color: #c9d1d9;
                padding: 12px;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        self.tabs.addTab(self.evidence_log, "📝 Evidence Log")

        return panel

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setFont(QFont("Ubuntu", 10))
        return t

    def _sec(self, text: str, layout):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(lbl)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_capture(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_log.append("Enter a URL to capture.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_input.setText(url)

        self.status_log.clear()
        self.status_log.append(f"Capturing: {url}")
        self.capture_btn.setEnabled(False)
        self.sha256_lbl.setText("—")
        self.md5_lbl.setText("—")

        self._thread = EvidenceCaptureThread(url)
        self._thread.progress.connect(lambda m: self.status_log.append(f"  {m}"))
        self._thread.captured.connect(self._on_captured)
        self._thread.error.connect(self._on_error)
        self._thread.finished.connect(lambda: self.capture_btn.setEnabled(True))
        self._thread.start()

        self.status_message.emit(f"Capturing evidence for: {url}")

    def _on_captured(self, result: dict):
        self._last_result = result
        self._captures.append(result)

        # Update hash labels
        self.sha256_lbl.setText(result.get("sha256", ""))
        self.md5_lbl.setText(result.get("md5", ""))

        # Add row to table
        self._add_table_row(result)

        # Log entry
        ts = result.get("timestamp", "")
        url = result.get("url", "")
        sha = result.get("sha256", "")
        size = result.get("size_bytes", 0)
        title = result.get("title", "")
        status = result.get("status_code", "")
        self.evidence_log.append(
            f"[{ts}] {status} | {size:,} bytes\n"
            f"  URL: {url}\n"
            f"  Title: {title or '(none)'}\n"
            f"  SHA256: {sha}\n"
            f"  Saved: {result.get('save_path', '')}\n"
        )

        # Show headers
        self._show_headers(result.get("headers", {}))

        self.status_log.append(f"Capture complete. SHA256: {sha[:16]}...")
        self.status_message.emit(f"Evidence captured: {url}")
        self.tabs.setCurrentIndex(0)

    def _on_error(self, msg: str):
        self.status_log.append(f"Error: {msg}")
        self.capture_btn.setEnabled(True)
        self.status_message.emit("Evidence capture failed")

    def _add_table_row(self, result: dict):
        row = self.capture_table.rowCount()
        self.capture_table.insertRow(row)

        ts_item = QTableWidgetItem(result.get("timestamp", ""))
        ts_item.setForeground(QColor(ACCENT))
        ts_item.setFont(QFont("Ubuntu Mono", 9))
        self.capture_table.setItem(row, 0, ts_item)

        url_item = QTableWidgetItem(result.get("url", ""))
        url_item.setForeground(QColor("#e6edf3"))
        self.capture_table.setItem(row, 1, url_item)

        title_item = QTableWidgetItem(result.get("title", ""))
        self.capture_table.setItem(row, 2, title_item)

        sha_short = result.get("sha256", "")[:16]
        sha_item = QTableWidgetItem(sha_short)
        sha_item.setFont(QFont("Ubuntu Mono", 9))
        sha_item.setForeground(QColor("#8b949e"))
        self.capture_table.setItem(row, 3, sha_item)

        status_code = result.get("status_code", "")
        status_item = QTableWidgetItem(str(status_code))
        if str(status_code).startswith("2"):
            status_item.setForeground(QColor("#3fb950"))
        elif str(status_code).startswith(("4", "5")):
            status_item.setForeground(QColor("#f85149"))
        else:
            status_item.setForeground(QColor("#e3b341"))
        self.capture_table.setItem(row, 4, status_item)

        size = result.get("size_bytes", 0)
        size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
        size_item = QTableWidgetItem(size_str)
        size_item.setForeground(QColor("#8b949e"))
        self.capture_table.setItem(row, 5, size_item)

        # Stash full result in first cell user data
        ts_item.setData(Qt.ItemDataRole.UserRole, result)

    def _on_row_double_click(self, row: int, _col: int):
        item = self.capture_table.item(row, 0)
        if not item:
            return
        result = item.data(Qt.ItemDataRole.UserRole)
        if not result:
            return

        # Show headers tab
        self._show_headers(result.get("headers", {}))
        self.tabs.setCurrentIndex(1)

        # Show full metadata dialog
        meta_text = json.dumps(
            {k: v for k, v in result.items() if k != "headers"},
            indent=2,
            default=str,
        )
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Evidence Metadata")
        dlg.setText(f"<b>{result.get('url', '')}</b>")
        dlg.setDetailedText(meta_text)
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.exec()

    def _show_headers(self, headers: dict):
        if not headers:
            self.headers_view.setPlainText("(no headers)")
            return
        try:
            text = json.dumps(headers, indent=2, default=str)
        except Exception:
            text = str(headers)
        self.headers_view.setPlainText(text)

    def _open_evidence_dir(self):
        path = Path(EVIDENCE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _reload_existing(self):
        """Load previously captured evidence on startup."""
        try:
            existing = list_evidence()
            for result in existing:
                self._captures.append(result)
                self._add_table_row(result)
                ts = result.get("timestamp", "")
                url = result.get("url", "")
                sha = result.get("sha256", "")
                size = result.get("size_bytes", 0)
                title = result.get("title", "")
                status = result.get("status_code", "")
                self.evidence_log.append(
                    f"[{ts}] {status} | {size:,} bytes\n"
                    f"  URL: {url}\n"
                    f"  Title: {title or '(none)'}\n"
                    f"  SHA256: {sha}\n"
                    f"  Saved: {result.get('save_path', '')}\n"
                )
            if existing:
                count = len(existing)
                self.tabs.setTabText(0, f"📋 Captured ({count})")
        except Exception:
            pass

    def apply_settings(self, settings: dict):
        pass
