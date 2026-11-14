"""
Drag-and-drop file target widget for DocuTools with visual feedback and file dialog fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class DropZone(QFrame):
    """
    Interactive drop zone area accepting dragged files from Windows Explorer.
    Emits files_dropped(List[str]) signal.
    """
    files_dropped = Signal(list)

    def __init__(
        self,
        title: str = "Drag & Drop files here",
        subtitle: str = "or click browse to select from your computer",
        file_filter: str = "All Supported Files (*.pdf *.docx *.png *.jpg *.jpeg *.webp)",
        multi_select: bool = True,
        parent: Optional[QFrame] = None
    ):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_filter = file_filter
        self.multi_select = multi_select

        self.setObjectName("dropZone")
        self._is_hovered = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Big icon / symbol
        self.icon_label = QLabel("📥")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 38px; background: transparent; border: none;")
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent; border: none;")
        layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #888899; background: transparent; border: none;")
        layout.addWidget(self.subtitle_label)

        # Browse Button
        self.btn_browse = QPushButton("Browse Files...")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        self.btn_browse.clicked.connect(self._open_file_dialog)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.btn_browse)
        layout.addLayout(btn_layout)

        self._update_style()

    def _update_style(self) -> None:
        if self._is_hovered:
            self.setStyleSheet("""
                QFrame#dropZone {
                    border: 2px dashed #3b82f6;
                    border-radius: 12px;
                    background-color: rgba(37, 99, 235, 0.12);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#dropZone {
                    border: 2px dashed #4b5563;
                    border-radius: 12px;
                    background-color: rgba(30, 32, 38, 0.4);
                }
            """)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._is_hovered = True
            self._update_style()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._is_hovered = False
        self._update_style()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._is_hovered = False
        self._update_style()

        urls = event.mimeData().urls()
        file_paths = [Path(u.toLocalFile()).resolve() for u in urls if u.isLocalFile()]
        valid_paths = [str(p) for p in file_paths if p.is_file()]

        if valid_paths:
            self.files_dropped.emit(valid_paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _open_file_dialog(self) -> None:
        if self.multi_select:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", self.file_filter)
            if files:
                self.files_dropped.emit(files)
        else:
            file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", self.file_filter)
            if file_name:
                self.files_dropped.emit([file_name])
