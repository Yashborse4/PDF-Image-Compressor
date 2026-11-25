"""Reusable custom UI components following Windows 11 Fluent Design principles."""

from __future__ import annotations

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class FluentCard(QFrame):
    """An elegant rounded container card with Windows 11 Fluent elevation."""

    clicked = Signal()

    def __init__(
        self,
        title: str = "",
        description: str = "",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("card", "true")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        if icon_name:
            icon_badge = QFrame()
            icon_badge.setStyleSheet(
                "background-color: rgba(96, 205, 255, 0.12); "
                "border-radius: 8px; "
                "min-width: 38px; min-height: 38px; max-width: 38px; max-height: 38px;"
            )
            badge_layout = QVBoxLayout(icon_badge)
            badge_layout.setContentsMargins(0, 0, 0, 0)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color="#60cdff").pixmap(QSize(20, 20)))
            icon_label.setStyleSheet("background: transparent;")
            badge_layout.addWidget(icon_label)
            header_layout.addWidget(icon_badge)

        if title:
            self.title_label = QLabel(title)
            title_font = QFont("Segoe UI Variable Display", 12, QFont.Weight.DemiBold)
            self.title_label.setFont(title_font)
            self.title_label.setStyleSheet("color: #ffffff;")
            header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Chevron arrow indicator
        chevron = QLabel()
        chevron.setPixmap(qta.icon("fa5s.chevron-right", color="#6b7280").pixmap(QSize(12, 12)))
        header_layout.addWidget(chevron)

        layout.addLayout(header_layout)

        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet("color: #9ca3af; font-size: 11.5px; line-height: 1.4;")
            layout.addWidget(self.desc_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class StatCard(QFrame):
    """Metrics display card for dashboard showing key numbers with rounded icon badge."""

    def __init__(
        self,
        label: str,
        value: str,
        subtext: str = "",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("card", "true")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        if icon_name:
            icon_circle = QFrame()
            icon_circle.setStyleSheet(
                "background-color: rgba(96, 205, 255, 0.12); "
                "border-radius: 20px; "
                "min-width: 40px; min-height: 40px; max-width: 40px; max-height: 40px;"
            )
            c_layout = QVBoxLayout(icon_circle)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_name, color="#60cdff").pixmap(QSize(20, 20)))
            icon_lbl.setStyleSheet("background: transparent;")
            c_layout.addWidget(icon_lbl)
            layout.addWidget(icon_circle)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        self.label_widget = QLabel(label.upper())
        self.label_widget.setStyleSheet("color: #9ca3af; font-size: 10px; font-weight: 600; letter-spacing: 0.6px;")
        text_layout.addWidget(self.label_widget)

        self.value_widget = QLabel(value)
        v_font = QFont("Segoe UI Variable Display", 16, QFont.Weight.Bold)
        self.value_widget.setFont(v_font)
        self.value_widget.setStyleSheet("color: #ffffff;")
        text_layout.addWidget(self.value_widget)

        if subtext:
            self.sub_widget = QLabel(subtext)
            self.sub_widget.setStyleSheet("color: #888888; font-size: 10.5px;")
            text_layout.addWidget(self.sub_widget)

        layout.addLayout(text_layout)
        layout.addStretch()

    def update_value(self, new_value: str, new_subtext: str | None = None) -> None:
        """Dynamically update metric value."""
        self.value_widget.setText(new_value)
        if new_subtext and hasattr(self, "sub_widget"):
            self.sub_widget.setText(new_subtext)


class FileDropArea(QFrame):
    """Interactive drag-and-drop zone with Windows 11 rounded dashed outline."""

    files_dropped = Signal(list)  # list of file path strings

    def __init__(
        self,
        prompt_text: str = "Drag & Drop files here, or click to Browse",
        accepted_extensions: set[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.accepted_extensions = accepted_extensions or set()
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(130)
        self._apply_normal_style()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setPixmap(qta.icon("fa5s.cloud-upload-alt", color="#60cdff").pixmap(QSize(40, 40)))
        layout.addWidget(self.icon_lbl)

        self.label = QLabel(prompt_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Segoe UI Variable Display", 11.5, QFont.Weight.DemiBold)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.label)

        ext_text = "Supports: " + ", ".join(sorted(self.accepted_extensions)) if self.accepted_extensions else "All supported files"
        self.ext_label = QLabel(ext_text)
        self.ext_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ext_label.setStyleSheet("color: #9ca3af; font-size: 10.5px;")
        layout.addWidget(self.ext_label)

    def _apply_normal_style(self) -> None:
        self.setStyleSheet(
            "QFrame {"
            "  border: 2px dashed #40404c;"
            "  border-radius: 14px;"
            "  background-color: rgba(255, 255, 255, 0.02);"
            "}"
            "QFrame:hover {"
            "  border: 2px dashed #60cdff;"
            "  background-color: rgba(96, 205, 255, 0.04);"
            "}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "border: 2px dashed #60cdff;"
                "border-radius: 14px;"
                "background-color: rgba(96, 205, 255, 0.10);"
            )

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._apply_normal_style()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._apply_normal_style()
        urls = event.mimeData().urls()
        dropped_files: list[str] = []

        for url in urls:
            file_path = Path(url.toLocalFile())
            if file_path.is_file():
                if not self.accepted_extensions or file_path.suffix.lower() in self.accepted_extensions:
                    dropped_files.append(str(file_path))

        if dropped_files:
            self.files_dropped.emit(dropped_files)
        event.acceptProposedAction()


class StatusPill(QLabel):
    """Windows 11 capsule status badge with indicator dot."""

    def __init__(
        self,
        text: str,
        variant: str = "neutral",  # 'success', 'warning', 'danger', 'neutral'
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 9.5, QFont.Weight.Medium))
        self.raw_text = text
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        """Update color style for status pill with dot indicator."""
        dot = "● "
        self.setText(f"{dot}{self.raw_text}")

        styles = {
            "success": (
                "background-color: rgba(16, 185, 129, 0.15); "
                "color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); "
                "border-radius: 12px; padding: 3px 12px;"
            ),
            "warning": (
                "background-color: rgba(245, 158, 11, 0.15); "
                "color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); "
                "border-radius: 12px; padding: 3px 12px;"
            ),
            "danger": (
                "background-color: rgba(239, 68, 68, 0.15); "
                "color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); "
                "border-radius: 12px; padding: 3px 12px;"
            ),
            "neutral": (
                "background-color: rgba(156, 163, 175, 0.15); "
                "color: #d1d5db; border: 1px solid rgba(156, 163, 175, 0.3); "
                "border-radius: 12px; padding: 3px 12px;"
            ),
        }
        self.setStyleSheet(styles.get(variant, styles["neutral"]))
