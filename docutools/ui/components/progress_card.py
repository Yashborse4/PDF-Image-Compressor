"""
Progress Card widget for background tasks in DocuTools.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressCard(QFrame):
    """Modern progress card displaying status and bar for running operations."""
    cancelled = Signal()

    def __init__(self, title: str = "Processing Task...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("class", "cardFrame")
        self.setStyleSheet("""
            QFrame {
                background-color: #1e222b;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #93c5fd;")
        header.addWidget(self.lbl_title)

        header.addStretch()

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setFixedSize(22, 22)
        self.btn_cancel.setToolTip("Cancel task")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #9ca3af;
                font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_cancel.clicked.connect(self.cancelled.emit)
        header.addWidget(self.btn_cancel)
        layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status text row
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #9ca3af;")
        layout.addWidget(self.lbl_status)

        self.hide()

    def start_task(self, title: str) -> None:
        self.lbl_title.setText(title)
        self.lbl_status.setText("Working...")
        self.progress_bar.setValue(0)
        self.show()

    def update_progress(self, percent: int, message: str = "") -> None:
        self.progress_bar.setValue(percent)
        if message:
            self.lbl_status.setText(message)

    def complete_task(self, message: str = "Completed successfully!") -> None:
        self.progress_bar.setValue(100)
        self.lbl_status.setText(message)

    def fail_task(self, error_message: str) -> None:
        self.lbl_status.setText(f"Error: {error_message}")
        self.setStyleSheet("""
            QFrame {
                background-color: #2b1e1e;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 10px;
            }
        """)
