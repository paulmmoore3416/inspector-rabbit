"""
Inspector Rabbit - Global Stylesheet  v1.5.0
Space Gray theme — Apple-inspired warm dark gray palette.
"""

# ── Space Gray Palette ─────────────────────────────────────────────────────────
# BG_PRIMARY  = #1c1c1e   Main app background
# BG_SURFACE  = #2c2c2e   Cards, panels
# BG_ELEVATED = #3a3a3c   Hover / elevated surfaces
# BG_SIDEBAR  = #161618   Sidebar / nav
# BORDER      = #38383a   Default border
# BORDER_STR  = #48484a   Stronger border
# TEXT_1      = #f5f5f7   Primary text
# TEXT_2      = #aeaeb2   Secondary text
# TEXT_3      = #636366   Tertiary / muted
# ACCENT      = #0a84ff   Apple blue
# SUCCESS     = #30d158   Green
# DANGER      = #ff453a   Red
# WARNING     = #ff9f0a   Orange
# PURPLE      = #bf5af2
# TEAL        = #5ac8fa
# YELLOW      = #ffd60a
# PINK        = #ff375f
# ──────────────────────────────────────────────────────────────────────────────

MAIN_STYLE = """
/* ===== Global ===== */
QWidget {
    background-color: #1c1c1e;
    color: #aeaeb2;
    font-family: 'SF Pro Display', 'Ubuntu', 'Segoe UI', 'Noto Sans', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1c1c1e;
}

QDialog {
    background: #1c1c1e;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #3a3a3c;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #0a84ff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #3a3a3c;
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #0a84ff;
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
    background-color: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f5f5f7;
    selection-background-color: #0a84ff44;
    selection-color: #f5f5f7;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0a84ff;
    background-color: #2c2c2e;
}
QLineEdit:hover {
    border: 1px solid #48484a;
}

/* ===== Buttons ===== */
QPushButton {
    background: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 8px;
    padding: 8px 16px;
    color: #f5f5f7;
    font-weight: 500;
}
QPushButton:hover {
    background: #3a3a3c;
    border: 1px solid #48484a;
}
QPushButton:pressed {
    background: #1c1c1e;
    border: 1px solid #0a84ff;
}
QPushButton:disabled {
    color: #48484a;
    border: 1px solid #2c2c2e;
    background: #1c1c1e;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0071e3, stop:1 #0a84ff);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0064cc, stop:1 #0071e3);
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0058b3, stop:1 #0064cc);
}

QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #d93025, stop:1 #ff453a);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
}
QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c02820, stop:1 #d93025);
}

QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #25a244, stop:1 #30d158);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1e8c3a, stop:1 #25a244);
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f5f5f7;
    min-width: 100px;
}
QComboBox:hover {
    border: 1px solid #48484a;
}
QComboBox:focus {
    border: 1px solid #0a84ff;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #636366;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #2c2c2e;
    border: 1px solid #38383a;
    selection-background-color: #0a84ff33;
    color: #f5f5f7;
    border-radius: 8px;
    padding: 4px;
}

/* ===== SpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 8px;
    padding: 7px 10px;
    color: #f5f5f7;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0a84ff;
}

/* ===== CheckBox ===== */
QCheckBox {
    color: #aeaeb2;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid #48484a;
    background: #2c2c2e;
}
QCheckBox::indicator:checked {
    background: #0a84ff;
    border: none;
}
QCheckBox::indicator:hover {
    border: 1px solid #0a84ff;
}

/* ===== Radio Button ===== */
QRadioButton {
    color: #aeaeb2;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #48484a;
    background: #2c2c2e;
}
QRadioButton::indicator:checked {
    background: #0a84ff;
    border: 2px solid #1c1c1e;
    outline: 1px solid #0a84ff;
}

/* ===== Tables ===== */
QTableWidget, QTableView {
    background-color: #1c1c1e;
    alternate-background-color: #242426;
    gridline-color: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 8px;
    selection-background-color: #0a84ff22;
    selection-color: #f5f5f7;
}
QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #0a84ff22;
    color: #f5f5f7;
}
QHeaderView::section {
    background-color: #242426;
    color: #636366;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #2c2c2e;
    border-bottom: 1px solid #38383a;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}
QHeaderView::section:hover {
    background-color: #2c2c2e;
    color: #aeaeb2;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #242426;
    border: 1px solid #38383a;
    border-radius: 5px;
    text-align: center;
    color: #aeaeb2;
    height: 12px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0071e3, stop:1 #0a84ff);
    border-radius: 4px;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: none;
    border-top: 1px solid #38383a;
    background: #1c1c1e;
}
QTabBar {
    background: #1c1c1e;
}
QTabBar::tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 18px;
    margin-right: 2px;
    color: #636366;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #f5f5f7;
    border-bottom: 2px solid #0a84ff;
}
QTabBar::tab:hover:!selected {
    color: #aeaeb2;
    border-bottom: 2px solid #3a3a3c;
}

/* ===== Group Box ===== */
QGroupBox {
    border: 1px solid #38383a;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 10px;
    color: #636366;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: #1c1c1e;
    color: #636366;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background: #2c2c2e;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background: #161618;
    border-bottom: 1px solid #2c2c2e;
    color: #636366;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 5px;
}
QMenuBar::item:selected {
    background: #2c2c2e;
    color: #aeaeb2;
}

/* ===== Menu ===== */
QMenu {
    background: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 6px;
    color: #aeaeb2;
}
QMenu::item:selected {
    background: #0a84ff22;
    color: #f5f5f7;
}
QMenu::separator {
    height: 1px;
    background: #38383a;
    margin: 4px 8px;
}

/* ===== Status Bar ===== */
QStatusBar {
    background: #161618;
    border-top: 1px solid #2c2c2e;
    color: #48484a;
    font-size: 11px;
    padding: 2px 8px;
}

/* ===== Tooltip ===== */
QToolTip {
    background: #2c2c2e;
    border: 1px solid #48484a;
    color: #f5f5f7;
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 12px;
}

/* ===== Tree Widget ===== */
QTreeWidget {
    background: #1c1c1e;
    border: 1px solid #38383a;
    border-radius: 8px;
    color: #aeaeb2;
}
QTreeWidget::item {
    padding: 4px 0;
}
QTreeWidget::item:selected {
    background: #0a84ff22;
    color: #f5f5f7;
}
QTreeWidget::item:hover {
    background: #2c2c2e;
}
QTreeWidget::branch {
    background: transparent;
}

/* ===== List Widget ===== */
QListWidget {
    background: #1c1c1e;
    border: 1px solid #38383a;
    border-radius: 8px;
    color: #aeaeb2;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 5px;
}
QListWidget::item:selected {
    background: #0a84ff22;
    color: #f5f5f7;
}
QListWidget::item:hover {
    background: #2c2c2e;
}

/* ===== Slider ===== */
QSlider::groove:horizontal {
    height: 4px;
    background: #3a3a3c;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #0a84ff;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: #0a84ff;
    border-radius: 2px;
}

/* ===== Labels ===== */
QLabel {
    color: #aeaeb2;
}
QLabel#titleLabel {
    font-size: 20px;
    font-weight: 700;
    color: #f5f5f7;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #636366;
}
QLabel#sectionLabel {
    font-size: 10px;
    font-weight: 700;
    color: #48484a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QLabel#accentLabel {
    color: #0a84ff;
    font-weight: 600;
}
QLabel#successLabel {
    color: #30d158;
    font-weight: 600;
}
QLabel#errorLabel {
    color: #ff453a;
    font-weight: 600;
}
QLabel#warningLabel {
    color: #ff9f0a;
    font-weight: 600;
}

/* ===== Cards / Frames ===== */
QFrame#card {
    background: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 10px;
}
QFrame#card:hover {
    background: #3a3a3c;
    border: 1px solid #48484a;
}
QFrame#cardHeader {
    background: #242426;
    border-bottom: 1px solid #38383a;
    border-radius: 10px 10px 0 0;
}
"""


SIDEBAR_STYLE = """
/* ===== Sidebar ===== */
QWidget#sidebar {
    background: #161618;
    border-right: 1px solid #2c2c2e;
}

QPushButton#sidebarBtn {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0 0 0 16px;
    color: #48484a;
    text-align: left;
    font-size: 12px;
    font-weight: 500;
}
QPushButton#sidebarBtn:hover {
    background: #1c1c1e;
    color: #aeaeb2;
}
QPushButton#sidebarBtn:checked {
    background: #0a84ff18;
    color: #f5f5f7;
    border-left: 2px solid #0a84ff;
}

QLabel#sidebarSection {
    color: #3a3a3c;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 12px 16px 4px;
    text-transform: uppercase;
}

QLabel#logoLabel {
    color: #5ac8fa;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.5px;
    padding: 16px 16px 2px;
}
QLabel#logoSubLabel {
    color: #2c2c2e;
    font-size: 8px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 0 16px 16px;
}
"""


GRAPH_STYLE = """
/* ===== Graph View ===== */
QGraphicsView {
    background: #161618;
    border: 1px solid #38383a;
    border-radius: 8px;
}
"""


STATUS_CARD_STYLE = """
/* ===== Status Card ===== */
QFrame#statusCard {
    background: #2c2c2e;
    border: 1px solid #38383a;
    border-radius: 10px;
}
"""
