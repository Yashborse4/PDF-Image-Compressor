"""Processing history view displaying local operation audit trail."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.file_manager import FileManager
from app.database.history import HistoryManager
from app.ui.widgets import StatusPill


class HistoryView(QWidget):
    """View displaying full audit log of all document and image operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history_mgr = HistoryManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Processing History")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("variant", "flat")
        refresh_btn.clicked.connect(self.refresh_history)
        header_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear All History")
        clear_btn.setProperty("variant", "flat")
        clear_btn.clicked.connect(self._clear_history)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Timestamp",
            "Operation",
            "Source File",
            "Output File",
            "Size Change",
            "Status",
            "Action",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)
        self.refresh_history()

    def refresh_history(self) -> None:
        """Fetch and populate history records."""
        records = self.history_mgr.get_recent_history(limit=100)
        self.table.setRowCount(len(records))

        for row_idx, r in enumerate(records):
            # Timestamp
            self.table.setItem(row_idx, 0, QTableWidgetItem(r.timestamp))

            # Operation
            op_item = QTableWidgetItem(r.operation_type)
            op_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            self.table.setItem(row_idx, 1, op_item)

            # Source file
            src_name = Path(r.source_file).name if r.source_file else "-"
            src_item = QTableWidgetItem(src_name)
            src_item.setToolTip(r.source_file)
            self.table.setItem(row_idx, 2, src_item)

            # Output file
            out_name = Path(r.output_file).name if r.output_file else "-"
            out_item = QTableWidgetItem(out_name)
            if r.output_file:
                out_item.setToolTip(r.output_file)
            self.table.setItem(row_idx, 3, out_item)

            # Size change
            if r.original_size > 0 and r.output_size > 0:
                change = r.compression_ratio_percent
                size_str = f"{FileManager.format_file_size(r.original_size)} -> {FileManager.format_file_size(r.output_size)} (-{change}%)"
            elif r.original_size > 0:
                size_str = FileManager.format_file_size(r.original_size)
            else:
                size_str = "-"
            self.table.setItem(row_idx, 4, QTableWidgetItem(size_str))

            # Status pill
            status_variant = "success" if r.status == "completed" else ("warning" if r.status == "cancelled" else "danger")
            pill = StatusPill(r.status.capitalize(), variant=status_variant)
            self.table.setCellWidget(row_idx, 5, pill)

            # Action: Open output folder
            if r.output_file and Path(r.output_file).exists():
                show_btn = QPushButton("Locate")
                show_btn.setProperty("variant", "flat")
                show_btn.clicked.connect(lambda _, path=r.output_file: self._locate_file(path))
                self.table.setCellWidget(row_idx, 6, show_btn)
            else:
                self.table.setItem(row_idx, 6, QTableWidgetItem("-"))

    def _locate_file(self, file_path: str) -> None:
        """Select file in Windows Explorer."""
        path = Path(file_path).resolve()
        if path.exists():
            subprocess.run(["explorer", f"/select,{path}"], check=False)

    def _clear_history(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all processing history? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.history_mgr.clear_history()
            self.refresh_history()
