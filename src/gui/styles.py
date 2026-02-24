"""
Inspector Rabbit - Global Stylesheet
Modern dark cyberpunk theme with cyan/magenta accents
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
    background: #161b22;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #00f5ff55;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #161b22;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #00f5ff55;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ===== Input Fields ===== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e6edf3;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00f5ff;
    background-color: #1a1f2e;
}
QLineEdit:hover, QTextEdit:hover {
    border: 1px solid #444c56;
}

/* ===== Buttons ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #21262d, stop:1 #161b22);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 18px;
    color: #c9d1d9;
    font-weight: 500;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2d333b, stop:1 #21262d);
    border: 1px solid #00f5ff66;
    color: #00f5ff;
}
QPushButton:pressed {
    background: #0d1117;
    border: 1px solid #00f5ff;
}
QPushButton:disabled {
    color: #484f58;
    border: 1px solid #21262d;
    background: #161b22;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0070f3, stop:1 #00c2ff);
    border: none;
    color: white;
    font-weight: 700;
    font-size: 13px;
    padding: 10px 24px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0080ff, stop:1 #00d4ff);
    color: white;
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0060d0, stop:1 #00a8dd);
}

QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #b91c1c, stop:1 #ef4444);
    border: none;
    color: white;
    font-weight: 600;
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
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #161b22;
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
    border: 1px solid #00f5ff;
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
    background: #1f2937;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    color: #e6edf3;
    border-radius: 6px;
    padding: 4px;
}

/* ===== SpinBox / DoubleSpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 10px;
    color: #e6edf3;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00f5ff;
}

/* ===== CheckBox ===== */
QCheckBox {
    color: #c9d1d9;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background: #161b22;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0070f3, stop:1 #00f5ff);
    border: none;
    image: none;
}
QCheckBox::indicator:hover {
    border: 1px solid #00f5ff;
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
    background: #161b22;
}
QRadioButton::indicator:checked {
    background: #00f5ff;
    border: 2px solid #0d1117;
    outline: 1px solid #00f5ff;
}

/* ===== Tables ===== */
QTableWidget, QTableView {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    gridline-color: #21262d;
    border: 1px solid #21262d;
    border-radius: 8px;
    selection-background-color: #1f3a5f;
    selection-color: #e6edf3;
}
QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #1f3a5f;
    color: #e6edf3;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #21262d;
    border-bottom: 1px solid #21262d;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QHeaderView::section:hover {
    background-color: #1f2937;
    color: #c9d1d9;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    text-align: center;
    color: #c9d1d9;
    height: 14px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0070f3, stop:0.5 #00c2ff, stop:1 #00f5ff);
    border-radius: 5px;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
}
QTabBar::tab {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
    margin-right: 2px;
    color: #8b949e;
}
QTabBar::tab:selected {
    background: #0d1117;
    color: #00f5ff;
    border-bottom: 2px solid #00f5ff;
}
QTabBar::tab:hover:!selected {
    background: #1f2937;
    color: #c9d1d9;
}

/* ===== Group Box ===== */
QGroupBox {
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 10px;
    font-weight: 600;
    color: #8b949e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: #0d1117;
    color: #8b949e;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background: #21262d;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background: #161b22;
    border-bottom: 1px solid #21262d;
    color: #c9d1d9;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #21262d;
    color: #00f5ff;
}
QMenu {
    background: #1f2937;
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
    background: #161b22;
    border-top: 1px solid #21262d;
    color: #8b949e;
    font-size: 12px;
    padding: 2px 8px;
}

/* ===== Tooltip ===== */
QToolTip {
    background: #1f2937;
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
    background: #1f3a5f;
    color: #e6edf3;
}
QTreeWidget::item:hover {
    background: #161b22;
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
    background: #1f3a5f;
    color: #e6edf3;
}
QListWidget::item:hover {
    background: #161b22;
}

/* ===== Slider ===== */
QSlider::groove:horizontal {
    height: 4px;
    background: #21262d;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00f5ff;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0070f3, stop:1 #00f5ff);
    border-radius: 2px;
}

/* ===== Dialogs ===== */
QDialog {
    background: #0d1117;
}

/* ===== Label ===== */
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
    font-size: 11px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
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
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
}
QFrame#cardHeader {
    background: #21262d;
    border-bottom: 1px solid #21262d;
    border-radius: 12px 12px 0 0;
}
"""


SIDEBAR_STYLE = """
QWidget#sidebar {
    background: #010409;
    border-right: 1px solid #21262d;
}

QPushButton#sidebarBtn {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 12px 8px;
    color: #8b949e;
    text-align: center;
    font-size: 11px;
    margin: 2px 8px;
    qproperty-iconSize: 24px 24px;
}
QPushButton#sidebarBtn:hover {
    background: #161b22;
    color: #c9d1d9;
}
QPushButton#sidebarBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00f5ff22, stop:1 transparent);
    color: #00f5ff;
    border-left: 3px solid #00f5ff;
}

QLabel#logoLabel {
    color: #00f5ff;
    font-size: 24px;
    font-weight: 900;
    letter-spacing: -1px;
    padding: 16px 8px 4px;
    text-align: center;
}
QLabel#logoSubLabel {
    color: #30363d;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 0 8px 16px;
    text-align: center;
}
"""


GRAPH_STYLE = """
QGraphicsView {
    background: #060c14;
    border: 1px solid #21262d;
    border-radius: 8px;
}
"""


STATUS_CARD_STYLE = """
QFrame#statusCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #161b22, stop:1 #0d1117);
    border: 1px solid #21262d;
    border-radius: 12px;
}
"""
