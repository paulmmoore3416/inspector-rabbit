"""
Inspector Rabbit - Case Manager Widget
Create, browse, and export OSINT investigation cases.
"""

import os
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QListWidget, QListWidgetItem,
    QSplitter, QComboBox, QMessageBox, QFileDialog, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..modules import case_manager
from .components import apply_page_header_style


ACCENT = "#f59e0b"

STATUS_ICONS = {
    "active":   "🟢",
    "closed":   "🔴",
    "archived": "⚪",
}
STATUS_COLORS = {
    "active":   "#3fb950",
    "closed":   "#f85149",
    "archived": "#8b949e",
}


class CaseWidget(QWidget):
    send_to_graph  = pyqtSignal(dict)   # included for consistency
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cases: list[dict] = []
        self._current_case_id: str = ""
        self._setup_ui()
        self._refresh_list()

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

        icon = QLabel("🗂️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Case Manager")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel(
            "Organize investigations · Track events · Export reports"
        )
        t2.setStyleSheet(
            "color: #8b949e; font-size: 11px; border: none; background: transparent;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()
        layout.addWidget(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")
        layout.addWidget(splitter, 1)

        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([300, 900])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(300)
        panel.setStyleSheet(
            "QFrame { background: #010409; border-right: 1px solid #21262d; }"
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(10)

        # ── New Case form ──────────────────────────────────────────────────────
        self._lbl("NEW CASE", lay)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Case name…")
        self.name_input.setFixedHeight(36)
        self.name_input.setFont(QFont("Ubuntu", 11))
        self._style_input(self.name_input)
        lay.addWidget(self.name_input)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Primary target (domain, email…)")
        self.target_input.setFixedHeight(36)
        self.target_input.setFont(QFont("Ubuntu", 11))
        self._style_input(self.target_input)
        lay.addWidget(self.target_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Tags: osint, recon, phishing…")
        self.tags_input.setFixedHeight(36)
        self.tags_input.setFont(QFont("Ubuntu", 11))
        self._style_input(self.tags_input)
        lay.addWidget(self.tags_input)

        self.create_btn = QPushButton("🗂️  Create Case")
        self.create_btn.setFixedHeight(38)
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22; border: 1px solid {ACCENT}55;
                color: {ACCENT}; border-radius: 8px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: {ACCENT}40; border-color: {ACCENT}; }}
            QPushButton:pressed {{ background: {ACCENT}60; }}
        """)
        self.create_btn.clicked.connect(self._create_case)
        lay.addWidget(self.create_btn)

        lay.addWidget(self._sep())

        # ── Search ─────────────────────────────────────────────────────────────
        self._lbl("SEARCH CASES", lay)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter cases…")
        self.search_input.setFixedHeight(34)
        self.search_input.setFont(QFont("Ubuntu", 11))
        self._style_input(self.search_input)
        self.search_input.textChanged.connect(self._on_search)
        lay.addWidget(self.search_input)

        # ── Case list ──────────────────────────────────────────────────────────
        self._lbl("CASES", lay)
        self.case_list = QListWidget()
        self.case_list.setFont(QFont("Ubuntu", 10))
        self.case_list.setStyleSheet("""
            QListWidget {
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 8px; color: #c9d1d9;
            }
            QListWidget::item {
                padding: 8px 10px; border-bottom: 1px solid #161b22;
            }
            QListWidget::item:selected {
                background: #1f2937; color: #e6edf3;
                border-left: 3px solid #f59e0b;
            }
            QListWidget::item:hover { background: #111820; }
        """)
        self.case_list.currentItemChanged.connect(self._on_case_selected)
        lay.addWidget(self.case_list, 1)

        # Delete button
        self.delete_btn = QPushButton("🗑️  Delete Case")
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: #2d0d0d; border: 1px solid #f8514933;
                color: #f85149; border-radius: 7px; font-size: 11px;
            }
            QPushButton:hover { background: #3d1010; border-color: #f85149; }
            QPushButton:disabled { color: #484f58; border-color: #21262d; background: #010409; }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_case)
        lay.addWidget(self.delete_btn)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 14, 20, 14)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #21262d; border-radius: 6px; }}
            QTabBar::tab {{
                background: #010409; color: #8b949e;
                padding: 8px 16px; border: 1px solid #21262d;
                border-bottom: none; border-radius: 6px 6px 0 0; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: #0d1117; color: #e6edf3; border-bottom: 2px solid {ACCENT}; }}
            QTabBar::tab:hover {{ background: #0d1117; color: #c9d1d9; }}
        """)
        lay.addWidget(self.tabs)

        # ── Tab 1: Overview ────────────────────────────────────────────────────
        overview = QWidget()
        ov_lay = QVBoxLayout(overview)
        ov_lay.setContentsMargins(20, 20, 20, 20)
        ov_lay.setSpacing(10)

        self.ov_title = QLabel("Select a case to view details.")
        self.ov_title.setFont(QFont("Ubuntu", 14, QFont.Weight.Bold))
        self.ov_title.setStyleSheet(f"color: {ACCENT}; border: none;")
        ov_lay.addWidget(self.ov_title)

        grid_frame = QFrame()
        grid_frame.setStyleSheet(
            "QFrame { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; }"
        )
        gfl = QVBoxLayout(grid_frame)
        gfl.setContentsMargins(16, 12, 16, 12)
        gfl.setSpacing(6)

        def _field_row(label: str) -> QLabel:
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            rlay = QHBoxLayout(row_widget)
            rlay.setContentsMargins(0, 0, 0, 0)
            rlay.setSpacing(8)
            lbl = QLabel(label + ":")
            lbl.setFixedWidth(80)
            lbl.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #8b949e; background: transparent; border: none;")
            rlay.addWidget(lbl)
            val = QLabel("—")
            val.setFont(QFont("Ubuntu", 10))
            val.setStyleSheet("color: #e6edf3; background: transparent; border: none;")
            val.setWordWrap(True)
            rlay.addWidget(val, 1)
            gfl.addWidget(row_widget)
            return val

        self.ov_name      = _field_row("Name")
        self.ov_target    = _field_row("Target")
        self.ov_created   = _field_row("Created")
        self.ov_updated   = _field_row("Updated")
        self.ov_status    = _field_row("Status")
        self.ov_tags      = _field_row("Tags")
        self.ov_events    = _field_row("Events")
        ov_lay.addWidget(grid_frame)

        # Status change combo
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_lbl = QLabel("Change Status:")
        status_lbl.setFont(QFont("Ubuntu", 10))
        status_lbl.setStyleSheet("color: #8b949e; border: none;")
        status_row.addWidget(status_lbl)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "closed", "archived"])
        self.status_combo.setFixedHeight(34)
        self.status_combo.setFont(QFont("Ubuntu", 10))
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 7px; color: #e6edf3; padding: 4px 12px;
            }}
            QComboBox QAbstractItemView {{
                background: #0d1117; color: #e6edf3;
                selection-background-color: {ACCENT}33;
            }}
        """)
        status_row.addWidget(self.status_combo)
        save_status_btn = QPushButton("Save")
        save_status_btn.setFixedHeight(34)
        save_status_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22; border: 1px solid {ACCENT}44;
                color: {ACCENT}; border-radius: 7px; padding: 4px 14px;
            }}
            QPushButton:hover {{ background: {ACCENT}40; }}
        """)
        save_status_btn.clicked.connect(self._save_status)
        status_row.addWidget(save_status_btn)
        status_row.addStretch()
        ov_lay.addLayout(status_row)

        ov_lay.addStretch()
        self.tabs.addTab(overview, "📋 Overview")

        # ── Tab 2: Events ──────────────────────────────────────────────────────
        events_widget = QWidget()
        ev_lay = QVBoxLayout(events_widget)
        ev_lay.setContentsMargins(16, 12, 16, 12)

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(
            ["Time", "Module", "Target", "Summary"]
        )
        self.events_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.events_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.setStyleSheet("""
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
        ev_lay.addWidget(self.events_table)
        self.tabs.addTab(events_widget, "📅 Events (0)")

        # ── Tab 3: Notes ───────────────────────────────────────────────────────
        notes_widget = QWidget()
        notes_lay = QVBoxLayout(notes_widget)
        notes_lay.setContentsMargins(16, 12, 16, 12)
        notes_lay.setSpacing(8)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFont(QFont("Ubuntu", 11))
        self.notes_edit.setPlaceholderText(
            "Investigation notes…\n\nSelect a case first."
        )
        self.notes_edit.setStyleSheet("""
            QTextEdit {
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 8px; color: #e6edf3; padding: 8px;
            }
        """)
        notes_lay.addWidget(self.notes_edit, 1)

        save_notes_btn = QPushButton("💾  Save Notes")
        save_notes_btn.setFixedHeight(38)
        save_notes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_notes_btn.setFont(QFont("Ubuntu", 10, QFont.Weight.Bold))
        save_notes_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}22; border: 1px solid {ACCENT}55;
                color: {ACCENT}; border-radius: 8px; padding: 4px 16px;
            }}
            QPushButton:hover {{ background: {ACCENT}40; border-color: {ACCENT}; }}
            QPushButton:pressed {{ background: {ACCENT}60; }}
        """)
        save_notes_btn.clicked.connect(self._save_notes)
        notes_lay.addWidget(save_notes_btn)
        self.tabs.addTab(notes_widget, "📝 Notes")

        # ── Tab 4: Export ──────────────────────────────────────────────────────
        export_widget = QWidget()
        exp_lay = QVBoxLayout(export_widget)
        exp_lay.setContentsMargins(32, 32, 32, 32)
        exp_lay.setSpacing(16)

        exp_label = QLabel("Export current case:")
        exp_label.setFont(QFont("Ubuntu", 12, QFont.Weight.Bold))
        exp_label.setStyleSheet("color: #e6edf3; border: none;")
        exp_lay.addWidget(exp_label)

        exp_desc = QLabel(
            "Export the selected case as a JSON data file or a human-readable "
            "plaintext report."
        )
        exp_desc.setWordWrap(True)
        exp_desc.setStyleSheet("color: #8b949e; font-size: 11px; border: none;")
        exp_lay.addWidget(exp_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.json_btn = QPushButton("📄  Export JSON")
        self.json_btn.setFixedHeight(44)
        self.json_btn.setFixedWidth(160)
        self.json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.json_btn.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        self.json_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1f2937; border: 1px solid {ACCENT}44;
                color: {ACCENT}; border-radius: 8px;
            }}
            QPushButton:hover {{ background: {ACCENT}22; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #484f58; border-color: #21262d; }}
        """)
        self.json_btn.setEnabled(False)
        self.json_btn.clicked.connect(self._export_json)
        btn_row.addWidget(self.json_btn)

        self.txt_btn = QPushButton("📋  Export TXT Report")
        self.txt_btn.setFixedHeight(44)
        self.txt_btn.setFixedWidth(180)
        self.txt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.txt_btn.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        self.txt_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1f2937; border: 1px solid {ACCENT}44;
                color: {ACCENT}; border-radius: 8px;
            }}
            QPushButton:hover {{ background: {ACCENT}22; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #484f58; border-color: #21262d; }}
        """)
        self.txt_btn.setEnabled(False)
        self.txt_btn.clicked.connect(self._export_txt)
        btn_row.addWidget(self.txt_btn)

        btn_row.addStretch()
        exp_lay.addLayout(btn_row)

        self.export_status = QLabel("")
        self.export_status.setFont(QFont("Ubuntu", 10))
        self.export_status.setStyleSheet("color: #3fb950; border: none;")
        exp_lay.addWidget(self.export_status)

        exp_lay.addStretch()
        self.tabs.addTab(export_widget, "💾 Export")

        return panel

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _lbl(self, text: str, lay):
        l = QLabel(text)
        l.setStyleSheet(
            "color: #484f58; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        lay.addWidget(l)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background: #21262d; max-height: 1px; border: none;")
        return f

    def _style_input(self, w: QLineEdit):
        w.setStyleSheet(f"""
            QLineEdit {{
                background: #0d1117; border: 1px solid #21262d;
                border-radius: 7px; color: #e6edf3; padding: 4px 10px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)

    def _refresh_list(self, query: str = ""):
        if query:
            self._cases = case_manager.search_cases(query)
        else:
            self._cases = case_manager.list_cases()

        self.case_list.clear()
        for c in self._cases:
            icon = STATUS_ICONS.get(c["status"], "⚪")
            label = f"{icon} {c['name']}\n    {c['target']}  ·  {c['event_count']} event(s)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, c["case_id"])
            item.setFont(QFont("Ubuntu", 10))
            self.case_list.addItem(item)

    def _load_case_to_ui(self, case_id: str):
        try:
            case = case_manager.load_case(case_id)
        except Exception:
            return

        self._current_case_id = case_id
        icon = STATUS_ICONS.get(case.status, "⚪")
        color = STATUS_COLORS.get(case.status, "#8b949e")

        self.ov_title.setText(f"{icon} {case.name}")
        self.ov_name.setText(case.name)
        self.ov_target.setText(case.target)
        self.ov_created.setText(case.created_at)
        self.ov_updated.setText(case.updated_at)
        self.ov_status.setText(f"<span style='color:{color};'>{icon} {case.status.upper()}</span>")
        self.ov_tags.setText(", ".join(case.tags) if case.tags else "—")
        self.ov_events.setText(str(len(case.events)))

        # Sync status combo
        idx = self.status_combo.findText(case.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        # Notes
        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(case.notes)
        self.notes_edit.blockSignals(False)

        # Events table
        self.events_table.setRowCount(0)
        for ev in case.events:
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            ts_item = QTableWidgetItem(ev.timestamp[:19])
            ts_item.setForeground(QColor("#8b949e"))
            ts_item.setFont(QFont("Ubuntu Mono", 9))
            self.events_table.setItem(row, 0, ts_item)
            mod_item = QTableWidgetItem(ev.module)
            mod_item.setForeground(QColor(ACCENT))
            self.events_table.setItem(row, 1, mod_item)
            self.events_table.setItem(row, 2, QTableWidgetItem(ev.target))
            self.events_table.setItem(row, 3, QTableWidgetItem(ev.summary))

        # Update events tab label
        ev_idx = self.tabs.indexOf(
            self.events_table.parent().parent()  # events QWidget
        )
        # Walk up to find the widget added to tabs
        for i in range(self.tabs.count()):
            if "Events" in self.tabs.tabText(i):
                self.tabs.setTabText(i, f"📅 Events ({len(case.events)})")
                break

        # Enable export buttons
        self.json_btn.setEnabled(True)
        self.txt_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.status_message.emit(f"Case loaded: {case.name}")

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._refresh_list(text)

    def _on_case_selected(self, current: QListWidgetItem, _previous):
        if current is None:
            return
        case_id = current.data(Qt.ItemDataRole.UserRole)
        if case_id:
            self._load_case_to_ui(case_id)

    def _create_case(self):
        name   = self.name_input.text().strip()
        target = self.target_input.text().strip()
        tags_raw = self.tags_input.text().strip()

        if not name:
            self.status_message.emit("⚠️  Case name is required.")
            return
        if not target:
            self.status_message.emit("⚠️  Target is required.")
            return

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        case = case_manager.create_case(name, target, tags)

        self.name_input.clear()
        self.target_input.clear()
        self.tags_input.clear()

        self._refresh_list()

        # Select the new case in the list
        for i in range(self.case_list.count()):
            item = self.case_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == case.case_id:
                self.case_list.setCurrentItem(item)
                break

        self.status_message.emit(f"Case created: {name}")

    def _delete_case(self):
        if not self._current_case_id:
            return
        reply = QMessageBox.question(
            self,
            "Delete Case",
            "Are you sure you want to permanently delete this case?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            case_manager.delete_case(self._current_case_id)
            self._current_case_id = ""
            self.delete_btn.setEnabled(False)
            self.json_btn.setEnabled(False)
            self.txt_btn.setEnabled(False)
            self.ov_title.setText("Select a case to view details.")
            self.notes_edit.clear()
            self.events_table.setRowCount(0)
            self._refresh_list()
            self.status_message.emit("Case deleted.")

    def _save_notes(self):
        if not self._current_case_id:
            self.status_message.emit("⚠️  No case selected.")
            return
        try:
            c = case_manager.load_case(self._current_case_id)
            c.notes = self.notes_edit.toPlainText()
            case_manager.save_case(c)
            self.status_message.emit("Notes saved.")
        except Exception as exc:
            self.status_message.emit(f"❌ Failed to save notes: {exc}")

    def _save_status(self):
        if not self._current_case_id:
            return
        try:
            c = case_manager.load_case(self._current_case_id)
            c.status = self.status_combo.currentText()
            case_manager.save_case(c)
            self._refresh_list()
            self._load_case_to_ui(self._current_case_id)
            self.status_message.emit(f"Status updated: {c.status}")
        except Exception as exc:
            self.status_message.emit(f"❌ Failed to update status: {exc}")

    def _export_json(self):
        if not self._current_case_id:
            return
        try:
            content = case_manager.export_case_json(self._current_case_id)
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Case as JSON", f"case_{self._current_case_id[:8]}.json",
                "JSON Files (*.json)"
            )
            if path:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                self.export_status.setText(f"✅ JSON exported: {os.path.basename(path)}")
                self.status_message.emit(f"Case exported: {path}")
        except Exception as exc:
            self.export_status.setText(f"❌ Export failed: {exc}")

    def _export_txt(self):
        if not self._current_case_id:
            return
        try:
            content = case_manager.export_case_txt(self._current_case_id)
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Case as Text Report", f"case_{self._current_case_id[:8]}.txt",
                "Text Files (*.txt)"
            )
            if path:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                self.export_status.setText(f"✅ TXT report exported: {os.path.basename(path)}")
                self.status_message.emit(f"Case report exported: {path}")
        except Exception as exc:
            self.export_status.setText(f"❌ Export failed: {exc}")

    def apply_settings(self, s):
        pass
