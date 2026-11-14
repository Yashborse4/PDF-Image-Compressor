"""
Settings View for DocuTools.
Manages theme preferences, default output folders, and keyboard shortcut references.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.assets import get_app_icon_path
from docutools.core.database import Database


class SettingsView(QWidget):
    """Application preferences and keyboard shortcuts view."""

    KEYBOARD_SHORTCUTS = [
        ("Ctrl + 1", "Home Dashboard"),
        ("Ctrl + 2", "PDF Tools"),
        ("Ctrl + 3", "Document Editor"),
        ("Ctrl + 4", "Image Tools"),
        ("Ctrl + 5", "Converter"),
        ("Ctrl + 6", "Batch Processing"),
        ("Ctrl + 7", "Activity History"),
        ("Ctrl + 8", "Settings"),
        ("Ctrl + O", "Open File in current active module"),
        ("Ctrl + S", "Save Document / Output file"),
        ("Ctrl + N", "Create New Document (in Document Editor)"),
        ("Ctrl + T", "Toggle Theme (Dark ↔ Light)"),
        ("Ctrl + B", "Toggle Bold (Document Editor)"),
        ("Ctrl + I", "Toggle Italic (Document Editor)"),
        ("Ctrl + U", "Toggle Underline (Document Editor)"),
        ("Ctrl + W", "Collapse / Expand Sidebar"),
    ]

    def __init__(
        self,
        db: Database,
        theme_change_callback: Callable[[str], None],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.db = db
        self.theme_change_callback = theme_change_callback

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Title
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Settings & Preferences")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Customize theme appearance, default output directories, and view keyboard shortcuts.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        main_layout.addLayout(title_box)

        # Scroll Area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setSpacing(14)

        # 1. Appearance Card
        card_app = QFrame()
        card_app.setProperty("class", "cardFrame")
        c1_lay = QVBoxLayout(card_app)
        c1_lay.setSpacing(10)

        lbl_app_t = QLabel("🎨 Appearance & Styling")
        lbl_app_t.setStyleSheet("font-weight: bold; font-size: 13px; color: #60a5fa;")
        c1_lay.addWidget(lbl_app_t)

        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("Interface Theme:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark (Fluent Dark)", "Light (Clean Light)"])
        current_theme = self.db.get_setting("theme", "dark")
        self.combo_theme.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        row_theme.addWidget(self.combo_theme)
        row_theme.addStretch()
        c1_lay.addLayout(row_theme)

        lay.addWidget(card_app)

        # 2. Output Folders Card
        card_dir = QFrame()
        card_dir.setProperty("class", "cardFrame")
        c2_lay = QVBoxLayout(card_dir)
        c2_lay.setSpacing(10)

        lbl_dir_t = QLabel("📁 Default Storage & Exports")
        lbl_dir_t.setStyleSheet("font-weight: bold; font-size: 13px; color: #60a5fa;")
        c2_lay.addWidget(lbl_dir_t)

        row_d = QHBoxLayout()
        row_d.addWidget(QLabel("Default Output Directory:"))
        self.txt_default_dir = QLineEdit(
            self.db.get_setting("default_output_dir", str(Path.home() / "Documents" / "DocuTools"))
        )
        row_d.addWidget(self.txt_default_dir, stretch=1)
        btn_browse = QPushButton("Change...")
        btn_browse.clicked.connect(self._choose_default_dir)
        row_d.addWidget(btn_browse)
        c2_lay.addLayout(row_d)

        lay.addWidget(card_dir)

        # 3. Keyboard Shortcuts Reference Table
        card_keys = QFrame()
        card_keys.setProperty("class", "cardFrame")
        c3_lay = QVBoxLayout(card_keys)
        c3_lay.setSpacing(8)

        lbl_keys_t = QLabel("⌨️ Keyboard Shortcuts Reference")
        lbl_keys_t.setStyleSheet("font-weight: bold; font-size: 13px; color: #60a5fa;")
        c3_lay.addWidget(lbl_keys_t)

        table_keys = QTableWidget(len(self.KEYBOARD_SHORTCUTS), 2)
        table_keys.setHorizontalHeaderLabels(["Shortcut", "Action"])
        table_keys.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table_keys.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row, (sc, desc) in enumerate(self.KEYBOARD_SHORTCUTS):
            item_sc = QTableWidgetItem(sc)
            item_sc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = item_sc.font()
            font.setBold(True)
            item_sc.setFont(font)
            item_desc = QTableWidgetItem(desc)
            table_keys.setItem(row, 0, item_sc)
            table_keys.setItem(row, 1, item_desc)

        table_keys.setFixedHeight(260)
        c3_lay.addWidget(table_keys)
        lay.addWidget(card_keys)

        # 4. About Card
        card_about = QFrame()
        card_about.setStyleSheet("background-color: #17181c; border-radius: 8px; padding: 12px;")
        ab_outer = QHBoxLayout(card_about)
        ab_outer.setSpacing(12)

        about_icon_lbl = QLabel()
        about_icon_px = QPixmap(get_app_icon_path())
        if not about_icon_px.isNull():
            about_icon_lbl.setPixmap(about_icon_px.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        ab_outer.addWidget(about_icon_lbl)

        ab_lay = QVBoxLayout()
        ab_lay.setSpacing(2)
        lbl_about_title = QLabel("DocuTools Desktop Suite")
        lbl_about_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #f3f4f6;")
        lbl_about_desc = QLabel(
            "Built with Python 3.13 + PySide6 (Qt) + SQLite + Pillow + PyMuPDF + pikepdf + python-docx.<br/>"
            "Offline-first, modular Windows architecture with zero cloud telemetry."
        )
        lbl_about_desc.setStyleSheet("color: #9ca3af; font-size: 11px;")
        ab_lay.addWidget(lbl_about_title)
        ab_lay.addWidget(lbl_about_desc)
        ab_outer.addLayout(ab_lay, stretch=1)
        lay.addWidget(card_about)

        lay.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

    def _on_theme_changed(self, index: int) -> None:
        theme = "dark" if index == 0 else "light"
        self.db.set_setting("theme", theme)
        self.theme_change_callback(theme)

    def _choose_default_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Default Directory", self.txt_default_dir.text())
        if folder:
            self.txt_default_dir.setText(folder)
            self.db.set_setting("default_output_dir", folder)
