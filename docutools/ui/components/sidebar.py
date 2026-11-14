"""
Modern Collapsible Sidebar Navigation for DocuTools.
Supports 8 primary modules with responsive collapse / expand toggle.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from docutools.core.assets import get_app_icon_path, get_sidebar_toggle_icon_path


class Sidebar(QWidget):
    """Collapsible navigation sidebar."""
    page_changed = Signal(int)  # index of selected page

    NAV_ITEMS = [
        (0, "🏠", "Home", "Dashboard and recent files"),
        (1, "📄", "PDF Tools", "All PDF operations"),
        (2, "📝", "Document Editor", "Word-style editing"),
        (3, "🖼️", "Image Tools", "Image processing"),
        (4, "🔄", "Converter", "Format conversion"),
        (5, "📦", "Batch Processing", "Multiple files"),
        (6, "📜", "History", "Previous operations"),
        (7, "⚙️", "Settings", "Preferences and appearance"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setFixedWidth(240)
        self.is_collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(4)

        # Header / Brand
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 10)

        self.logo_icon = QLabel()
        icon_px = QPixmap(get_app_icon_path())
        if not icon_px.isNull():
            self.logo_icon.setPixmap(icon_px.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_icon.setText("📄")
            self.logo_icon.setStyleSheet("font-size: 20px;")
        header_layout.addWidget(self.logo_icon)

        self.title_box = QVBoxLayout()
        self.title_box.setSpacing(1)
        self.title_label = QLabel("DocuTools")
        self.title_label.setObjectName("sidebarTitle")
        self.subtitle_label = QLabel("Desktop Suite")
        self.subtitle_label.setObjectName("sidebarSubtitle")
        self.title_box.addWidget(self.title_label)
        self.title_box.addWidget(self.subtitle_label)
        header_layout.addLayout(self.title_box)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #282a30; margin-bottom: 6px;")
        layout.addWidget(sep)

        # Nav buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.buttons: Dict[int, QPushButton] = {}

        for idx, icon, title, desc in self.NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {title}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "navButton")
            btn.setToolTip(desc)
            if idx == 0:
                btn.setChecked(True)
                btn.setProperty("active", "true")

            btn.clicked.connect(lambda checked=False, i=idx: self._on_btn_clicked(i))
            self.button_group.addButton(btn, idx)
            self.buttons[idx] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Collapse / Expand toggle button at bottom (Icon only, no text)
        self.btn_collapse = QPushButton()
        self.btn_collapse.setObjectName("btnSidebarCollapse")
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setToolTip("Toggle Sidebar (Ctrl+W)")
        self.btn_collapse.setFixedHeight(36)
        self.btn_collapse.setStyleSheet("""
            QPushButton#btnSidebarCollapse {
                background: transparent;
                border: 1px solid #282a30;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton#btnSidebarCollapse:hover {
                background-color: #22242a;
                border-color: #3b82f6;
            }
        """)
        self._update_collapse_icon()
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        layout.addWidget(self.btn_collapse)

    def _update_collapse_icon(self) -> None:
        icon_path = get_sidebar_toggle_icon_path(collapsed=self.is_collapsed)
        self.btn_collapse.setIcon(QIcon(icon_path))
        self.btn_collapse.setIconSize(QSize(22, 22))
        self.btn_collapse.setText("")  # Ensure strictly no text

    def _on_btn_clicked(self, index: int) -> None:
        for idx, btn in self.buttons.items():
            btn.setProperty("active", "true" if idx == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.page_changed.emit(index)

    def select_page(self, index: int) -> None:
        if index in self.buttons:
            self.buttons[index].setChecked(True)
            self._on_btn_clicked(index)

    def toggle_collapse(self) -> None:
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(68)
            self.title_label.hide()
            self.subtitle_label.hide()
            for idx, icon, title, desc in self.NAV_ITEMS:
                self.buttons[idx].setText(f" {icon}")
        else:
            self.setFixedWidth(240)
            self.title_label.show()
            self.subtitle_label.show()
            for idx, icon, title, desc in self.NAV_ITEMS:
                self.buttons[idx].setText(f"  {icon}  {title}")
        self._update_collapse_icon()
