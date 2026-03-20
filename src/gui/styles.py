"""
Inspector Rabbit - Global Stylesheet  v1.5.0
Professional dark theme — refined developer tool aesthetic.
"""

MAIN_STYLE = """
/* ===== Global ===== */
QWidget {
    background-color: #0a0e17;
    color: #cbd5e1;
    font-family: 'Ubuntu', 'Segoe UI', 'Noto Sans', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0a0e17;
}

QDialog {
    background: #0a0e17;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1e2a3a;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #1e2a3a;
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ===== Scroll Area ===== */
QScrollArea {
    background: transparent;
    border: none;
}

/* ===== Input Fields ===== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e2e8f0;
    selection-background-color: #1e3a5f;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
}
QLineEdit:hover {
    border: 1px solid #2d3f55;
}

/* ===== Buttons ===== */
QPushButton {
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 8px 16px;
    color: #e2e8f0;
    font-weight: 500;
}
QPushButton:hover {
    background: #1a2233;
    border: 1px solid #2d3f55;
}
QPushButton:pressed {
    background: #0d1220;
    border: 1px solid #3b82f6;
}
QPushButton:disabled {
    color: #475569;
    border: 1px solid #1a2030;
    background: #0a0e17;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #3b82f6);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:1 #2563eb);
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1e40af, stop:1 #1d4ed8);
}

QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #dc2626, stop:1 #ef4444);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 6px;
}
QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #b91c1c, stop:1 #dc2626);
}

QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 6px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #047857, stop:1 #059669);
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 7px 12px;
    color: #e2e8f0;
    min-width: 100px;
}
QComboBox:hover {
    border: 1px solid #2d3f55;
}
QComboBox:focus {
    border: 1px solid #3b82f6;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid #1e2a3a;
    selection-background-color: #1e3a5f;
    color: #e2e8f0;
    border-radius: 6px;
    padding: 4px;
}

/* ===== SpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e2e8f0;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3b82f6;
}

/* ===== CheckBox ===== */
QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #1e2a3a;
    background: #111827;
}
QCheckBox::indicator:checked {
    background: #3b82f6;
    border: none;
}
QCheckBox::indicator:hover {
    border: 1px solid #3b82f6;
}

/* ===== Radio Button ===== */
QRadioButton {
    color: #cbd5e1;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #1e2a3a;
    background: #111827;
}
QRadioButton::indicator:checked {
    background: #3b82f6;
    border: 2px solid #0a0e17;
    outline: 1px solid #3b82f6;
}

/* ===== Tables ===== */
QTableWidget, QTableView {
    background-color: #0a0e17;
    alternate-background-color: #0d1220;
    gridline-color: #1a2030;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    selection-background-color: #1e3a5f;
    selection-color: #e2e8f0;
}
QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #1e3a5f;
    color: #e2e8f0;
}
QHeaderView::section {
    background-color: #0d1220;
    color: #475569;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #1a2030;
    border-bottom: 1px solid #1e2a3a;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}
QHeaderView::section:hover {
    background-color: #111827;
    color: #64748b;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #0d1220;
    border: 1px solid #1e2a3a;
    border-radius: 4px;
    text-align: center;
    color: #94a3b8;
    height: 12px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #3b82f6);
    border-radius: 3px;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: none;
    border-top: 1px solid #1e2a3a;
    background: #0a0e17;
}
QTabBar {
    background: #0a0e17;
}
QTabBar::tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 18px;
    margin-right: 2px;
    color: #475569;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #e2e8f0;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover:!selected {
    color: #94a3b8;
    border-bottom: 2px solid #2d3f55;
}

/* ===== Group Box ===== */
QGroupBox {
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 10px;
    color: #475569;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: #0a0e17;
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background: #1a2030;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background: #070b12;
    border-bottom: 1px solid #1a2030;
    color: #64748b;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: #111827;
    color: #94a3b8;
}

/* ===== Menu ===== */
QMenu {
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    color: #cbd5e1;
}
QMenu::item:selected {
    background: #1e3a5f;
    color: #e2e8f0;
}
QMenu::separator {
    height: 1px;
    background: #1e2a3a;
    margin: 4px 8px;
}

/* ===== Status Bar ===== */
QStatusBar {
    background: #070b12;
    border-top: 1px solid #1a2030;
    color: #374151;
    font-size: 11px;
    padding: 2px 8px;
}

/* ===== Tooltip ===== */
QToolTip {
    background: #1e2a3a;
    border: 1px solid #2d3f55;
    color: #e2e8f0;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ===== Tree Widget ===== */
QTreeWidget {
    background: #0a0e17;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    color: #cbd5e1;
}
QTreeWidget::item {
    padding: 4px 0;
}
QTreeWidget::item:selected {
    background: #1e3a5f;
    color: #e2e8f0;
}
QTreeWidget::item:hover {
    background: #111827;
}
QTreeWidget::branch {
    background: transparent;
}

/* ===== List Widget ===== */
QListWidget {
    background: #0a0e17;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    color: #cbd5e1;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #1e3a5f;
    color: #e2e8f0;
}
QListWidget::item:hover {
    background: #111827;
}

/* ===== Slider ===== */
QSlider::groove:horizontal {
    height: 4px;
    background: #1e2a3a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3b82f6;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 2px;
}

/* ===== Labels ===== */
QLabel {
    color: #cbd5e1;
}
QLabel#titleLabel {
    font-size: 20px;
    font-weight: 700;
    color: #e2e8f0;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #94a3b8;
}
QLabel#sectionLabel {
    font-size: 10px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QLabel#accentLabel {
    color: #3b82f6;
    font-weight: 600;
}
QLabel#successLabel {
    color: #10b981;
    font-weight: 600;
}
QLabel#errorLabel {
    color: #ef4444;
    font-weight: 600;
}
QLabel#warningLabel {
    color: #f59e0b;
    font-weight: 600;
}

/* ===== Cards / Frames ===== */
QFrame#card {
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
}
QFrame#card:hover {
    background: #1a2233;
    border: 1px solid #2d3f55;
}
QFrame#cardHeader {
    background: #0d1220;
    border-bottom: 1px solid #1e2a3a;
    border-radius: 8px 8px 0 0;
}
"""


SIDEBAR_STYLE = """
/* ===== Sidebar ===== */
QWidget#sidebar {
    background: #070b12;
    border-right: 1px solid #1a2030;
}

QPushButton#sidebarBtn {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0 0 0 16px;
    color: #475569;
    text-align: left;
    font-size: 12px;
    font-weight: 500;
}
QPushButton#sidebarBtn:hover {
    background: #0d1220;
    color: #94a3b8;
}
QPushButton#sidebarBtn:checked {
    background: #131f35;
    color: #e2e8f0;
    border-left: 2px solid #3b82f6;
}

QLabel#sidebarSection {
    color: #2d3f55;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 12px 16px 4px;
    text-transform: uppercase;
}

QLabel#logoLabel {
    color: #06b6d4;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.5px;
    padding: 16px 16px 2px;
}
QLabel#logoSubLabel {
    color: #1e2a3a;
    font-size: 8px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 0 16px 16px;
}
"""


GRAPH_STYLE = """
/* ===== Graph View ===== */
QGraphicsView {
    background: #070b12;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
}
"""


STATUS_CARD_STYLE = """
/* ===== Status Card ===== */
QFrame#statusCard {
    background: #111827;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
}
"""
