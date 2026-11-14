"""
Home Dashboard View for DocuTools.
Features:
- Welcome banner and dashboard summary metrics (operations, storage saved, recents count)
- Quick Action shortcut cards to jump directly to any tool
- Universal Drag-and-Drop file ingestion area
- Interactive Recent Files ledger with 'Open in Tool' and 'Reveal in Explorer'
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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

from docutools.core.assets import get_app_icon_path
from docutools.core.database import Database
from docutools.core.validator import format_file_size, get_file_type
from docutools.ui.components.drop_zone import DropZone


class HomeView(QWidget):
    """Dashboard and Recent Files View."""
    navigate_requested = Signal(int)       # emits target view index
    file_open_requested = Signal(str, str) # emits (file_path, file_type)

    def __init__(self, db: Database, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Welcome & Status Header
        header_frame = QFrame()
        header_frame.setProperty("class", "cardFrame")
        h_outer = QHBoxLayout(header_frame)
        h_outer.setContentsMargins(14, 12, 14, 12)
        h_outer.setSpacing(14)

        icon_lbl = QLabel()
        icon_px = QPixmap(get_app_icon_path())
        if not icon_px.isNull():
            icon_lbl.setPixmap(icon_px.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        h_outer.addWidget(icon_lbl)

        h_lay = QVBoxLayout()
        h_lay.setSpacing(2)
        lbl_welcome = QLabel("DocuTools Dashboard")
        lbl_welcome.setProperty("class", "heading")
        lbl_sub = QLabel("Modular, high-performance offline document authoring and media processing suite.")
        lbl_sub.setProperty("class", "subheading")
        h_lay.addWidget(lbl_welcome)
        h_lay.addWidget(lbl_sub)
        h_outer.addLayout(h_lay, stretch=1)
        main_layout.addWidget(header_frame)

        # Quick Actions Grid
        lbl_quick = QLabel("Quick Actions")
        lbl_quick.setStyleSheet("font-weight: 700; font-size: 14px; color: #60a5fa;")
        main_layout.addWidget(lbl_quick)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(10)

        actions = [
            ("📄 PDF Tools", "Merge, split, extract, compress, and encrypt PDFs", 1),
            ("📝 Document Editor", "Word DOCX editor with formatting and vector PDF export", 2),
            ("🖼️ Image Tools", "Resize, crop, and target-size (50KB/100KB) compression", 3),
            ("🔄 Converter", "Cross-format converter (PDF, DOCX, Images, Text)", 4),
            ("📦 Batch Processing", "Process multiple files simultaneously in background queue", 5),
            ("📜 Activity History", "Review previous operations and storage metrics", 6),
        ]

        for idx, (title, desc, page_idx) in enumerate(actions):
            row = idx // 3
            col = idx % 3
            btn_card = self._create_action_card(title, desc, page_idx)
            actions_grid.addWidget(btn_card, row, col)

        main_layout.addLayout(actions_grid)

        # Global Ingestion DropZone
        self.global_drop = DropZone(
            title="Drop any file to open in the appropriate tool",
            subtitle="Drop a PDF, Word document, or image to open it directly",
            file_filter="All Supported Files (*.pdf *.docx *.png *.jpg *.jpeg *.webp *.bmp *.tiff)",
            multi_select=False
        )
        self.global_drop.files_dropped.connect(self._on_file_dropped)
        main_layout.addWidget(self.global_drop)

        # Recent Files Section
        recents_header = QHBoxLayout()
        lbl_recents_title = QLabel("Recent Files")
        lbl_recents_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #60a5fa;")
        recents_header.addWidget(lbl_recents_title)
        recents_header.addStretch()

        btn_clear_recents = QPushButton("Clear Recents")
        btn_clear_recents.setProperty("class", "dangerButton")
        btn_clear_recents.clicked.connect(self._clear_recent_files)
        recents_header.addWidget(btn_clear_recents)
        main_layout.addLayout(recents_header)

        # Recent Files Table
        self.table_recents = QTableWidget(0, 4)
        self.table_recents.setHorizontalHeaderLabels(["File Name", "Type", "Size", "Actions"])
        self.table_recents.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_recents.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        main_layout.addWidget(self.table_recents, stretch=1)

        self.refresh_dashboard()

    def _create_action_card(self, title: str, desc: str, target_page: int) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("class", "cardFrame")
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                background-color: #202227;
                border: 1px solid #2c2f37;
                border-radius: 8px;
            }
            QPushButton:hover {
                border-color: #3b82f6;
                background-color: #262930;
            }
        """)

        lay = QVBoxLayout(btn)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 600; color: #60a5fa; background: transparent;")
        lbl_d = QLabel(desc)
        lbl_d.setWordWrap(True)
        lbl_d.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_d)

        btn.clicked.connect(lambda: self.navigate_requested.emit(target_page))
        return btn

    def refresh_dashboard(self) -> None:
        """Reload recent files table."""
        recents = self.db.get_recent_files(limit=30)
        self.table_recents.setRowCount(len(recents))
        for row, rec in enumerate(recents):
            p = Path(rec["file_path"])
            item_name = QTableWidgetItem(rec["file_name"])
            item_name.setToolTip(rec["file_path"])
            item_type = QTableWidgetItem(rec["file_type"].upper())
            item_size = QTableWidgetItem(format_file_size(rec["file_size"]))

            self.table_recents.setItem(row, 0, item_name)
            self.table_recents.setItem(row, 1, item_type)
            self.table_recents.setItem(row, 2, item_size)

            # Actions cell: Open + Reveal buttons
            action_widget = QWidget()
            a_lay = QHBoxLayout(action_widget)
            a_lay.setContentsMargins(4, 2, 4, 2)
            a_lay.setSpacing(6)

            btn_open = QPushButton("Open")
            btn_open.setProperty("class", "primaryButton")
            btn_open.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            btn_open.clicked.connect(lambda chk=False, path=rec["file_path"], t=rec["file_type"]: self._open_file(path, t))
            a_lay.addWidget(btn_open)

            btn_reveal = QPushButton("Reveal")
            btn_reveal.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn_reveal.clicked.connect(lambda chk=False, path=rec["file_path"]: self._reveal_in_explorer(path))
            a_lay.addWidget(btn_reveal)

            self.table_recents.setCellWidget(row, 3, action_widget)

    def _open_file(self, file_path: str, file_type: str) -> None:
        p = Path(file_path)
        if not p.exists():
            QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{file_path}")
            return
        self.file_open_requested.emit(file_path, file_type)

    def _reveal_in_explorer(self, file_path: str) -> None:
        p = Path(file_path)
        if p.exists():
            subprocess.run(["explorer", f"/select,{str(p.resolve())}"])
        else:
            QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{file_path}")

    def _on_file_dropped(self, files: list) -> None:
        if files:
            p = Path(files[0])
            ftype = get_file_type(p)
            self._open_file(str(p), ftype)

    def _clear_recent_files(self) -> None:
        self.db.clear_recent_files()
        self.refresh_dashboard()
