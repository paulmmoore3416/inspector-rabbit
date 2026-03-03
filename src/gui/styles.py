"""
Inspector Rabbit - Global Stylesheet  v1.3.0
Dark cyberpunk theme — enhanced with richer inputs, underline tabs,
glassmorphism-inspired cards, and tighter visual hierarchy.
"""

MAIN_STYLE = """
/* ===== Global ===== */
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Ubuntu', 'Segoe UI', 'Noto Sans', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0d1117;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2d333b;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #00f5ff66;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #2d333b;
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #00f5ff66;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ===== Input Fields ===== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e6edf3;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00f5ff88;
    background-color: #0f161f;
}
QLineEdit:hover {
    border: 1px solid #444c56;
}

/* ===== Buttons ===== */
QPushButton {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 18px;
    color: #c9d1d9;
    font-weight: 500;
}
QPushButton:hover {
    background: #1f2937;
    border: 1px solid #00f5ff44;
    color: #e6edf3;
}
QPushButton:pressed {
    background: #0d1117;
    border: 1px solid #00f5ff;
}
QPushButton:disabled {
    color: #3a4149;
    border: 1px solid #21262d;
    background: #0d1117;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0066e0, stop:1 #00bbf0);
    border: none;
    color: white;
    font-weight: 700;
    font-size: 13px;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #007af5, stop:1 #00ccff);
    color: white;
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0055c8, stop:1 #009ed4);
}

QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #b91c1c, stop:1 #ef4444);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
}
QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #dc2626, stop:1 #f87171);
}

QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #16a34a, stop:1 #22c55e);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 12px;
    color: #e6edf3;
    min-width: 100px;
}
QComboBox:hover {
    border: 1px solid #444c56;
}
QComboBox:focus {
    border: 1px solid #00f5ff66;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    color: #e6edf3;
    border-radius: 6px;
    padding: 4px;
}

/* ===== SpinBox / DoubleSpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 10px;
    color: #e6edf3;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00f5ff66;
}

/* ===== CheckBox ===== */
QCheckBox {
    color: #c9d1d9;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #30363d;
    background: #0d1117;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0066e0, stop:1 #00f5ff);
    border: none;
}
QCheckBox::indicator:hover {
    border: 1px solid #00f5ff66;
}

/* ===== Radio Button ===== */
QRadioButton {
    color: #c9d1d9;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #30363d;
    background: #0d1117;
}
QRadioButton::indicator:checked {
    background: #00f5ff;
    border: 2px solid #0d1117;
    outline: 1px solid #00f5ff;
}

/* ===== Tables ===== */
QTableWidget, QTableView {
    background-color: #0d1117;
    alternate-background-color: #0a0f16;
    gridline-color: #1a2030;
    border: 1px solid #21262d;
    border-radius: 8px;
    selection-background-color: #1a3050;
    selection-color: #e6edf3;
}
QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #1a3050;
    color: #e6edf3;
}
QHeaderView::section {
    background-color: #0a0f16;
    color: #484f58;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #1a2030;
    border-bottom: 1px solid #21262d;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QHeaderView::section:hover {
    background-color: #161b22;
    color: #8b949e;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #0a0f16;
    border: 1px solid #21262d;
    border-radius: 6px;
    text-align: center;
    color: #c9d1d9;
    height: 14px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0066e0, stop:0.5 #00a0e8, stop:1 #00f5ff);
    border-radius: 5px;
}

/* ===== Tabs — underline style ===== */
QTabWidget::pane {
    border: none;
    border-top: 1px solid #21262d;
    background: #0d1117;
}
QTabBar::tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 20px;
    margin-right: 2px;
    color: #8b949e;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #00f5ff;
    border-bottom: 2px solid #00f5ff;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #c9d1d9;
    border-bottom: 2px solid #30363d;
}
QTabBar {
    background: #0a0f16;
    border-bottom: 1px solid #21262d;
}

/* ===== Group Box ===== */
QGroupBox {
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 10px;
    font-weight: 600;
    color: #484f58;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: #0d1117;
    color: #484f58;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
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
    background: #010409;
    border-bottom: 1px solid #1a2030;
    color: #8b949e;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #161b22;
    color: #00f5ff;
}
QMenu {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #1f6feb22;
    color: #00f5ff;
}
QMenu::separator {
    height: 1px;
    background: #21262d;
    margin: 4px 8px;
}

/* ===== Status Bar ===== */
QStatusBar {
    background: #010409;
    border-top: 1px solid #1a2030;
    color: #484f58;
    font-size: 11px;
    padding: 2px 8px;
}

/* ===== Tooltip ===== */
QToolTip {
    background: #161b22;
    border: 1px solid #30363d;
    color: #c9d1d9;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ===== Tree Widget ===== */
QTreeWidget {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    color: #c9d1d9;
}
QTreeWidget::item {
    padding: 4px 0;
}
QTreeWidget::item:selected {
    background: #1a3050;
    color: #e6edf3;
}
QTreeWidget::item:hover {
    background: #0f161f;
}
QTreeWidget::branch {
    background: transparent;
}

/* ===== List Widget ===== */
QListWidget {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    color: #c9d1d9;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #1a3050;
    color: #e6edf3;
}
QListWidget::item:hover {
    background: #0f161f;
}

/* ===== Slider ===== */
QSlider::groove:horizontal {
    height: 4px;
    background: #21262d;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00f5ff;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0066e0, stop:1 #00f5ff);
    border-radius: 2px;
}

/* ===== Dialogs ===== */
QDialog {
    background: #0d1117;
}

/* ===== Labels ===== */
QLabel {
    color: #c9d1d9;
}
QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #e6edf3;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #8b949e;
}
QLabel#sectionLabel {
    font-size: 10px;
    font-weight: 700;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QLabel#accentLabel {
    color: #00f5ff;
    font-weight: 600;
}
QLabel#successLabel {
    color: #3fb950;
    font-weight: 600;
}
QLabel#errorLabel {
    color: #f85149;
    font-weight: 600;
}
QLabel#warningLabel {
    color: #e3b341;
    font-weight: 600;
}

/* ===== Frame / Cards ===== */
QFrame#card {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
}
QFrame#card:hover {
    background: #161b22;
    border: 1px solid #30363d;
}
QFrame#cardHeader {
    background: #0a0f16;
    border-bottom: 1px solid #21262d;
    border-radius: 10px 10px 0 0;
}
"""


SIDEBAR_STYLE = """
QWidget#sidebar {
    background: #010409;
    border-right: 1px solid #1a2030;
}

QPushButton#sidebarBtn {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 12px 8px;
    color: #484f58;
    text-align: center;
    font-size: 10px;
    margin: 2px 8px;
    qproperty-iconSize: 24px 24px;
}
QPushButton#sidebarBtn:hover {
    background: #0d1117;
    color: #8b949e;
}
QPushButton#sidebarBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00f5ff1a, stop:1 transparent);
    color: #00f5ff;
    border-left: 2px solid #00f5ff;
}

QLabel#logoLabel {
    color: #00f5ff;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: -1px;
    padding: 16px 8px 4px;
    text-align: center;
}
QLabel#logoSubLabel {
    color: #1a2030;
    font-size: 8px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 0 8px 16px;
    text-align: center;
}
"""


GRAPH_STYLE = """
QGraphicsView {
    background: #030810;
    border: 1px solid #21262d;
    border-radius: 8px;
}
"""


STATUS_CARD_STYLE = """
QFrame#statusCard {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
}
"""
