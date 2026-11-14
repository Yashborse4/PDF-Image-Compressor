"""
Interactive Page Thumbnail Card for PDF Manager.
Displays high-fidelity page preview, page number, selection checkbox, and rotate/delete actions.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ThumbnailCard(QFrame):
    """Visual page card for PDF thumbnail grids."""
    selection_changed = Signal(int, bool)  # (page_index, is_selected)
    rotate_requested = Signal(int)         # (page_index)
    delete_requested = Signal(int)         # (page_index)
    move_left_requested = Signal(int)      # (page_index)
    move_right_requested = Signal(int)     # (page_index)

    def __init__(
        self,
        page_index: int,
        page_number: int,
        pixmap_bytes: bytes,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.page_index = page_index
        self.page_number = page_number
        self.setFixedSize(170, 240)
        self.setProperty("class", "cardFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Top bar: Checkbox + Page Badge
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(2, 2, 2, 2)
        top_bar.setSpacing(4)

        self.chk_select = QCheckBox()
        self.chk_select.setToolTip("Select page for extraction/deletion")
        self.chk_select.toggled.connect(lambda checked: self.selection_changed.emit(self.page_index, checked))
        top_bar.addWidget(self.chk_select)

        self.lbl_page = QLabel(f"Page {page_number}")
        self.lbl_page.setStyleSheet("font-weight: 600; font-size: 11px; color: #93c5fd;")
        top_bar.addWidget(self.lbl_page)

        top_bar.addStretch()

        # Rotate button
        self.btn_rotate = QPushButton("⟳")
        self.btn_rotate.setFixedSize(20, 20)
        self.btn_rotate.setToolTip("Rotate page 90° clockwise")
        self.btn_rotate.setStyleSheet("padding: 0; font-size: 12px;")
        self.btn_rotate.clicked.connect(lambda: self.rotate_requested.emit(self.page_index))
        top_bar.addWidget(self.btn_rotate)

        # Delete button
        self.btn_delete = QPushButton("✕")
        self.btn_delete.setFixedSize(20, 20)
        self.btn_delete.setToolTip("Delete this page")
        self.btn_delete.setStyleSheet("padding: 0; font-size: 10px; color: #ef4444;")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.page_index))
        top_bar.addWidget(self.btn_delete)

        layout.addLayout(top_bar)

        # Thumbnail Image Display
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background-color: #111215; border-radius: 4px; border: 1px solid #282a30;")
        self.set_pixmap(pixmap_bytes)
        layout.addWidget(self.lbl_image, stretch=1)

        # Bottom Bar: Move Up / Down (Left / Right) buttons
        bot_bar = QHBoxLayout()
        bot_bar.setContentsMargins(2, 2, 2, 2)
        bot_bar.setSpacing(4)

        self.btn_left = QPushButton("◀")
        self.btn_left.setFixedSize(24, 20)
        self.btn_left.setToolTip("Move page earlier")
        self.btn_left.setStyleSheet("padding: 0; font-size: 9px;")
        self.btn_left.clicked.connect(lambda: self.move_left_requested.emit(self.page_index))
        bot_bar.addWidget(self.btn_left)

        bot_bar.addStretch()

        self.btn_right = QPushButton("▶")
        self.btn_right.setFixedSize(24, 20)
        self.btn_right.setToolTip("Move page later")
        self.btn_right.setStyleSheet("padding: 0; font-size: 9px;")
        self.btn_right.clicked.connect(lambda: self.move_right_requested.emit(self.page_index))
        bot_bar.addWidget(self.btn_right)

        layout.addLayout(bot_bar)

    def set_pixmap(self, pixmap_bytes: bytes) -> None:
        px = QPixmap()
        px.loadFromData(pixmap_bytes)
        scaled = px.scaled(150, 175, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_image.setPixmap(scaled)

    def is_selected(self) -> bool:
        return self.chk_select.isChecked()

    def set_selected(self, selected: bool) -> None:
        self.chk_select.setChecked(selected)
