"""
Inspector Rabbit - GeoIP Tracker Widget
Resolves IPs/domains and plots them on a dark world-map scatter chart.
"""

import matplotlib
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules.geo_tracker import GeoTrackThread
from .components import apply_page_header_style


ACCENT = "#06b6d4"

# Very approximate continent polygon vertices (lon, lat) — outline-only hints.
# Drawn as closed line loops so the map gives geographic context.
_CONTINENT_OUTLINES = [
    # North America
    [(-168, 72), (-50, 72), (-50, 15), (-90, 8), (-80, 8),
     (-77, 9), (-83, 9), (-90, 15), (-120, 15), (-168, 72)],
    # South America
    [(-82, 12), (-60, 12), (-35, -5), (-35, -55), (-70, -55),
     (-82, -15), (-82, 12)],
    # Europe
    [(-10, 35), (40, 35), (40, 72), (-10, 72), (-10, 35)],
    # Africa
    [(-18, 38), (52, 38), (52, -35), (-18, -35), (-18, 38)],
    # Asia
    [(25, 10), (145, 10), (145, 75), (25, 75), (25, 10)],
    # Australia
    [(113, -10), (154, -10), (154, -43), (113, -43), (113, -10)],
]


class GeoMapCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas: dark scatter plot world map."""

    def __init__(self, parent=None):
        self._fig = Figure(facecolor="#030810", figsize=(8, 4), tight_layout=True)
        super().__init__(self._fig)
        self._ax = self._fig.add_subplot(111)
        self._points: list[dict] = []
        self._init_axes()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _init_axes(self):
        ax = self._ax
        ax.set_facecolor("#030810")
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xlabel("Longitude", color="#8b949e", fontsize=8)
        ax.set_ylabel("Latitude", color="#8b949e", fontsize=8)
        ax.set_title("GeoIP Map", color="#e6edf3", fontsize=11, fontweight="bold", pad=8)
        ax.tick_params(colors="#8b949e", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#21262d")
        ax.grid(True, color="#1a2030", linewidth=0.5, linestyle="--", alpha=0.6)

        # Draw continent outlines
        for poly in _CONTINENT_OUTLINES:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            ax.plot(xs, ys, color="#1e3a4a", linewidth=0.8, alpha=0.7)

        # Reference lines
        ax.axhline(0, color="#1a2030", linewidth=0.6)   # equator
        ax.axvline(0, color="#1a2030", linewidth=0.6)   # prime meridian

    def plot_points(self, results: list[dict]):
        self._points = results
        ax = self._ax
        ax.cla()
        self._init_axes()

        valid = [r for r in results if r.get("lat") is not None and r.get("lon") is not None]

        if valid:
            lons = [r["lon"] for r in valid]
            lats = [r["lat"] for r in valid]

            # Glow effect: larger, faint outer circle
            ax.scatter(lons, lats, s=220, c=ACCENT, alpha=0.15, linewidths=0, zorder=3)
            # Main dot
            ax.scatter(lons, lats, s=60, c=ACCENT, alpha=0.95,
                       edgecolors="#ffffff", linewidths=0.5, zorder=4)

            for r in valid:
                label = r.get("city") or r.get("country") or r["ip"]
                ax.annotate(
                    label,
                    xy=(r["lon"], r["lat"]),
                    xytext=(4, 4),
                    textcoords="offset points",
                    color="#e6edf3",
                    fontsize=7,
                    zorder=5,
                )

        self.draw()


class GeoWidget(QWidget):
    send_to_graph = pyqtSignal(dict)   # included for consistency
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._results: list[dict] = []
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────────────

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

        icon = QLabel("🌍")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("GeoIP Tracker")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Geolocate IPs and domains · Batch lookup · Interactive scatter map")
        t2.setStyleSheet(
            "color: #8b949e; font-size: 11px; border: none; background: transparent;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        # Content area (full-width, no splitter)
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(20, 16, 20, 12)
        content_lay.setSpacing(10)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(
            "Enter comma-separated IPs or domains, e.g. 8.8.8.8, example.com, 1.1.1.1"
        )
        self.target_input.setFixedHeight(40)
        self.target_input.setFont(QFont("Ubuntu", 12))
        self.target_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                color: #e6edf3;
                padding: 4px 12px;
            }
            QLineEdit:focus { border-color: #06b6d4; }
        """)
        self.target_input.returnPressed.connect(self._start)
        input_row.addWidget(self.target_input, 1)

        self.track_btn = QPushButton("🌍  Track IPs")
        self.track_btn.setFixedHeight(40)
        self.track_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.track_btn.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        self.track_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22;
                border: 1px solid {ACCENT}55;
                color: {ACCENT};
                border-radius: 8px;
                padding: 4px 20px;
            }}
            QPushButton:hover {{
                background: {ACCENT}40;
                border-color: {ACCENT};
            }}
            QPushButton:pressed {{ background: {ACCENT}60; }}
            QPushButton:disabled {{ color: #484f58; border-color: #21262d; background: #010409; }}
        """)
        self.track_btn.clicked.connect(self._start)
        input_row.addWidget(self.track_btn)

        self.count_label = QLabel("0 targets")
        self.count_label.setFont(QFont("Ubuntu", 10))
        self.count_label.setStyleSheet(f"color: {ACCENT}; border: none;")
        self.count_label.setFixedWidth(80)
        input_row.addWidget(self.count_label)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(40)
        self.clear_btn.setFixedWidth(70)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #0d1117; border: 1px solid #21262d;
                color: #8b949e; border-radius: 8px;
            }
            QPushButton:hover { border-color: #484f58; color: #e6edf3; }
        """)
        self.clear_btn.clicked.connect(self._clear)
        input_row.addWidget(self.clear_btn)

        content_lay.addLayout(input_row)

        # Map canvas (stretch)
        self.map_canvas = GeoMapCanvas()
        self.map_canvas.setMinimumHeight(300)
        content_lay.addWidget(self.map_canvas, 1)

        # Results table (fixed height)
        self.table = self._make_table(
            ["IP", "Country", "City", "ISP", "Org", "AS", "Timezone", "Lat", "Lon"]
        )
        self.table.setFixedHeight(200)
        content_lay.addWidget(self.table)

        # Status bar
        self.status_lbl = QLabel("Enter IPs or domains above and click Track IPs.")
        self.status_lbl.setFont(QFont("Ubuntu", 10))
        self.status_lbl.setStyleSheet("color: #8b949e; border: none;")
        content_lay.addWidget(self.status_lbl)

        layout.addWidget(content, 1)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(
            len(headers) - 1, QHeaderView.ResizeMode.Stretch
        )
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setStyleSheet("""
            QTableWidget {
                background: #0d1117; alternate-background-color: #090d13;
                color: #c9d1d9; border: 1px solid #21262d; border-radius: 6px;
                gridline-color: #161b22;
            }
            QHeaderView::section {
                background: #010409; color: #8b949e;
                border: none; border-bottom: 1px solid #21262d;
                padding: 4px 8px; font-size: 10px; font-weight: 700;
            }
        """)
        return t

    # ── Actions ───────────────────────────────────────────────────────────────

    def _start(self):
        raw = self.target_input.text().strip()
        if not raw:
            self.status_lbl.setText("⚠️  Enter at least one IP or domain.")
            return

        targets = [t.strip() for t in raw.split(",") if t.strip()]
        self.count_label.setText(f"{len(targets)} target{'s' if len(targets) != 1 else ''}")

        self.table.setRowCount(0)
        self._results = []
        self.map_canvas.plot_points([])
        self.track_btn.setEnabled(False)
        self.status_lbl.setText(f"Tracking {len(targets)} target(s)…")

        self._thread = GeoTrackThread(targets)
        self._thread.progress.connect(self._on_progress)
        self._thread.result.connect(self._on_result)
        self._thread.done.connect(self._on_done)
        self._thread.start()
        self.status_message.emit(f"GeoIP tracking {len(targets)} target(s)…")

    def _on_progress(self, msg: str):
        self.status_lbl.setText(msg)

    def _on_result(self, r: dict):
        self._results.append(r)

        row = self.table.rowCount()
        self.table.insertRow(row)

        ip_item = QTableWidgetItem(r.get("ip", ""))
        ip_item.setForeground(QColor(ACCENT))
        ip_item.setFont(QFont("Ubuntu Mono", 10, QFont.Weight.Bold))
        self.table.setItem(row, 0, ip_item)

        flag = r.get("country_code", "").lower()
        country_text = r.get("country", "") or ("Error: " + r.get("error", "?"))
        self.table.setItem(row, 1, QTableWidgetItem(country_text))
        self.table.setItem(row, 2, QTableWidgetItem(r.get("city", "")))
        self.table.setItem(row, 3, QTableWidgetItem(r.get("isp", "")))
        self.table.setItem(row, 4, QTableWidgetItem(r.get("org", "")))
        self.table.setItem(row, 5, QTableWidgetItem(r.get("as_num", "")))
        self.table.setItem(row, 6, QTableWidgetItem(r.get("timezone", "")))

        lat = r.get("lat")
        lon = r.get("lon")
        lat_item = QTableWidgetItem(str(lat) if lat is not None else "")
        lon_item = QTableWidgetItem(str(lon) if lon is not None else "")
        lat_item.setForeground(QColor("#8b949e"))
        lon_item.setForeground(QColor("#8b949e"))
        self.table.setItem(row, 7, lat_item)
        self.table.setItem(row, 8, lon_item)

    def _on_done(self, all_results: list):
        self.track_btn.setEnabled(True)
        self.map_canvas.plot_points(all_results)
        count = len(all_results)
        mapped = sum(1 for r in all_results if r.get("lat") is not None)
        self.status_lbl.setText(
            f"✅ Done — {count} result(s), {mapped} plotted on map."
        )
        self.status_message.emit(f"GeoIP complete: {count} result(s), {mapped} mapped.")

    def _clear(self):
        self.target_input.clear()
        self.table.setRowCount(0)
        self._results = []
        self.map_canvas.plot_points([])
        self.count_label.setText("0 targets")
        self.status_lbl.setText("Cleared.")

    def apply_settings(self, s):
        pass
