"""
Inspector Rabbit - Reverse Image Search & EXIF Widget
Load image from URL or local file, preview thumbnail, view EXIF metadata,
and open reverse image search engines in the browser.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QFileDialog, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QUrl, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPixmap, QDesktopServices

import requests
import io

from ..modules.metadata_extractor import fetch_and_extract, extract_image_metadata
from .components import apply_page_header_style


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}


class ReverseImageThread(QThread):
    progress = pyqtSignal(str)
    image_ready = pyqtSignal(bytes)         # raw image bytes for preview
    exif_ready = pyqtSignal(dict)           # full result dict from fetch_and_extract
    error = pyqtSignal(str)

    def __init__(self, source: str, is_url: bool = True):
        super().__init__()
        self._source = source.strip()
        self._is_url = is_url

    def run(self):
        try:
            if self._is_url:
                self.progress.emit(f"Fetching image from URL...")
                resp = requests.get(self._source, headers=HEADERS, timeout=15, stream=True)
                resp.raise_for_status()
                data = b''
                for chunk in resp.iter_content(65536):
                    data += chunk
                    if len(data) > 50 * 1024 * 1024:
                        break
                self.progress.emit(f"Downloaded {len(data) // 1024} KB")
                self.image_ready.emit(data)
                self.progress.emit("Extracting EXIF metadata...")
                import os
                filename = self._source.split('/')[-1] or 'image'
                result = extract_image_metadata(data, filename)
                self.exif_ready.emit(self._result_to_dict(result))
            else:
                self.progress.emit(f"Reading local file...")
                with open(self._source, 'rb') as f:
                    data = f.read()
                self.progress.emit(f"Read {len(data) // 1024} KB")
                self.image_ready.emit(data)
                self.progress.emit("Extracting EXIF metadata...")
                import os
                filename = os.path.basename(self._source)
                result = extract_image_metadata(data, filename)
                self.exif_ready.emit(self._result_to_dict(result))
        except Exception as e:
            self.error.emit(str(e))

    def _result_to_dict(self, result) -> dict:
        """Convert MetadataResult to a plain dict for signal emission."""
        return {
            'filename': result.filename,
            'file_type': result.file_type,
            'file_size': result.file_size,
            'exif': result.exif_data,
            'gps': result.gps_data,
            'warnings': result.warnings,
            'error': result.error,
            'raw_tags': result.raw_tags,
        }


class ReverseImageWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._current_url = ""
        self._image_bytes = None
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
        apply_page_header_style(bar, "#e879f9")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)

        icon = QLabel("🖼️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Reverse Image Search")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Preview · EXIF metadata · Reverse search via Google, TinEye, Yandex, Bing")
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
        lay.setSpacing(12)

        self._lbl("IMAGE URL", lay)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/photo.jpg")
        self.url_input.setFixedHeight(42)
        self.url_input.setFont(QFont("Ubuntu", 11))
        self.url_input.returnPressed.connect(self._start_url)
        lay.addWidget(self.url_input)

        self.fetch_btn = QPushButton("🔍  Fetch Image")
        self.fetch_btn.setObjectName("primaryBtn")
        self.fetch_btn.setFixedHeight(42)
        self.fetch_btn.clicked.connect(self._start_url)
        lay.addWidget(self.fetch_btn)

        file_btn = QPushButton("📂  Open Local File")
        file_btn.setFixedHeight(38)
        file_btn.clicked.connect(self._open_file)
        lay.addWidget(file_btn)

        lay.addWidget(self._sep())
        self._lbl("STATUS", lay)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Ubuntu Mono", 10))
        self.log.setStyleSheet("""
            QTextEdit {
                background: #010409;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: #e879f9;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        self.log.setMinimumHeight(180)
        lay.addWidget(self.log)

        lay.addStretch()

        # GPS summary label
        self.gps_label = QLabel("No GPS data found")
        self.gps_label.setStyleSheet("color: #484f58; font-size: 11px; border: none;")
        self.gps_label.setWordWrap(True)
        lay.addWidget(self.gps_label)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # --- Tab 1: Preview ---
        preview_widget = QWidget()
        preview_lay = QVBoxLayout(preview_widget)
        preview_lay.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #21262d; border-radius: 8px; background: #0d1117; }")

        self.preview_label = QLabel("Load an image to see preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFont(QFont("Ubuntu", 12))
        self.preview_label.setStyleSheet("color: #484f58; background: #0d1117; border: none;")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(self.preview_label)
        preview_lay.addWidget(scroll)

        self.img_info_label = QLabel("")
        self.img_info_label.setStyleSheet("color: #8b949e; font-size: 11px; border: none;")
        self.img_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_lay.addWidget(self.img_info_label)

        self.tabs.addTab(preview_widget, "🖼️ Preview")

        # --- Tab 2: EXIF ---
        self.exif_tree = QTreeWidget()
        self.exif_tree.setHeaderLabels(["Field", "Value"])
        self.exif_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.exif_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.exif_tree.setAlternatingRowColors(True)
        self.exif_tree.setFont(QFont("Ubuntu Mono", 10))
        self.tabs.addTab(self.exif_tree, "📷 EXIF")

        # --- Tab 3: Reverse Search ---
        self.tabs.addTab(self._build_reverse_search_tab(), "🔎 Reverse Search")

        return panel

    def _build_reverse_search_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header = QLabel("Open reverse image search in your browser")
        header.setFont(QFont("Ubuntu", 12))
        header.setStyleSheet("color: #8b949e; border: none;")
        lay.addWidget(header)

        note = QLabel("Requires an image URL to be loaded first.")
        note.setFont(QFont("Ubuntu", 10))
        note.setStyleSheet("color: #484f58; border: none;")
        lay.addWidget(note)

        lay.addWidget(self._sep())

        engines = [
            ("Google Images", "#4285f4", "🔵",
             "https://images.google.com/searchbyimage?image_url={url}"),
            ("TinEye", "#f0732c", "🟠",
             "https://www.tineye.com/search?url={url}"),
            ("Yandex Images", "#e3200a", "🔴",
             "https://yandex.com/images/search?url={url}&rpt=imageview"),
            ("Bing Visual Search", "#00b4f0", "🔷",
             "https://www.bing.com/images/search?q=imgurl:{url}&view=detailv2&iss=sbi"),
        ]

        for name, color, icon, url_template in engines:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: #0d1117;
                    border: 1px solid #21262d;
                    border-radius: 10px;
                }}
                QFrame:hover {{
                    border: 1px solid {color}44;
                    background: #161b22;
                }}
            """)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(16, 12, 16, 12)

            lbl = QLabel(f"{icon}  {name}")
            lbl.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            row_lay.addWidget(lbl)
            row_lay.addStretch()

            btn = QPushButton("Open in Browser")
            btn.setFixedHeight(34)
            btn.setFixedWidth(140)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}22;
                    border: 1px solid {color}66;
                    border-radius: 6px;
                    color: {color};
                    font-weight: 600;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {color}44;
                    border: 1px solid {color};
                    color: #e6edf3;
                }}
            """)
            # Capture url_template in closure
            btn.clicked.connect(self._make_open_handler(url_template))
            row_lay.addWidget(btn)

            lay.addWidget(row)

        lay.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_open_handler(self, url_template: str):
        def handler():
            url = self._current_url.strip()
            if not url:
                self.log.append("⚠️  Load an image URL first")
                return
            from urllib.parse import quote
            final_url = url_template.replace("{url}", quote(url, safe=''))
            QDesktopServices.openUrl(QUrl(final_url))
            self.log.append(f"  ↳ Opened in browser")
        return handler

    def _lbl(self, text: str, lay):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(l)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.log.append("⚠️  Enter an image URL")
            return
        self._current_url = url
        self._reset_results()
        self.log.append(f"🐇 Fetching: {url}")
        self.fetch_btn.setEnabled(False)
        self._thread = ReverseImageThread(url, is_url=True)
        self._connect_thread()
        self._thread.start()
        self.status_message.emit(f"Fetching image: {url}")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "",
            "Images (*.jpg *.jpeg *.png *.tiff *.tif *.gif *.bmp *.webp);;"
            "All Files (*)"
        )
        if not path:
            return
        # For local files, set the URL field so reverse-search engines get something
        self._current_url = ""
        self._reset_results()
        self.log.append(f"🐇 Loading file: {path}")
        self.fetch_btn.setEnabled(False)
        self._thread = ReverseImageThread(path, is_url=False)
        self._connect_thread()
        self._thread.start()
        self.status_message.emit(f"Analyzing file: {path}")

    def _connect_thread(self):
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.image_ready.connect(self._on_image_ready)
        self._thread.exif_ready.connect(self._on_exif_ready)
        self._thread.error.connect(self._on_error)
        self._thread.finished.connect(lambda: self.fetch_btn.setEnabled(True))

    def _reset_results(self):
        self.preview_label.setText("Loading...")
        self.preview_label.setPixmap(QPixmap())
        self.img_info_label.setText("")
        self.exif_tree.clear()
        self.gps_label.setText("No GPS data found")
        self.gps_label.setStyleSheet("color: #484f58; font-size: 11px; border: none;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_image_ready(self, data: bytes):
        self._image_bytes = data
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            w, h = pixmap.width(), pixmap.height()
            scaled = pixmap.scaled(
                780, 520,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
            self.img_info_label.setText(
                f"{w} x {h} px  |  {len(data) // 1024} KB"
            )
            self.tabs.setCurrentIndex(0)
        else:
            self.preview_label.setText("Could not render preview (unsupported format)")
        self.log.append("✅ Image preview loaded")

    def _on_exif_ready(self, result: dict):
        self.exif_tree.clear()

        if result.get('error'):
            self.log.append(f"⚠️  EXIF: {result['error']}")
        else:
            self.log.append("✅ EXIF extraction complete")

        # Warnings
        warnings = result.get('warnings', [])
        if warnings:
            warn_root = QTreeWidgetItem(self.exif_tree, ["⚠️ Warnings", ""])
            warn_root.setExpanded(True)
            warn_root.setForeground(0, QColor("#f85149"))
            for w in warnings:
                wi = QTreeWidgetItem(warn_root, ["!", w])
                wi.setForeground(0, QColor("#ffa657"))
                wi.setForeground(1, QColor("#ffa657"))

        # EXIF fields
        exif = result.get('exif', {})
        if exif:
            exif_root = QTreeWidgetItem(self.exif_tree, ["📷 EXIF Data", ""])
            exif_root.setExpanded(True)
            for tag, val in exif.items():
                if tag == 'GPSInfo' and isinstance(val, dict):
                    gps_item = QTreeWidgetItem(exif_root, ["GPSInfo", ""])
                    for gk, gv in val.items():
                        QTreeWidgetItem(gps_item, [str(gk), str(gv)[:120]])
                else:
                    item = QTreeWidgetItem(exif_root, [tag, str(val)[:120]])
                    item.setForeground(0, QColor("#e879f9"))

        # Raw tags
        raw = result.get('raw_tags', {})
        if raw:
            raw_root = QTreeWidgetItem(self.exif_tree, ["🔍 Raw / Info Tags", ""])
            for tag, val in raw.items():
                QTreeWidgetItem(raw_root, [tag, str(val)[:120]])

        # GPS summary
        gps = result.get('gps', {})
        if gps and gps.get('latitude') is not None:
            lat = gps['latitude']
            lon = gps['longitude']
            self.gps_label.setText(f"📍 GPS: {lat:.4f}, {lon:.4f}")
            self.gps_label.setStyleSheet(
                "color: #f85149; font-size: 11px; font-weight: bold; border: none;"
            )

        exif_count = len(exif)
        self.status_message.emit(f"EXIF extracted: {exif_count} tags")

    def _on_error(self, msg: str):
        self.log.append(f"❌ {msg}")
        self.fetch_btn.setEnabled(True)
        self.status_message.emit(f"Error: {msg}")

    def apply_settings(self, s):
        pass
