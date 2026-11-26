"""Windows 11 Fluent Design theme engine and stylesheets for DocuTools."""

from __future__ import annotations

from typing import Literal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

ThemeMode = Literal["dark", "light"]

DARK_PALETTE = {
    "bg_main": "#1e1e22",
    "bg_sidebar": "#161619",
    "bg_header": "#222226",
    "bg_card": "#28282e",
    "bg_card_hover": "#32323a",
    "bg_input": "#242429",
    "border": "#363640",
    "border_light": "#4a4a58",
    "border_focus": "#60cdff",
    "accent": "#0078d4",
    "accent_fluent": "#60cdff",
    "accent_hover": "#1e88e5",
    "accent_pressed": "#005a9e",
    "accent_subtle": "rgba(96, 205, 255, 0.12)",
    "text_primary": "#ffffff",
    "text_secondary": "#d1d5db",
    "text_muted": "#9ca3af",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
}

LIGHT_PALETTE = {
    "bg_main": "#f8f9fc",
    "bg_sidebar": "#f0f2f7",
    "bg_header": "#ffffff",
    "bg_card": "#ffffff",
    "bg_card_hover": "#f3f5f9",
    "bg_input": "#ffffff",
    "border": "#e2e8f0",
    "border_light": "#cbd5e1",
    "border_focus": "#0078d4",
    "accent": "#0078d4",
    "accent_fluent": "#0078d4",
    "accent_hover": "#1e88e5",
    "accent_pressed": "#005a9e",
    "accent_subtle": "rgba(0, 120, 212, 0.10)",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#94a3b8",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
}


def generate_qss(mode: ThemeMode = "dark") -> str:
    """Generate comprehensive Windows 11-inspired QSS stylesheet with rounded corners."""
    c = DARK_PALETTE if mode == "dark" else LIGHT_PALETTE

    return f"""
    /* Global Application Reset - Windows 11 Segoe UI Variable */
    * {{
        font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
        font-size: 13px;
        color: {c["text_primary"]};
        outline: none;
    }}

    QMainWindow, QDialog, QScrollArea, #centralWorkArea {{
        background-color: {c["bg_main"]};
    }}

    QWidget {{
        background-color: transparent;
    }}

    /* Drop Zone (Theme-Adaptive) */
    #FileDropArea {{
        border: 2px dashed {c["border_light"]};
        border-radius: 14px;
        background-color: {c["bg_card"]};
    }}

    #FileDropArea:hover {{
        border: 2px dashed {c["accent"]};
        background-color: {c["accent_subtle"]};
    }}

    #FileDropArea QLabel {{
        border: none;
        background: transparent;
    }}

    /* Sidebar Navigation Container */
    #sidebarContainer {{
        background-color: {c["bg_sidebar"]};
        border-right: 1px solid {c["border"]};
    }}

    /* Header Bar */
    #headerContainer {{
        background-color: {c["bg_header"]};
        border-bottom: 1px solid {c["border"]};
    }}

    /* Windows 11 Rounded Elevation Cards */
    QFrame[card="true"] {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
    }}

    QFrame[card="true"]:hover {{
        border: 1px solid {c["border_light"]};
        background-color: {c["bg_card_hover"]};
    }}

    /* Windows 11 Pill Search Bar */
    QLineEdit#searchBar {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 17px;
        padding: 6px 14px;
        font-size: 12px;
    }}

    QLineEdit#searchBar:focus {{
        border: 1px solid {c["border_focus"]};
        background-color: {c["bg_card"]};
    }}

    /* Modern Rounded Buttons */
    QPushButton {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 7px 18px;
        font-weight: 500;
        min-height: 18px;
    }}

    QPushButton:hover {{
        background-color: {c["bg_card_hover"]};
        border: 1px solid {c["border_light"]};
    }}

    QPushButton:pressed {{
        background-color: {c["border"]};
    }}

    QPushButton:disabled {{
        background-color: {c["bg_sidebar"]};
        color: {c["text_muted"]};
        border: 1px solid {c["border"]};
    }}

    /* Accent Button Variant (Fluent Blue) */
    QPushButton[variant="accent"] {{
        background-color: {c["accent"]};
        color: #ffffff;
        border: 1px solid {c["accent"]};
        border-radius: 8px;
        font-weight: 600;
    }}

    QPushButton[variant="accent"]:hover {{
        background-color: {c["accent_hover"]};
        border: 1px solid {c["accent_hover"]};
    }}

    QPushButton[variant="accent"]:pressed {{
        background-color: {c["accent_pressed"]};
        border: 1px solid {c["accent_pressed"]};
    }}

    /* Subdued / Flat Buttons */
    QPushButton[variant="flat"] {{
        background-color: transparent;
        border: none;
        border-radius: 7px;
        color: {c["text_secondary"]};
        padding: 6px 14px;
    }}

    QPushButton[variant="flat"]:hover {{
        background-color: {c["bg_card_hover"]};
        color: {c["text_primary"]};
    }}

    /* Windows 11 Sidebar Navigation Pill Buttons */
    QPushButton[nav="true"] {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
        color: {c["text_secondary"]};
        margin: 1px 4px;
    }}

    QPushButton[nav="true"]:hover {{
        background-color: {c["bg_card_hover"]};
        color: {c["text_primary"]};
    }}

    QPushButton[nav="true"]:checked, QPushButton[nav="true"][active="true"] {{
        background-color: {c["accent_subtle"]};
        color: {c["accent_fluent"]};
        font-weight: 600;
        border-left: 3.5px solid {c["accent_fluent"]};
    }}

    /* Input Fields with Windows 11 Focus Ring */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 7px 12px;
        selection-background-color: {c["accent"]};
        selection-color: #ffffff;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c["border_focus"]};
    }}

    /* Drop-down combo */
    QComboBox::drop-down {{
        border: none;
        padding-right: 10px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        selection-background-color: {c["accent_subtle"]};
        selection-color: {c["text_primary"]};
        padding: 6px;
    }}

    /* Sleek Windows 11 Rounded Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px 0px 2px 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {c["border"]};
        border-radius: 4px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["border_light"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0px 2px 0px 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {c["border"]};
        border-radius: 4px;
        min-width: 28px;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Rounded Tables & Lists */
    QTableWidget, QTableView, QListWidget {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        gridline-color: {c["border"]};
        selection-background-color: {c["accent_subtle"]};
        selection-color: {c["text_primary"]};
    }}

    QHeaderView::section {{
        background-color: {c["bg_sidebar"]};
        color: {c["text_secondary"]};
        padding: 6px 12px;
        min-height: 26px;
        border: none;
        border-bottom: 1px solid {c["border"]};
        font-weight: 600;
        font-size: 12px;
    }}

    /* Rounded Progress Capsule */
    QProgressBar {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        text-align: center;
        height: 12px;
        font-size: 10px;
        color: {c["text_secondary"]};
    }}

    QProgressBar::chunk {{
        background-color: {c["accent_fluent"]};
        border-radius: 5px;
    }}

    /* Tab Widget - Rounded Pill Tabs */
    QTabWidget::pane {{
        border: 1px solid {c["border"]};
        border-radius: 12px;
        background-color: {c["bg_card"]};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {c["bg_sidebar"]};
        color: {c["text_secondary"]};
        padding: 8px 18px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 3px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        font-weight: 600;
        border: 1px solid {c["border"]};
        border-bottom: 2px solid {c["accent_fluent"]};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {c["bg_card_hover"]};
    }}

    /* Tooltips with Windows 11 Shadows */
    QToolTip {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_light"]};
        border-radius: 7px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* Checkbox & Radio Buttons */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {c["text_primary"]};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {c["border_light"]};
        background: {c["bg_input"]};
    }}

    QRadioButton::indicator {{
        border-radius: 9px;
    }}

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border: 1px solid {c["border_focus"]};
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {c["accent"]};
        border: 1px solid {c["accent"]};
    }}
    """


def apply_theme(app: QApplication, mode: ThemeMode = "dark") -> None:
    """Apply the styled QSS stylesheet and Qt palette to the application."""
    c = DARK_PALETTE if mode == "dark" else LIGHT_PALETTE
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(c["bg_main"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(c["bg_input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c["bg_card"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(c["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(c["bg_card"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(c["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    qss = generate_qss(mode)
    app.setStyleSheet(qss)
