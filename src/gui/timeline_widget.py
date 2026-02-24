"""
Inspector Rabbit - OSINT Investigation Timeline
Chronological log of all findings and investigation events
"""

import json
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QApplication, QSplitter,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor


TIMELINE_FILE = os.path.expanduser("~/.inspector_rabbit_timeline.json")

EVENT_TYPES = {
    'username': ('👤', '#a78bfa'),
    'domain':   ('🌐', '#60a5fa'),
    'email':    ('✉️',  '#34d399'),
    'ip':       ('🖥️', '#f87171'),
    'phone':    ('📞', '#22d3ee'),
    'cert':     ('🔐', '#fbbf24'),
    'metadata': ('📄', '#fb923c'),
    'paste':    ('📋', '#f472b6'),
    'dork':     ('🔍', '#818cf8'),
    'crawler':  ('🕷️', '#4ade80'),
    'note':     ('📝', '#8b949e'),
    'graph':    ('🕸️', '#00f5ff'),
}


def _load_timeline() -> list:
    try:
        with open(TIMELINE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def _save_timeline(events: list):
    try:
        with open(TIMELINE_FILE, 'w') as f:
            json.dump(events[-500:], f, indent=2)  # Keep last 500 events
    except Exception:
        pass


class TimelineWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = _load_timeline()
        self._filter_type = 'all'
        self._filter_text = ''
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #010409; border-bottom: 1px solid #21262d; }")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        icon = QLabel("📅")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)
        vl = QVBoxLayout()
        t1 = QLabel("Investigation Timeline")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Chronological OSINT event log · Auto-captures all findings · Add custom notes")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()

        clear_btn = QPushButton("🗑️ Clear Timeline")
        clear_btn.setFixedHeight(36)
        clear_btn.setFixedWidth(140)
        clear_btn.clicked.connect(self._clear_timeline)
        bl.addWidget(clear_btn)

        export_btn = QPushButton("💾 Export")
        export_btn.setObjectName("primaryBtn")
        export_btn.setFixedHeight(36)
        export_btn.setFixedWidth(90)
        export_btn.clicked.connect(self._export)
        bl.addWidget(export_btn)

        layout.addWidget(bar)

        # Filter bar
        filter_bar = QFrame()
        filter_bar.setStyleSheet("QFrame { background: #0d1117; border-bottom: 1px solid #21262d; }")
        filter_bar.setFixedHeight(52)
        fb_lay = QHBoxLayout(filter_bar)
        fb_lay.setContentsMargins(24, 8, 24, 8)
        fb_lay.setSpacing(12)

        fb_lay.addWidget(QLabel("Filter:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("All Types", "all")
        for key, (icon, _) in EVENT_TYPES.items():
            self.type_combo.addItem(f"{icon} {key.title()}", key)
        self.type_combo.setFixedWidth(160)
        self.type_combo.currentIndexChanged.connect(self._on_filter_change)
        fb_lay.addWidget(self.type_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search timeline...")
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._on_filter_change)
        fb_lay.addWidget(self.search_input, 1)

        self.count_label = QLabel("0 events")
        self.count_label.setStyleSheet("color: #484f58; font-size: 11px;")
        fb_lay.addWidget(self.count_label)

        layout.addWidget(filter_bar)

        # Main splitter: table left, detail right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")
        layout.addWidget(splitter, 1)

        # Events table
        table_widget = QWidget()
        table_lay = QVBoxLayout(table_widget)
        table_lay.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Time", "Type", "Target", "Summary", "Tags"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(4, 100)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self._on_selection)
        table_lay.addWidget(self.table)

        # Note add row
        note_row = QHBoxLayout()
        note_row.setContentsMargins(8, 6, 8, 8)
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Add investigation note...")
        self.note_input.setFixedHeight(36)
        self.note_input.returnPressed.connect(self._add_note)
        note_row.addWidget(self.note_input)
        add_note_btn = QPushButton("➕ Add Note")
        add_note_btn.setFixedHeight(36)
        add_note_btn.setFixedWidth(110)
        add_note_btn.clicked.connect(self._add_note)
        note_row.addWidget(add_note_btn)
        table_lay.addLayout(note_row)
        splitter.addWidget(table_widget)

        # Detail panel
        detail_panel = QWidget()
        detail_panel.setMinimumWidth(340)
        dl = QVBoxLayout(detail_panel)
        dl.setContentsMargins(12, 12, 12, 12)
        dl.setSpacing(8)

        dl.addWidget(QLabel("Event Detail"))
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Ubuntu Mono", 10))
        self.detail_text.setStyleSheet(
            "QTextEdit { background:#0d1117; border:1px solid #21262d; "
            "border-radius:8px; color:#c9d1d9; font-size:11px; }"
        )
        dl.addWidget(self.detail_text, 1)

        # Stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            "QFrame { background:#161b22; border:1px solid #21262d; border-radius:8px; }"
        )
        sl = QVBoxLayout(stats_frame)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(4)
        stats_title = QLabel("Session Statistics")
        stats_title.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        stats_title.setStyleSheet("color: #8b949e; border: none;")
        sl.addWidget(stats_title)
        self.stats_label = QLabel("No events yet")
        self.stats_label.setStyleSheet("color: #c9d1d9; font-size: 11px; border: none;")
        self.stats_label.setWordWrap(True)
        sl.addWidget(self.stats_label)
        dl.addWidget(stats_frame)

        splitter.addWidget(detail_panel)
        splitter.setSizes([700, 340])

    def _on_filter_change(self):
        self._filter_type = self.type_combo.currentData() or 'all'
        self._filter_text = self.search_input.text().lower()
        self._refresh_table()

    def _refresh_table(self):
        filtered = self._get_filtered()
        # Sort newest first
        filtered = sorted(filtered, key=lambda e: e.get('timestamp', ''), reverse=True)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for ev in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)

            ts = ev.get('timestamp', '')[:16].replace('T', ' ')
            ev_type = ev.get('type', 'note')
            icon, color_hex = EVENT_TYPES.get(ev_type, ('●', '#8b949e'))

            time_item = QTableWidgetItem(ts)
            time_item.setForeground(QColor("#484f58"))
            time_item.setFont(QFont("Ubuntu Mono", 9))
            self.table.setItem(row, 0, time_item)

            type_item = QTableWidgetItem(f"{icon} {ev_type}")
            type_item.setForeground(QColor(color_hex))
            type_item.setFont(QFont("Ubuntu", 9, QFont.Weight.Bold))
            self.table.setItem(row, 1, type_item)

            target_item = QTableWidgetItem(ev.get('target', ''))
            target_item.setForeground(QColor("#00f5ff"))
            self.table.setItem(row, 2, target_item)

            summary_item = QTableWidgetItem(ev.get('summary', '')[:100])
            self.table.setItem(row, 3, summary_item)

            tags = ', '.join(ev.get('tags', []))
            tag_item = QTableWidgetItem(tags)
            tag_item.setForeground(QColor("#a78bfa"))
            self.table.setItem(row, 4, tag_item)

            # Store full event in user data
            time_item.setData(Qt.ItemDataRole.UserRole, ev)

        self.table.setSortingEnabled(True)
        self.count_label.setText(f"{len(filtered)} events")
        self._update_stats()

    def _get_filtered(self) -> list:
        result = self._events
        if self._filter_type != 'all':
            result = [e for e in result if e.get('type') == self._filter_type]
        if self._filter_text:
            txt = self._filter_text
            result = [e for e in result
                      if txt in e.get('target', '').lower()
                      or txt in e.get('summary', '').lower()
                      or txt in ' '.join(e.get('tags', [])).lower()]
        return result

    def _on_selection(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        ev = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not ev:
            return
        ev_type = ev.get('type', 'note')
        icon, color_hex = EVENT_TYPES.get(ev_type, ('●', '#8b949e'))
        ts = ev.get('timestamp', '')[:19].replace('T', ' ')
        detail = (
            f"{'─'*40}\n"
            f"  {icon}  {ev_type.upper()} EVENT\n"
            f"  Time:    {ts}\n"
            f"  Target:  {ev.get('target', '—')}\n"
            f"  Summary: {ev.get('summary', '—')}\n"
        )
        tags = ev.get('tags', [])
        if tags:
            detail += f"  Tags:    {', '.join(tags)}\n"
        detail += f"{'─'*40}\n"
        data = ev.get('data', {})
        if data:
            detail += "\nData:\n"
            for k, v in data.items():
                detail += f"  {k}: {v}\n"
        self.detail_text.setPlainText(detail)

    def _update_stats(self):
        if not self._events:
            self.stats_label.setText("No events recorded yet.")
            return
        counts = {}
        for ev in self._events:
            t = ev.get('type', 'note')
            counts[t] = counts.get(t, 0) + 1
        lines = [f"Total: {len(self._events)} events"]
        for ev_type, count in sorted(counts.items(), key=lambda x: -x[1])[:6]:
            icon, _ = EVENT_TYPES.get(ev_type, ('●', ''))
            lines.append(f"  {icon} {ev_type}: {count}")
        self.stats_label.setText('\n'.join(lines))

    def _add_note(self):
        text = self.note_input.text().strip()
        if not text:
            return
        self.add_event('note', 'Manual Note', text, tags=['note', 'manual'])
        self.note_input.clear()

    def _clear_timeline(self):
        reply = QMessageBox.question(
            self, "Clear Timeline",
            "Clear all timeline events? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._events.clear()
            _save_timeline(self._events)
            self._refresh_table()
            self.detail_text.clear()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Timeline",
            os.path.expanduser("~/inspector_rabbit_timeline.json"),
            "JSON (*.json);;Text (*.txt)"
        )
        if not path:
            return
        try:
            if path.endswith('.txt'):
                lines = []
                for ev in sorted(self._events, key=lambda e: e.get('timestamp', '')):
                    ts = ev.get('timestamp', '')[:19].replace('T', ' ')
                    lines.append(f"[{ts}] [{ev.get('type','?').upper()}] {ev.get('target','')} — {ev.get('summary','')}")
                with open(path, 'w') as f:
                    f.write('\n'.join(lines))
            else:
                with open(path, 'w') as f:
                    json.dump(self._events, f, indent=2)
            self.status_message.emit(f"Timeline exported: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    # ── Public API called by other widgets ──────────────────────────────────

    def add_event(self, ev_type: str, target: str, summary: str,
                  data: dict = None, tags: list = None):
        """Add a new event to the timeline. Called by other widgets."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': ev_type,
            'target': target,
            'summary': summary,
            'data': data or {},
            'tags': tags or [],
        }
        self._events.append(event)
        _save_timeline(self._events)
        self._refresh_table()
        self.status_message.emit(f"Timeline: {ev_type} — {target}")

    def apply_settings(self, s):
        pass
