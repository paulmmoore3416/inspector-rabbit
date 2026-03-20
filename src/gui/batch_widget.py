"""
Inspector Rabbit - Batch Processor Widget
Run OSINT modules against multiple targets in bulk.
"""

import csv
import json
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QProgressBar,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush

from ..modules.batch_processor import BatchProcessorThread, parse_csv_targets
from .components import apply_page_header_style

ACCENT = "#94a3b8"

MODULE_LABELS = {
    "username": "Username",
    "domain":   "Domain",
    "email":    "Email",
    "ip":       "IP Address",
    "phone":    "Phone",
}

STATUS_COLORS = {
    "done":    "#3fb950",
    "error":   "#f85149",
    "running": "#e3b341",
    "pending": "#8b949e",
}

STATUS_BG = {
    "done":    "#0d2a14",
    "error":   "#2a0d0d",
    "running": "#2a220d",
    "pending": "#0d1117",
}


class BatchWidget(QWidget):
    send_to_graph = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._jobs: list[dict] = []
        self._csv_path = ""
        self._setup_ui()

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

        icon = QLabel("📦")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(0)
        t1 = QLabel("Batch Processor")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Run OSINT modules against multiple targets · CSV import · Export results")
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

        # CSV import
        self._sec("IMPORT FROM CSV", layout)
        csv_row = QHBoxLayout()
        self.load_csv_btn = QPushButton("📂 Load CSV")
        self.load_csv_btn.setFixedHeight(34)
        self.load_csv_btn.clicked.connect(self._load_csv)
        csv_row.addWidget(self.load_csv_btn)
        layout.addLayout(csv_row)

        self.csv_lbl = QLabel("No file loaded")
        self.csv_lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        self.csv_lbl.setWordWrap(True)
        layout.addWidget(self.csv_lbl)

        layout.addWidget(self._sep())
        self._sec("MANUAL TARGETS (one per line)", layout)

        self.targets_input = QTextEdit()
        self.targets_input.setPlaceholderText("example.com\ngoogle.com\ngithub.com")
        self.targets_input.setFont(QFont("Ubuntu Mono", 10))
        self.targets_input.setFixedHeight(100)
        self.targets_input.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 6px;
                color: #e6edf3;
                font-family: 'Ubuntu Mono', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.targets_input)

        layout.addWidget(self._sep())
        self._sec("MODULE", layout)

        self.module_combo = QComboBox()
        self.module_combo.setFixedHeight(36)
        self.module_combo.setFont(QFont("Ubuntu", 11))
        for key, label in MODULE_LABELS.items():
            self.module_combo.addItem(label, key)
        self.module_combo.setStyleSheet("""
            QComboBox {
                background: #0d1117;
                border: 1px solid #21262d;
                border-radius: 6px;
                color: #e6edf3;
                padding: 4px 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #0d1117;
                border: 1px solid #21262d;
                color: #e6edf3;
                selection-background-color: #21262d;
            }
        """)
        layout.addWidget(self.module_combo)

        # Run / Stop buttons
        self.run_btn = QPushButton("▶  Run Batch")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setFixedHeight(42)
        self.run_btn.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        self.run_btn.clicked.connect(self._start_batch)
        layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⛔  Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_batch)
        layout.addWidget(self.stop_btn)

        # Progress bar
        layout.addWidget(self._sep())
        self._sec("PROGRESS", layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: none;
                border-radius: 4px;
                color: #e6edf3;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: #94a3b8;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.progress_lbl = QLabel("0 / 0")
        self.progress_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
        self.progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_lbl)

        # Status log
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
        self.status_log.setMinimumHeight(100)
        layout.addWidget(self.status_log)

        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)

        # Tab 1: Jobs
        self.jobs_table = self._make_jobs_table()
        self.tabs.addTab(self.jobs_table, "📋 Jobs")

        # Tab 2: Results summary
        self.results_view = QTextEdit()
        self.results_view.setReadOnly(True)
        self.results_view.setFont(QFont("Ubuntu", 11))
        self.results_view.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                border: none;
                color: #c9d1d9;
                padding: 16px;
            }
        """)
        self.tabs.addTab(self.results_view, "📊 Results")

        # Tab 3: Export
        export_panel = self._build_export_tab()
        self.tabs.addTab(export_panel, "💾 Export")

        return panel

    def _make_jobs_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(6)
        t.setHorizontalHeaderLabels(["#", "Target", "Module", "Status", "Result", "Time"])
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        t.setColumnWidth(0, 40)
        t.setColumnWidth(2, 90)
        t.setColumnWidth(3, 80)
        t.setColumnWidth(5, 100)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setFont(QFont("Ubuntu", 10))
        t.setAlternatingRowColors(False)
        return t

    def _build_export_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        lbl = QLabel("Export batch results to file")
        lbl.setFont(QFont("Ubuntu", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #e6edf3;")
        layout.addWidget(lbl)

        desc = QLabel(
            "Save all job results including targets, statuses, and findings "
            "as CSV or JSON for use in external tools."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        layout.addWidget(sep)

        csv_btn = QPushButton("📄  Export as CSV")
        csv_btn.setFixedHeight(42)
        csv_btn.setFont(QFont("Ubuntu", 12))
        csv_btn.clicked.connect(self._export_csv)
        layout.addWidget(csv_btn)

        json_btn = QPushButton("{ }  Export as JSON")
        json_btn.setFixedHeight(42)
        json_btn.setFont(QFont("Ubuntu", 12))
        json_btn.clicked.connect(self._export_json)
        layout.addWidget(json_btn)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sec(self, text: str, layout):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(lbl)

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _get_targets(self) -> list:
        """Collect targets from CSV or manual input."""
        if self._csv_path and os.path.isfile(self._csv_path):
            targets = parse_csv_targets(self._csv_path)
            if targets:
                return targets

        raw = self.targets_input.toPlainText().strip()
        if not raw:
            return []
        return [t.strip() for t in raw.splitlines() if t.strip()]

    def _result_summary(self, result: dict) -> str:
        """Create a short one-line summary of a job result."""
        if not result:
            return ""
        # Domain
        if "reachable" in result:
            ips = result.get("ip_addresses", [])
            status = result.get("status_code", "?")
            reachable = "up" if result.get("reachable") else "down"
            return f"{reachable} | HTTP {status} | IPs: {', '.join(ips[:2])}"
        # Email
        if "valid_format" in result:
            mx = result.get("mx_records", [])
            valid = result.get("valid_format", False)
            deliverable = result.get("deliverable", False)
            return f"{'valid' if valid else 'invalid'} | {'deliverable' if deliverable else 'no MX'} | MX: {len(mx)}"
        # IP
        if "geo" in result:
            geo = result.get("geo", {})
            country = geo.get("country", "?")
            city = geo.get("city", "")
            isp = geo.get("isp", "")
            return f"{country} / {city} | {isp}"
        # Username
        if "found_count" in result:
            count = result.get("found_count", 0)
            return f"Found on {count} site(s)"
        # Phone
        if "country" in result and "digit_count" in result:
            return f"{result.get('country', '?')} | {result.get('digit_count', '?')} digits"
        return str(result)[:80]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        self._csv_path = path
        targets = parse_csv_targets(path)
        filename = os.path.basename(path)
        self.csv_lbl.setText(f"{filename} ({len(targets)} targets)")
        self.status_log.append(f"Loaded CSV: {filename} — {len(targets)} targets")

        # Populate manual input as preview
        self.targets_input.setPlainText("\n".join(targets[:200]))

    def _start_batch(self):
        targets = self._get_targets()
        if not targets:
            self.status_log.append("No targets found. Enter targets or load a CSV.")
            return

        module_key = self.module_combo.currentData()
        module_label = self.module_combo.currentText()

        # Clear state
        self._jobs.clear()
        self.jobs_table.setRowCount(0)
        self.results_view.clear()
        self.status_log.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(targets))
        self.progress_lbl.setText(f"0 / {len(targets)}")

        self.status_log.append(
            f"Starting batch: {len(targets)} targets — module: {module_label}"
        )

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._thread = BatchProcessorThread(targets, module_key)
        self._thread.job_update.connect(self._on_job_update)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.start()

        self.status_message.emit(f"Batch processing {len(targets)} targets with module: {module_label}")

    def _stop_batch(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.terminate()
            self.status_log.append("Batch stopped by user.")
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_message.emit("Batch stopped")

    def _on_job_update(self, job: dict):
        self._jobs_upsert(job)

    def _on_progress(self, completed: int, total: int):
        self.progress_bar.setValue(completed)
        self.progress_bar.setMaximum(total)
        self.progress_lbl.setText(f"{completed} / {total}")

    def _on_done(self, jobs: list):
        self._jobs = jobs
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        total = len(jobs)
        done_count = sum(1 for j in jobs if j["status"] == "done")
        error_count = sum(1 for j in jobs if j["status"] == "error")
        success_rate = (done_count / total * 100) if total else 0

        self.status_log.append(
            f"Batch complete: {done_count}/{total} succeeded, {error_count} errors."
        )

        # Build HTML summary
        html = f"""
<div style='padding:16px;'>
  <h2 style='color:{ACCENT}; margin-bottom:8px;'>Batch Results Summary</h2>
  <table style='border-collapse:collapse; width:100%;'>
    <tr>
      <td style='padding:6px 12px; color:#8b949e;'>Total targets:</td>
      <td style='padding:6px 12px; color:#e6edf3; font-weight:bold;'>{total}</td>
    </tr>
    <tr>
      <td style='padding:6px 12px; color:#8b949e;'>Completed:</td>
      <td style='padding:6px 12px; color:#3fb950; font-weight:bold;'>{done_count}</td>
    </tr>
    <tr>
      <td style='padding:6px 12px; color:#8b949e;'>Errors:</td>
      <td style='padding:6px 12px; color:#f85149; font-weight:bold;'>{error_count}</td>
    </tr>
    <tr>
      <td style='padding:6px 12px; color:#8b949e;'>Success rate:</td>
      <td style='padding:6px 12px; color:{ACCENT}; font-weight:bold;'>{success_rate:.1f}%</td>
    </tr>
  </table>

  <h3 style='color:#8b949e; margin-top:20px;'>Error Summary</h3>
"""
        err_jobs = [j for j in jobs if j["status"] == "error"]
        if err_jobs:
            for j in err_jobs[:20]:
                html += f"  <div style='color:#f85149; margin:2px 0; font-size:11px;'>{j['target']} — {j['error_msg']}</div>\n"
        else:
            html += "  <div style='color:#3fb950; font-size:11px;'>No errors.</div>\n"

        html += "</div>"
        self.results_view.setHtml(html)
        self.tabs.setCurrentIndex(1)
        self.status_message.emit(f"Batch complete: {done_count}/{total} succeeded")

    def _jobs_upsert(self, job: dict):
        """Add or update a row in the jobs table."""
        target = job["target"]

        # Find existing row
        for row in range(self.jobs_table.rowCount()):
            item = self.jobs_table.item(row, 1)
            if item and item.text() == target:
                self._set_job_row(row, job)
                return

        # Add new row
        row = self.jobs_table.rowCount()
        self.jobs_table.insertRow(row)
        self._set_job_row(row, job)

        # Also update internal list
        for existing in self._jobs:
            if existing.get("target") == target:
                existing.update(job)
                return
        self._jobs.append(job)

    def _set_job_row(self, row: int, job: dict):
        status = job.get("status", "pending")
        color = STATUS_COLORS.get(status, "#8b949e")
        bg = STATUS_BG.get(status, "#0d1117")

        def cell(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(str(text))
            item.setForeground(QColor(color))
            item.setBackground(QColor(bg))
            return item

        num_item = QTableWidgetItem(str(row + 1))
        num_item.setForeground(QColor("#484f58"))
        num_item.setBackground(QColor(bg))
        self.jobs_table.setItem(row, 0, num_item)

        self.jobs_table.setItem(row, 1, cell(job.get("target", "")))
        self.jobs_table.setItem(row, 2, cell(job.get("module", "").capitalize()))

        status_item = QTableWidgetItem(status.upper())
        status_item.setForeground(QColor(color))
        status_item.setBackground(QColor(bg))
        status_item.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        self.jobs_table.setItem(row, 3, status_item)

        # Result / error summary
        if status == "error":
            result_text = job.get("error_msg", "")[:100]
        else:
            result_text = self._result_summary(job.get("result", {}))
        self.jobs_table.setItem(row, 4, cell(result_text))

        # Duration
        started = job.get("started_at", "")
        completed = job.get("completed_at", "")
        if started and completed:
            try:
                from datetime import datetime
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                s = datetime.strptime(started, fmt)
                c = datetime.strptime(completed, fmt)
                dur = (c - s).total_seconds()
                time_str = f"{dur:.1f}s"
            except Exception:
                time_str = completed[-8:] if len(completed) >= 8 else completed
        elif started:
            time_str = "running..."
        else:
            time_str = ""
        self.jobs_table.setItem(row, 5, cell(time_str))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self):
        if not self._jobs:
            QMessageBox.information(self, "No Data", "Run a batch first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "batch_results.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["#", "Target", "Module", "Status", "Result", "Error", "Started", "Completed"])
                for idx, job in enumerate(self._jobs, 1):
                    result_str = self._result_summary(job.get("result", {}))
                    writer.writerow([
                        idx,
                        job.get("target", ""),
                        job.get("module", ""),
                        job.get("status", ""),
                        result_str,
                        job.get("error_msg", ""),
                        job.get("started_at", ""),
                        job.get("completed_at", ""),
                    ])
            self.status_log.append(f"CSV exported: {path}")
        except Exception as exc:
            self.status_log.append(f"Export failed: {exc}")

    def _export_json(self):
        if not self._jobs:
            QMessageBox.information(self, "No Data", "Run a batch first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "batch_results.json", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._jobs, fh, indent=2, default=str)
            self.status_log.append(f"JSON exported: {path}")
        except Exception as exc:
            self.status_log.append(f"Export failed: {exc}")

    def apply_settings(self, settings: dict):
        pass
