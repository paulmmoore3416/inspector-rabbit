"""
Inspector Rabbit - Metadata Extractor Widget
Extract EXIF, GPS, and document metadata from files/URLs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor

from ..modules.metadata_extractor import fetch_and_extract
from .components import apply_page_header_style


class MetadataFetchThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(dict)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self):
        self.progress.emit(f"Fetching {self._url} ...")
        result = fetch_and_extract(self._url)
        self.result_ready.emit(result)


class MetadataWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
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

        # Top bar
        bar = QFrame()
        apply_page_header_style(bar, "#fb923c")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("📄")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Metadata Extractor")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Extract EXIF · GPS coordinates · PDF/DOCX author data · Hidden metadata")
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

        self._lbl("URL OR FILE PATH", lay)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/image.jpg")
        self.url_input.setFixedHeight(42)
        self.url_input.setFont(QFont("Ubuntu", 11))
        self.url_input.returnPressed.connect(self._start_url)
        lay.addWidget(self.url_input)

        self.fetch_btn = QPushButton("🔍  Fetch & Analyze URL")
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
            QTextEdit { background:#010409; border:1px solid #21262d; border-radius:8px;
                        color:#3fb950; font-family:'Ubuntu Mono',monospace; font-size:11px; }
        """)
        self.log.setMinimumHeight(200)
        lay.addWidget(self.log)

        lay.addStretch()

        self.gps_label = QLabel("📍 No GPS found")
        self.gps_label.setStyleSheet("color: #484f58; font-size: 11px; border: none;")
        self.gps_label.setWordWrap(True)
        lay.addWidget(self.gps_label)

        copy_btn = QPushButton("📋 Copy All Metadata")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(self._copy_metadata)
        lay.addWidget(copy_btn)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 16, 24, 16)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # Overview tree
        self.overview_tree = QTreeWidget()
        self.overview_tree.setHeaderLabels(["Field", "Value"])
        self.overview_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.overview_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.overview_tree.setAlternatingRowColors(True)
        self.tabs.addTab(self.overview_tree, "📋 Overview")

        # EXIF table
        self.exif_table = self._make_table(["Tag", "Value"])
        self.tabs.addTab(self.exif_table, "📷 EXIF Data")

        # GPS tab
        gps_widget = QWidget()
        gps_lay = QVBoxLayout(gps_widget)
        gps_lay.setContentsMargins(16, 16, 16, 16)
        self.gps_text = QTextEdit()
        self.gps_text.setReadOnly(True)
        self.gps_text.setFont(QFont("Ubuntu Mono", 11))
        self.gps_text.setStyleSheet(
            "QTextEdit { background:#0d1117; border:1px solid #21262d; border-radius:8px; color:#e6edf3; }"
        )
        gps_lay.addWidget(self.gps_text)
        open_map_btn = QPushButton("🗺️  Open in Google Maps")
        open_map_btn.setFixedHeight(36)
        open_map_btn.clicked.connect(self._open_maps)
        gps_lay.addWidget(open_map_btn)
        self.tabs.addTab(gps_widget, "📍 GPS Location")

        # Raw tab
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Ubuntu Mono", 10))
        self.raw_text.setStyleSheet(
            "QTextEdit { background:#0d1117; border:1px solid #21262d; border-radius:8px; color:#8b949e; font-size:11px; }"
        )
        self.tabs.addTab(self.raw_text, "🔍 Raw")

        return panel

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        return t

    def _lbl(self, text, lay):
        l = QLabel(text)
        l.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(l)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _start_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.log.append("⚠️  Enter a URL")
            return
        self._clear_results()
        self.log.append(f"🐇 Fetching: {url}")
        self.fetch_btn.setEnabled(False)
        self._thread = MetadataFetchThread(url)
        self._thread.progress.connect(lambda m: self.log.append(f"  ↳ {m}"))
        self._thread.result_ready.connect(self._on_result)
        self._thread.start()
        self.status_message.emit(f"Extracting metadata from {url}...")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File for Metadata Analysis",
            "",
            "All Supported (*.jpg *.jpeg *.png *.tiff *.tif *.gif *.bmp *.pdf *.docx);;"
            "Images (*.jpg *.jpeg *.png *.tiff *.tif *.gif *.bmp);;"
            "Documents (*.pdf *.docx)"
        )
        if not path:
            return
        self._clear_results()
        self.log.append(f"🐇 Analyzing: {path}")
        self.fetch_btn.setEnabled(False)
        import threading
        def _run():
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                import os
                from ..modules.metadata_extractor import extract_image_metadata, extract_pdf_metadata
                filename = os.path.basename(path)
                ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
                if ext in ('jpg', 'jpeg', 'png', 'tiff', 'tif', 'gif', 'bmp', 'webp'):
                    result = extract_image_metadata(data, filename)
                elif ext == 'pdf':
                    result = extract_pdf_metadata(data, filename)
                else:
                    result = {'error': f'Unsupported file type: {ext}', 'filename': filename}
                # emit via invokeMethod-compatible approach
                from PyQt6.QtCore import QMetaObject, Qt as Qt2
                self._pending_result = result
                QMetaObject.invokeMethod(self, "_deliver_result", Qt2.ConnectionType.QueuedConnection)
            except Exception as e:
                self._pending_result = {'error': str(e)}
                from PyQt6.QtCore import QMetaObject, Qt as Qt2
                QMetaObject.invokeMethod(self, "_deliver_result", Qt2.ConnectionType.QueuedConnection)
        self._pending_result = None
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot()
    def _deliver_result(self):
        if self._pending_result is not None:
            self._on_result(self._pending_result)

    def _clear_results(self):
        self.overview_tree.clear()
        self.exif_table.setRowCount(0)
        self.gps_text.clear()
        self.raw_text.clear()
        self.gps_label.setText("📍 No GPS found")

    def _on_result(self, result: dict):
        self._result = result
        self.fetch_btn.setEnabled(True)

        if 'error' in result and result.get('error'):
            self.log.append(f"❌ {result['error']}")
            return

        filename = result.get('filename', 'unknown')
        file_type = result.get('file_type', 'unknown')
        self.log.append(f"✅ Analyzed: {filename} ({file_type})")

        # Build overview tree
        info_root = QTreeWidgetItem(self.overview_tree, ["📋 File Info", ""])
        info_root.setExpanded(True)
        for key in ['filename', 'file_type', 'file_size']:
            val = result.get(key, '')
            if val:
                QTreeWidgetItem(info_root, [key.replace('_', ' ').title(), str(val)])

        # Warnings
        warnings = result.get('warnings', [])
        if warnings:
            warn_root = QTreeWidgetItem(self.overview_tree, ["⚠️ Warnings", ""])
            warn_root.setExpanded(True)
            warn_root.setForeground(0, QColor("#f85149"))
            for w in warnings:
                wi = QTreeWidgetItem(warn_root, ["!", w])
                wi.setForeground(0, QColor("#ffa657"))
                wi.setForeground(1, QColor("#ffa657"))

        # Image-specific
        if file_type == 'image':
            img_root = QTreeWidgetItem(self.overview_tree, ["📷 Image Info", ""])
            img_root.setExpanded(True)
            for key in ['make', 'model', 'software', 'datetime', 'width', 'height', 'color_space']:
                val = result.get(key, '')
                if val:
                    QTreeWidgetItem(img_root, [key.replace('_', ' ').title(), str(val)])

        # PDF-specific
        if file_type == 'pdf':
            doc_root = QTreeWidgetItem(self.overview_tree, ["📄 Document Info", ""])
            doc_root.setExpanded(True)
            for key in ['title', 'author', 'creator', 'producer', 'subject', 'keywords',
                        'creation_date', 'modification_date', 'pages', 'encrypted']:
                val = result.get(key, '')
                if val:
                    QTreeWidgetItem(doc_root, [key.replace('_', ' ').title(), str(val)])

        # GPS
        gps = result.get('gps', {})
        if gps:
            lat = gps.get('latitude')
            lon = gps.get('longitude')
            alt = gps.get('altitude', '')
            if lat is not None and lon is not None:
                gps_str = (
                    f"⚠️  GPS COORDINATES FOUND IN FILE!\n\n"
                    f"  Latitude:   {lat:.6f}°\n"
                    f"  Longitude:  {lon:.6f}°\n"
                )
                if alt:
                    gps_str += f"  Altitude:   {alt}\n"
                gps_str += f"\n  Google Maps: https://maps.google.com/?q={lat},{lon}"
                self.gps_text.setPlainText(gps_str)
                self.gps_label.setText(f"📍 GPS: {lat:.4f}, {lon:.4f}")
                self.gps_label.setStyleSheet("color: #f85149; font-size: 11px; font-weight: bold; border: none;")
                self._gps_lat = lat
                self._gps_lon = lon

                gps_root = QTreeWidgetItem(self.overview_tree, ["📍 GPS Location", ""])
                gps_root.setExpanded(True)
                gps_root.setForeground(0, QColor("#f85149"))
                QTreeWidgetItem(gps_root, ["Latitude", f"{lat:.6f}°"])
                QTreeWidgetItem(gps_root, ["Longitude", f"{lon:.6f}°"])
                if alt:
                    QTreeWidgetItem(gps_root, ["Altitude", str(alt)])
            else:
                self._gps_lat = None
                self._gps_lon = None
        else:
            self._gps_lat = None
            self._gps_lon = None

        # EXIF table
        exif = result.get('exif', {})
        for tag, val in exif.items():
            row = self.exif_table.rowCount()
            self.exif_table.insertRow(row)
            tag_item = QTableWidgetItem(tag)
            tag_item.setForeground(QColor("#00f5ff"))
            val_item = QTableWidgetItem(str(val)[:200])
            self.exif_table.setItem(row, 0, tag_item)
            self.exif_table.setItem(row, 1, val_item)

        # Raw dump
        import json
        self.raw_text.setPlainText(json.dumps(result, indent=2, default=str))

        count = len(exif)
        self.status_message.emit(f"Metadata extracted: {count} EXIF tags, GPS={'Yes' if gps else 'No'}")

    def _open_maps(self):
        lat = getattr(self, '_gps_lat', None)
        lon = getattr(self, '_gps_lon', None)
        if lat is not None and lon is not None:
            import webbrowser
            webbrowser.open(f"https://maps.google.com/?q={lat},{lon}")

    def _copy_metadata(self):
        if self._result:
            import json
            text = json.dumps(self._result, indent=2, default=str)
            QApplication.clipboard().setText(text)
            self.log.append("📋 Metadata copied to clipboard")

    def apply_settings(self, s):
        pass
