"""
Modern Windows 11 Fluent-inspired Dark & Light QSS Themes for DocuTools.
"""

DARK_THEME_QSS = """
/* Global Window & Fonts */
QWidget {
    background-color: #1a1b1e;
    color: #e1e3e6;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #121316;
}

/* Tooltips */
QToolTip {
    background-color: #2a2c33;
    color: #f3f4f6;
    border: 1px solid #3f424e;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* Sidebar Styling */
#sidebarWidget {
    background-color: #151619;
    border-right: 1px solid #282a30;
}

#sidebarHeader {
    padding: 16px 12px;
    border-bottom: 1px solid #24262c;
}

#sidebarTitle {
    font-size: 16px;
    font-weight: bold;
    color: #60a5fa;
    letter-spacing: 0.5px;
}

#sidebarSubtitle {
    font-size: 11px;
    color: #9ca3af;
}

/* Sidebar Navigation Buttons */
QPushButton.navButton {
    background-color: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.navButton:hover {
    background-color: #22242a;
    color: #ffffff;
}

QPushButton.navButton:checked, QPushButton.navButton[active="true"] {
    background-color: #1e3a8a;
    color: #93c5fd;
    font-weight: 600;
}

/* Cards & Content Panels */
QFrame.cardFrame {
    background-color: #202227;
    border: 1px solid #2c2f37;
    border-radius: 10px;
    padding: 14px;
}

QFrame.cardFrame:hover {
    border: 1px solid #3b404d;
}

/* Standard Buttons */
QPushButton {
    background-color: #2a2c33;
    color: #e5e7eb;
    border: 1px solid #3a3d47;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #343740;
    border-color: #4b505e;
}

QPushButton:pressed {
    background-color: #22242a;
}

QPushButton:disabled {
    background-color: #1c1d22;
    color: #555866;
    border-color: #26282f;
}

/* Primary Action Buttons */
QPushButton.primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: 600;
}

QPushButton.primaryButton:hover {
    background-color: #3b82f6;
    border-color: #2563eb;
}

QPushButton.primaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton.successButton {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #15803d;
    font-weight: 600;
}

QPushButton.successButton:hover {
    background-color: #22c55e;
}

/* Danger / Delete Buttons */
QPushButton.dangerButton {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #b91c1c;
}

QPushButton.dangerButton:hover {
    background-color: #ef4444;
}

/* Input Fields & Combos */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #24262c;
    color: #f3f4f6;
    border: 1px solid #363943;
    border-radius: 6px;
    padding: 7px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
    background-color: #272a32;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #363943;
}

QComboBox QAbstractItemView {
    background-color: #24262c;
    color: #f3f4f6;
    border: 1px solid #3b404d;
    selection-background-color: #2563eb;
    padding: 4px;
}

/* Text Editors */
QTextEdit, QPlainTextEdit {
    background-color: #1f2025;
    color: #f3f4f6;
    border: 1px solid #32353e;
    border-radius: 8px;
    padding: 12px;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #18191d;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #373a44;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #4b505e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #18191d;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #373a44;
    min-width: 24px;
    border-radius: 5px;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #2c2f37;
    background-color: #1f2025;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #17181c;
    color: #9ca3af;
    border: 1px solid #282a31;
    border-bottom: none;
    padding: 9px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #1f2025;
    color: #60a5fa;
    border: 1px solid #2c2f37;
    border-bottom: 2px solid #3b82f6;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #23252c;
    color: #e5e7eb;
}

/* Tables & Lists */
QTableWidget, QListView, QTreeView {
    background-color: #1e1f24;
    border: 1px solid #2c2f37;
    border-radius: 6px;
    gridline-color: #2a2c34;
    color: #e1e3e6;
}

QTableWidget::item, QListView::item {
    padding: 6px;
}

QTableWidget::item:selected, QListView::item:selected {
    background-color: #1e3a8a;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #17181c;
    color: #9ca3af;
    padding: 8px;
    border: none;
    border-right: 1px solid #282a30;
    border-bottom: 1px solid #282a30;
    font-weight: 600;
    font-size: 12px;
}

/* Progress Bars */
QProgressBar {
    background-color: #16171b;
    border: 1px solid #2d3039;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

/* Status Bar */
QStatusBar {
    background-color: #141518;
    color: #9ca3af;
    border-top: 1px solid #24262c;
    font-size: 12px;
}

/* Labels */
QLabel.heading {
    font-size: 18px;
    font-weight: 700;
    color: #f3f4f6;
}

QLabel.subheading {
    font-size: 13px;
    color: #9ca3af;
}

QLabel.badge {
    background-color: #2563eb;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #363943;
    height: 6px;
    background: #24262c;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #60a5fa;
    border: 2px solid #ffffff;
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}
"""

LIGHT_THEME_QSS = """
/* Global Window & Fonts */
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #f1f5f9;
}

QToolTip {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

#sidebarWidget {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}

#sidebarHeader {
    padding: 16px 12px;
    border-bottom: 1px solid #e2e8f0;
}

#sidebarTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1d4ed8;
    letter-spacing: 0.5px;
}

#sidebarSubtitle {
    font-size: 11px;
    color: #64748b;
}

QPushButton.navButton {
    background-color: transparent;
    color: #475569;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.navButton:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QPushButton.navButton:checked, QPushButton.navButton[active="true"] {
    background-color: #eff6ff;
    color: #1d4ed8;
    font-weight: 600;
}

QFrame.cardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px;
}

QFrame.cardFrame:hover {
    border: 1px solid #cbd5e1;
}

QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #f1f5f9;
}

QPushButton:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

QPushButton.primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: 600;
}

QPushButton.primaryButton:hover {
    background-color: #1d4ed8;
}

QPushButton.successButton {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #15803d;
    font-weight: 600;
}

QPushButton.successButton:hover {
    background-color: #15803d;
}

QPushButton.dangerButton {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #dc2626;
}

QPushButton.dangerButton:hover {
    background-color: #dc2626;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2563eb;
    background-color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #cbd5e1;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
    padding: 4px;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px;
}

QScrollBar:vertical {
    background: #f1f5f9;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #f1f5f9;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 24px;
    border-radius: 5px;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    padding: 9px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1d4ed8;
    border: 1px solid #e2e8f0;
    border-bottom: 2px solid #2563eb;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #e2e8f0;
    color: #0f172a;
}

QTableWidget, QListView, QTreeView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    color: #1e293b;
}

QTableWidget::item:selected, QListView::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 8px;
    border: none;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 600;
    font-size: 12px;
}

QProgressBar {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    text-align: center;
    color: #0f172a;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

QStatusBar {
    background-color: #ffffff;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    font-size: 12px;
}

QLabel.heading {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
}

QLabel.subheading {
    font-size: 13px;
    color: #64748b;
}

QLabel.badge {
    background-color: #2563eb;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
}

QSlider::groove:horizontal {
    border: 1px solid #cbd5e1;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #2563eb;
    border: 2px solid #ffffff;
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    """Return the QSS stylesheet for the given theme ('dark' or 'light')."""
    return DARK_THEME_QSS if theme.lower() == "dark" else LIGHT_THEME_QSS
