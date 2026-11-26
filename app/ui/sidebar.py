"""Collapsible Windows 11 Fluent navigation sidebar with smooth width transitions."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SidebarWidget(QWidget):
    """Left navigation panel with Windows 11 rounded pill styling and smooth collapse animation."""

    page_selected = Signal(str)  # Emits page ID

    NAV_ITEMS = [
        ("home", "Home", "fa5s.home"),
        ("pdf_tools", "PDF Tools", "fa5s.file-pdf"),
        ("pdf_editor", "PDF Editor", "fa5s.edit"),
        ("doc_editor", "Document Editor", "fa5s.file-word"),
        ("image_tools", "Image Tools", "fa5s.image"),
        ("converter", "File Converter", "fa5s.exchange-alt"),
        ("batch", "Batch Processing", "fa5s.layer-group"),
        ("history", "History", "fa5s.history"),
        ("settings", "Settings", "fa5s.cog"),
        ("about", "About", "fa5s.info-circle"),
    ]

    EXPANDED_WIDTH = 224
    COLLAPSED_WIDTH = 68

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._is_collapsed = False
        self._anim: QPropertyAnimation | None = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 14, 8, 14)
        main_layout.setSpacing(4)

        # 1. App Brand Header
        self.brand_container = QWidget()
        brand_layout = QHBoxLayout(self.brand_container)
        brand_layout.setContentsMargins(6, 2, 6, 12)
        brand_layout.setSpacing(10)

        import qtawesome as qta
        self.brand_badge = QFrame()
        self.brand_badge.setStyleSheet(
            "background-color: rgba(96, 205, 255, 0.14); "
            "border-radius: 9px; "
            "min-width: 34px; min-height: 34px; max-width: 34px; max-height: 34px;"
        )
        b_layout = QVBoxLayout(self.brand_badge)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.brand_icon = QLabel()
        self.brand_icon.setPixmap(qta.icon("fa5s.shapes", color="#60cdff").pixmap(QSize(18, 18)))
        self.brand_icon.setStyleSheet("background: transparent;")
        b_layout.addWidget(self.brand_icon)
        brand_layout.addWidget(self.brand_badge)

        self.brand_text_box = QWidget()
        b_text_layout = QVBoxLayout(self.brand_text_box)
        b_text_layout.setContentsMargins(0, 0, 0, 0)
        b_text_layout.setSpacing(1)

        self.brand_title = QLabel("DocuTools")
        title_font = QFont("Segoe UI Variable Display", 13, QFont.Weight.Bold)
        self.brand_title.setFont(title_font)
        b_text_layout.addWidget(self.brand_title)

        self.brand_sub = QLabel("Desktop Suite")
        self.brand_sub.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 500;")
        b_text_layout.addWidget(self.brand_sub)

        brand_layout.addWidget(self.brand_text_box)
        brand_layout.addStretch()
        main_layout.addWidget(self.brand_container)

        # Subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.22); max-height: 1px; margin: 4px 6px 8px 6px;")
        main_layout.addWidget(divider)

        # 2. Nav Buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for item_id, label, icon_name in self.NAV_ITEMS:
            btn = QPushButton(f"  {label}")
            btn.setIcon(qta.icon(icon_name, color="#9ca3af"))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setProperty("nav", "true")
            btn.setToolTip(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            btn.clicked.connect(lambda checked=False, id_=item_id: self._on_item_clicked(id_))

            self.button_group.addButton(btn)
            self._buttons[item_id] = btn
            main_layout.addWidget(btn)

        main_layout.addStretch()

        # 3. Bottom Collapse / Expand Toggle
        collapse_box = QHBoxLayout()
        collapse_box.setContentsMargins(4, 4, 4, 4)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setProperty("variant", "flat")
        self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-left", color="#9ca3af"))
        self.collapse_btn.setIconSize(QSize(16, 16))
        self.collapse_btn.setToolTip("Collapse Navigation Sidebar")
        self.collapse_btn.clicked.connect(self.toggle_collapse)

        collapse_box.addWidget(self.collapse_btn)
        collapse_box.addStretch()
        main_layout.addLayout(collapse_box)

        # Select Home initially without emitting signal
        if "home" in self._buttons:
            self._buttons["home"].setChecked(True)
            self._update_icons("home")

    def _update_icons(self, active_page_id: str) -> None:
        """Update icon colors for active vs inactive items."""
        import qtawesome as qta
        for item_id, label, icon_name in self.NAV_ITEMS:
            btn = self._buttons[item_id]
            is_active = (item_id == active_page_id)
            color = "#60cdff" if is_active else "#9ca3af"
            btn.setIcon(qta.icon(icon_name, color=color))

    def select_page(self, page_id: str, emit_signal: bool = True) -> None:
        """Programmatically switch active navigation button."""
        if page_id in self._buttons:
            self._buttons[page_id].setChecked(True)
            self._update_icons(page_id)
            if emit_signal:
                self.page_selected.emit(page_id)

    def _on_item_clicked(self, page_id: str) -> None:
        """Handle nav button click."""
        self._update_icons(page_id)
        self.page_selected.emit(page_id)

    def toggle_collapse(self) -> None:
        """Smoothly animate collapse/expansion of the navigation sidebar."""
        import qtawesome as qta
        self._is_collapsed = not self._is_collapsed
        target_w = self.COLLAPSED_WIDTH if self._is_collapsed else self.EXPANDED_WIDTH

        # Animate minimum and maximum width
        self._anim = QPropertyAnimation(self, b"minimumWidth", self)
        self._anim.setDuration(180)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target_w)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_max = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim_max.setDuration(180)
        self._anim_max.setStartValue(self.width())
        self._anim_max.setEndValue(target_w)
        self._anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_finish():
            self.setFixedWidth(target_w)
            # Toggle text visibility
            self.brand_text_box.setVisible(not self._is_collapsed)
            for item_id, label, _ in self.NAV_ITEMS:
                btn = self._buttons[item_id]
                btn.setText("" if self._is_collapsed else f"  {label}")

            icon_name = "fa5s.angle-double-right" if self._is_collapsed else "fa5s.angle-double-left"
            self.collapse_btn.setIcon(qta.icon(icon_name, color="#9ca3af"))
            self.collapse_btn.setToolTip("Expand Navigation Sidebar" if self._is_collapsed else "Collapse Navigation Sidebar")

        self._anim.finished.connect(_on_finish)
        self._anim.start()
        self._anim_max.start()
