"""Smooth UI transitions and animation helpers for Windows 11 Fluent experience."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class SmoothStackedWidget(QStackedWidget):
    """StackedWidget with smooth fade and subtle slide transitions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fade_anim: QPropertyAnimation | None = None
        self._slide_anim: QPropertyAnimation | None = None
        self._effect: QGraphicsOpacityEffect | None = None

    def fade_to_widget(self, target_widget: QWidget, duration_ms: int = 200) -> None:
        """Smoothly fade and slide the target widget into view."""
        if self.currentWidget() == target_widget:
            return

        # Prepare opacity effect on target
        self._effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(self._effect)

        # Switch widget in stack
        self.setCurrentWidget(target_widget)

        # 1. Opacity fade-in animation
        self._fade_anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 2. Subtle upward slide (8px)
        orig_pos = target_widget.pos()
        target_widget.move(orig_pos.x(), orig_pos.y() + 8)

        self._slide_anim = QPropertyAnimation(target_widget, b"pos", self)
        self._slide_anim.setDuration(duration_ms)
        self._slide_anim.setStartValue(QPoint(orig_pos.x(), orig_pos.y() + 8))
        self._slide_anim.setEndValue(orig_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Clean up effect on finish to prevent rendering overhead
        def _cleanup():
            target_widget.setGraphicsEffect(None)
            target_widget.move(orig_pos)

        self._fade_anim.finished.connect(_cleanup)
        self._fade_anim.start()
        self._slide_anim.start()
