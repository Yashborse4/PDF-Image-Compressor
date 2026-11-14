"""Placeholder views for modular tools during initial phase rollout."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import FileDropArea, FluentCard


class BaseToolView(QWidget):
    """Base template for tool views with consistent header and action areas."""

    file_selected = Signal(str)

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_name: str,
        accepted_extensions: set[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.accepted_extensions = accepted_extensions

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(18)

        # Header
        header = QVBoxLayout()
        header.setSpacing(4)
        t_label = QLabel(title)
        t_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.addWidget(t_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        header.addWidget(sub_label)
        self.main_layout.addLayout(header)

        # Drop Area
        self.drop_area = FileDropArea(
            prompt_text=f"Drag & drop {title} input files here, or choose below",
            accepted_extensions=accepted_extensions,
        )
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        self.main_layout.addWidget(self.drop_area)

        # Action Buttons row
        btn_layout = QHBoxLayout()
        choose_btn = QPushButton("Choose File...")
        choose_btn.setProperty("variant", "accent")
        choose_btn.clicked.connect(self._choose_file)
        btn_layout.addWidget(choose_btn)
        btn_layout.addStretch()
        self.main_layout.addLayout(btn_layout)

    def _choose_file(self) -> None:
        exts = " ".join(f"*{e}" for e in self.accepted_extensions) if self.accepted_extensions else "*.*"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document or Image",
            "",
            f"Supported Files ({exts});;All Files (*.*)",
        )
        if file_path:
            self.file_selected.emit(file_path)

    def _on_files_dropped(self, files: list[str]) -> None:
        if files:
            self.file_selected.emit(files[0])


class PdfToolsView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="PDF Management Tools",
            subtitle="Merge multiple PDFs, split into ranges, compress files, and reorder pages.",
            icon_name="fa5s.file-pdf",
            accepted_extensions={".pdf"},
            parent=parent,
        )
        # Summary card
        card = FluentCard(
            title="Phase 2 Features Active",
            description="PDF Merger, Range Splitter, Dual-Engine Compressor, Page Manager, and AES Security.",
            icon_name="fa5s.check-circle",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()


class PdfEditorView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Advanced PDF Editor",
            subtitle="View, in-place edit text, draw annotations, add images, and sign documents.",
            icon_name="fa5s.edit",
            accepted_extensions={".pdf"},
            parent=parent,
        )
        card = FluentCard(
            title="PDF In-Place Editing Engine",
            description="Redaction-reinsertion algorithm, bounding box detection, and undo/redo snapshots.",
            icon_name="fa5s.pencil-alt",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()


class DocEditorView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Word Document Editor",
            subtitle="Word-style rich-text workspace with formatting, tables, images, and PDF export.",
            icon_name="fa5s.file-word",
            accepted_extensions={".docx", ".doc", ".txt", ".rtf"},
            parent=parent,
        )
        card = FluentCard(
            title="DOCX Document Engine",
            description="python-docx integration and rich-text QTextDocument editor.",
            icon_name="fa5s.file-alt",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()


class ImageToolsView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Image Studio",
            subtitle="Resize, crop, format convert, and compress images to target sizes (e.g. 50 KB, 100 KB).",
            icon_name="fa5s.image",
            accepted_extensions={".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"},
            parent=parent,
        )
        card = FluentCard(
            title="Target File-Size Compression",
            description="Iterative binary search algorithm optimizing quality and dimensions to hit exact targets.",
            icon_name="fa5s.compress",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()


class ConverterView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="File Converter",
            subtitle="Universal local conversions: PDF to Images, Images to PDF, DOCX to PDF.",
            icon_name="fa5s.exchange-alt",
            accepted_extensions={".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"},
            parent=parent,
        )
        card = FluentCard(
            title="High-Fidelity Offline Transcoding",
            description="All conversions occur locally with zero cloud dependencies.",
            icon_name="fa5s.sync-alt",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()


class BatchView(BaseToolView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Batch Processing Queue",
            subtitle="Queue dozens or hundreds of files for concurrent resizing, conversion, and compression.",
            icon_name="fa5s.layer-group",
            accepted_extensions={".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx"},
            parent=parent,
        )
        card = FluentCard(
            title="Concurrent Thread Pool Engine",
            description="Multi-threaded processing with real-time progress indicators and cancellation control.",
            icon_name="fa5s.cogs",
        )
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()
