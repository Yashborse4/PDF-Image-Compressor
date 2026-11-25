"""Home dashboard for DocuTools with Windows 11 Fluent Design, stats, and drag-and-drop routing."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.file_manager import FileManager
from app.database.history import HistoryManager
from app.ui.widgets import FileDropArea, FluentCard, StatCard


class DashboardView(QWidget):
    """Modern Windows 11 Fluent Home Dashboard."""

    navigate_to = Signal(str)  # Target page ID
    open_file_requested = Signal(str)  # File path to open

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history_mgr = HistoryManager()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(32, 28, 32, 28)
        self.layout.setSpacing(24)

        self._build_header()
        self._build_stats()
        self._build_drop_zone()
        self._build_tools_grid()
        self._build_recent_files()

        self.layout.addStretch()
        scroll.setWidget(content)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _build_header(self) -> None:
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)

        badge_row = QHBoxLayout()
        pill = QLabel("  WINDOWS 11 SUITE  ")
        pill.setStyleSheet(
            "background-color: rgba(96, 205, 255, 0.12); "
            "color: #60cdff; "
            "font-size: 10px; font-weight: 700; "
            "border-radius: 9px; padding: 2px 6px;"
        )
        badge_row.addWidget(pill)
        badge_row.addStretch()
        header_layout.addLayout(badge_row)

        title = QLabel("Welcome to DocuTools")
        title_font = QFont("Segoe UI Variable Display", 22, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        subtitle = QLabel("Your unified, 100% offline document, PDF, and image processing workspace.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13.5px;")
        header_layout.addWidget(subtitle)

        self.layout.addLayout(header_layout)

    def _build_stats(self) -> None:
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        stats_data = self.history_mgr.get_statistics()
        total_tasks = str(stats_data.get("total_tasks", 0))
        saved_bytes = FileManager.format_file_size(stats_data.get("total_bytes_saved", 0))

        self.stat_processed = StatCard(
            label="Processed Tasks",
            value=total_tasks,
            subtext="Lifetime local operations",
            icon_name="fa5s.tasks",
        )
        self.stat_saved = StatCard(
            label="Storage Saved",
            value=saved_bytes,
            subtext="Via PDF & image optimization",
            icon_name="fa5s.hdd",
        )
        self.stat_privacy = StatCard(
            label="Offline & Private",
            value="100% Local",
            subtext="Zero cloud uploads or telemetry",
            icon_name="fa5s.shield-alt",
        )

        stats_layout.addWidget(self.stat_processed)
        stats_layout.addWidget(self.stat_saved)
        stats_layout.addWidget(self.stat_privacy)
        self.layout.addLayout(stats_layout)

    def refresh_stats(self) -> None:
        """Fetch updated statistics and refresh stat cards."""
        stats_data = self.history_mgr.get_statistics()
        total_tasks = str(stats_data.get("total_tasks", 0))
        saved_bytes = FileManager.format_file_size(stats_data.get("total_bytes_saved", 0))
        if hasattr(self, "stat_processed"):
            self.stat_processed.update_value(total_tasks)
        if hasattr(self, "stat_saved"):
            self.stat_saved.update_value(saved_bytes)

    def showEvent(self, event) -> None:
        """Refresh dynamic stats and recent files upon navigating to dashboard."""
        super().showEvent(event)
        self.refresh_stats()
        self.refresh_recent_files()

    def _build_drop_zone(self) -> None:
        self.drop_area = FileDropArea(
            prompt_text="Drag & drop any PDF, Word document, or image here to begin",
        )
        self.drop_area.files_dropped.connect(self._handle_files_dropped)
        self.layout.addWidget(self.drop_area)

    def _build_tools_grid(self) -> None:
        sec_label = QLabel("Quick Access Tools")
        sec_font = QFont("Segoe UI Variable Display", 15, QFont.Weight.DemiBold)
        sec_label.setFont(sec_font)
        sec_label.setStyleSheet("color: #ffffff;")
        self.layout.addWidget(sec_label)

        grid = QGridLayout()
        grid.setSpacing(16)

        tools = [
            (
                "PDF Organize & Merge",
                "Merge multiple PDFs, visual page reordering, rotation, and deletion.",
                "fa5s.file-pdf",
                "pdf_tools:organize",
            ),
            (
                "PDF Editor",
                "Edit PDF text in-place, modify images, add highlights, and sign documents.",
                "fa5s.edit",
                "pdf_editor",
            ),
            (
                "PDF Compressor",
                "Lossless stream compression & high-ratio raster image downsampling.",
                "fa5s.compress-arrows-alt",
                "pdf_tools:compress",
            ),
            (
                "PDF Splitter",
                "Split by custom page ranges, extract pages, or burst into individual files.",
                "fa5s.cut",
                "pdf_tools:split",
            ),
            (
                "Document Editor",
                "Word-style DOCX rich-text workspace with formatting, tables, and PDF export.",
                "fa5s.file-word",
                "doc_editor",
            ),
            (
                "Image Tools",
                "Resize, crop, convert, and compress images to target sizes (e.g. 50 KB, 100 KB).",
                "fa5s.image",
                "image_tools",
            ),
            (
                "Batch Processor",
                "Concurrent multi-file image optimization and conversion queue.",
                "fa5s.layer-group",
                "batch",
            ),
            (
                "Digital Signatures",
                "PAdES cryptographic signatures, certificate manager, and integrity verification.",
                "fa5s.file-signature",
                "pdf_tools:sign",
            ),
        ]

        for idx, (title, desc, icon, page_id) in enumerate(tools):
            card = FluentCard(title=title, description=desc, icon_name=icon)
            card.clicked.connect(lambda p=page_id: self.navigate_to.emit(p))
            row = idx // 3
            col = idx % 3
            grid.addWidget(card, row, col)

        self.layout.addLayout(grid)

    def _build_recent_files(self) -> None:
        header_layout = QHBoxLayout()
        sec_label = QLabel("Recent Files")
        sec_font = QFont("Segoe UI Variable Display", 15, QFont.Weight.DemiBold)
        sec_label.setFont(sec_font)
        sec_label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(sec_label)
        header_layout.addStretch()

        clear_btn = QPushButton("Clear Recent")
        clear_btn.setProperty("variant", "flat")
        clear_btn.clicked.connect(self._clear_recent_files)
        header_layout.addWidget(clear_btn)
        self.layout.addLayout(header_layout)

        self.recent_table = QTableWidget(0, 4)
        self.recent_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Action"])
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setMinimumHeight(160)

        self.layout.addWidget(self.recent_table)
        self.refresh_recent_files()

    def refresh_recent_files(self) -> None:
        """Reload recent files from the SQLite database."""
        files = self.history_mgr.get_recent_files(limit=8)
        self.recent_table.setRowCount(len(files))

        for row_idx, f in enumerate(files):
            # Name
            name_item = QTableWidgetItem(f.file_name)
            name_item.setToolTip(f.file_path)
            self.recent_table.setItem(row_idx, 0, name_item)

            # Type badge
            type_item = QTableWidgetItem(f.file_type.upper())
            self.recent_table.setItem(row_idx, 1, type_item)

            # Size
            size_str = FileManager.format_file_size(f.file_size)
            size_item = QTableWidgetItem(size_str)
            self.recent_table.setItem(row_idx, 2, size_item)

            # Action button
            action_btn = QPushButton("Open")
            action_btn.setProperty("variant", "flat")
            action_btn.clicked.connect(lambda _, path=f.file_path: self.open_file_requested.emit(path))
            self.recent_table.setCellWidget(row_idx, 3, action_btn)

    def _clear_recent_files(self) -> None:
        self.history_mgr.clear_recent_files()
        self.refresh_recent_files()

    def _handle_files_dropped(self, file_paths: list[str]) -> None:
        """Route dropped files to the appropriate editor or tool."""
        if not file_paths:
            return

        first_file = Path(file_paths[0])
        ext = first_file.suffix.lower()

        # Add to recents
        self.history_mgr.add_recent_file(first_file)
        self.refresh_recent_files()

        if ext == ".pdf":
            self.open_file_requested.emit(str(first_file))
        elif ext in {".docx", ".doc"}:
            self.navigate_to.emit("doc_editor")
            self.open_file_requested.emit(str(first_file))
        elif ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            self.navigate_to.emit("image_tools")
            self.open_file_requested.emit(str(first_file))
        else:
            QMessageBox.information(
                self,
                "Unsupported File",
                f"File format '{ext}' is not supported for direct preview.",
            )
