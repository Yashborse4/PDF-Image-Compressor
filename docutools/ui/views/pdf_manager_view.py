"""
PDF Manager View for DocuTools.
Features:
- Visual Page Organizer: Thumbnail grid, drag-style reordering, rotating, deleting, extracting
- PDF Merge: Combine multiple PDFs
- PDF Split: Split by ranges or every N pages
- PDF Compress: Deep pikepdf stream compression with before/after size stats
- PDF Protect: AES password encryption
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.pdf_engine import PDFEngine
from docutools.core.validator import format_file_size, validate_file
from docutools.ui.components.drop_zone import DropZone
from docutools.ui.components.progress_card import ProgressCard
from docutools.ui.components.thumbnail_card import ThumbnailCard
from docutools.workers.task_worker import TaskWorker


class PDFManagerView(QWidget):
    """Integrated PDF Manager module view."""

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool

        self.current_pdf_path: Optional[str] = None
        self.pages_data: List[Dict[str, Any]] = []  # [{orig_index: int, rotation: int, pixmap_bytes: bytes}]
        self.thumbnail_widgets: List[ThumbnailCard] = []
        self.merge_file_list: List[str] = []
        self.editor_current_page: int = 0
        self.editor_zoom: float = 1.2
        self.editor_total_pages: int = 0

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("PDF Manager")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Organize, merge, split, compress, and secure your PDF documents.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.btn_open_pdf = QPushButton("📂 Open PDF File...")
        self.btn_open_pdf.setProperty("class", "primaryButton")
        self.btn_open_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_pdf.clicked.connect(self._select_pdf_dialog)
        header_row.addWidget(self.btn_open_pdf)

        main_layout.addLayout(header_row)

        # Progress Card
        self.progress_card = ProgressCard()
        main_layout.addWidget(self.progress_card)

        # Tab Widget for Operations
        self.tabs = QTabWidget()
        self.tab_organize = QWidget()
        self.tab_merge = QWidget()
        self.tab_split = QWidget()
        self.tab_compress = QWidget()
        self.tab_protect = QWidget()
        self.tab_annotate = QWidget()
        self.tab_editor = QWidget()

        self.tabs.addTab(self.tab_organize, "📑 Page Organizer & Extraction")
        self.tabs.addTab(self.tab_merge, "🔗 Merge PDFs")
        self.tabs.addTab(self.tab_split, "✂️ Split PDF")
        self.tabs.addTab(self.tab_compress, "📉 Compress PDF")
        self.tabs.addTab(self.tab_protect, "🔒 Password & Protection")
        self.tabs.addTab(self.tab_annotate, "🖋️ Annotations & Watermarks")
        self.tabs.addTab(self.tab_editor, "✏️ Advanced PDF Editor")

        main_layout.addWidget(self.tabs, stretch=1)

        self._build_organizer_tab()
        self._build_merge_tab()
        self._build_split_tab()
        self._build_compress_tab()
        self._build_protect_tab()
        self._build_annotate_tab()
        self._build_editor_tab()

    # --- TAB 1: Visual Page Organizer ---
    def _build_organizer_tab(self) -> None:
        layout = QVBoxLayout(self.tab_organize)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Drop Zone & Document Stats Bar
        self.organizer_drop = DropZone(
            title="Drop PDF to view thumbnails and reorder pages",
            subtitle="View pages visually, rotate, delete, or extract selected pages",
            file_filter="PDF Files (*.pdf)",
            multi_select=False
        )
        self.organizer_drop.files_dropped.connect(lambda files: self.load_pdf(files[0]))
        layout.addWidget(self.organizer_drop)

        # Action Toolbar (shown when PDF loaded)
        self.organizer_toolbar = QFrame()
        self.organizer_toolbar.setProperty("class", "cardFrame")
        tb_layout = QHBoxLayout(self.organizer_toolbar)
        tb_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_pdf_info = QLabel("No document loaded")
        self.lbl_pdf_info.setStyleSheet("font-weight: 600; color: #60a5fa;")
        tb_layout.addWidget(self.lbl_pdf_info)

        tb_layout.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self._select_all_pages)
        tb_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self._deselect_all_pages)
        tb_layout.addWidget(self.btn_deselect_all)

        self.btn_rotate_all = QPushButton("⟳ Rotate All 90°")
        self.btn_rotate_all.clicked.connect(self._rotate_all_pages)
        tb_layout.addWidget(self.btn_rotate_all)

        self.btn_extract_selected = QPushButton("Extract Selected Pages...")
        self.btn_extract_selected.setProperty("class", "primaryButton")
        self.btn_extract_selected.clicked.connect(self._extract_selected_pages)
        tb_layout.addWidget(self.btn_extract_selected)

        self.btn_save_reordered = QPushButton("💾 Save Reordered PDF...")
        self.btn_save_reordered.setProperty("class", "successButton")
        self.btn_save_reordered.clicked.connect(self._save_reordered_pdf)
        tb_layout.addWidget(self.btn_save_reordered)

        self.organizer_toolbar.hide()
        layout.addWidget(self.organizer_toolbar)

        # Scroll Area with Thumbnail Grid
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_container = QWidget()
        self.thumbnail_grid = QGridLayout(self.thumbnail_container)
        self.thumbnail_grid.setSpacing(14)
        self.thumbnail_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.thumbnail_scroll.setWidget(self.thumbnail_container)
        self.thumbnail_scroll.hide()
        layout.addWidget(self.thumbnail_scroll, stretch=1)

    # --- TAB 2: Merge Tab ---
    def _build_merge_tab(self) -> None:
        layout = QVBoxLayout(self.tab_merge)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Drop Zone for multiple PDFs
        drop_merge = DropZone(
            title="Drop multiple PDFs here to merge",
            subtitle="Add all files you want to combine into a single PDF",
            file_filter="PDF Files (*.pdf)",
            multi_select=True
        )
        drop_merge.files_dropped.connect(self._add_files_to_merge_list)
        layout.addWidget(drop_merge)

        # Table of files to merge
        self.table_merge = QTableWidget(0, 4)
        self.table_merge.setHorizontalHeaderLabels(["Order", "File Name", "Size", "Path"])
        self.table_merge.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_merge.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_merge, stretch=1)

        # Controls row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_move_up = QPushButton("▲ Move Up")
        btn_move_up.clicked.connect(self._merge_move_up)
        btn_row.addWidget(btn_move_up)

        btn_move_down = QPushButton("▼ Move Down")
        btn_move_down.clicked.connect(self._merge_move_down)
        btn_row.addWidget(btn_move_down)

        btn_remove = QPushButton("Remove Selected")
        btn_remove.setProperty("class", "dangerButton")
        btn_remove.clicked.connect(self._merge_remove_file)
        btn_row.addWidget(btn_remove)

        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._merge_clear)
        btn_row.addWidget(btn_clear)

        btn_row.addStretch()

        self.btn_run_merge = QPushButton("🔗 Merge into Single PDF...")
        self.btn_run_merge.setProperty("class", "primaryButton")
        self.btn_run_merge.clicked.connect(self._execute_merge)
        btn_row.addWidget(self.btn_run_merge)

        layout.addLayout(btn_row)

    # --- TAB 3: Split Tab ---
    def _build_split_tab(self) -> None:
        layout = QVBoxLayout(self.tab_split)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        lbl_info = QLabel("Split Options for Current or Selected Document")
        lbl_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        card_layout.addWidget(lbl_info)

        # Option A: Split by ranges
        grp_range = QGroupBox("Mode A: Split by Page Ranges")
        lay_range = QVBoxLayout(grp_range)
        lbl_hint = QLabel("Enter ranges separated by commas (e.g. '1-3, 5, 8-10'):")
        lbl_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.txt_ranges = QLineEdit("1-2, 3-4")
        lay_range.addWidget(lbl_hint)
        lay_range.addWidget(self.txt_ranges)
        self.btn_split_ranges = QPushButton("Split by Defined Ranges...")
        self.btn_split_ranges.setProperty("class", "primaryButton")
        self.btn_split_ranges.clicked.connect(self._execute_split_ranges)
        lay_range.addWidget(self.btn_split_ranges)
        card_layout.addWidget(grp_range)

        # Option B: Split into individual pages or fixed chunks
        grp_chunk = QGroupBox("Mode B: Split Every N Pages")
        lay_chunk = QHBoxLayout(grp_chunk)
        lay_chunk.addWidget(QLabel("Pages per split file:"))
        self.spin_chunk_size = QSpinBox()
        self.spin_chunk_size.setRange(1, 500)
        self.spin_chunk_size.setValue(1)
        lay_chunk.addWidget(self.spin_chunk_size)
        lay_chunk.addStretch()
        self.btn_split_chunks = QPushButton("Split Every N Pages...")
        self.btn_split_chunks.setProperty("class", "primaryButton")
        self.btn_split_chunks.clicked.connect(self._execute_split_chunks)
        lay_chunk.addWidget(self.btn_split_chunks)
        card_layout.addWidget(grp_chunk)

        layout.addWidget(card)
        layout.addStretch()

    # --- TAB 4: Compress Tab ---
    def _build_compress_tab(self) -> None:
        layout = QVBoxLayout(self.tab_compress)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel("PDF Optimization & Compression")
        lbl_t.setStyleSheet("font-weight: bold; font-size: 14px;")
        c_layout.addWidget(lbl_t)

        lbl_desc = QLabel("Applies stream deflation, object streams, and optional embedded image downsampling.")
        lbl_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        c_layout.addWidget(lbl_desc)

        row_level = QHBoxLayout()
        row_level.addWidget(QLabel("Compression Profile:"))
        self.combo_compress_level = QComboBox()
        self.combo_compress_level.addItems(["Low (Fast / High Image Quality)", "Medium (Balanced Compression)", "High (Maximum Compression)"])
        self.combo_compress_level.setCurrentIndex(1)
        row_level.addWidget(self.combo_compress_level)
        row_level.addStretch()
        c_layout.addLayout(row_level)

        self.btn_run_compress = QPushButton("📉 Compress PDF Now...")
        self.btn_run_compress.setProperty("class", "primaryButton")
        self.btn_run_compress.clicked.connect(self._execute_compression)
        c_layout.addWidget(self.btn_run_compress)

        # Compression Statistics Box
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("background-color: #17181c; border-radius: 6px; padding: 12px;")
        stats_layout = QVBoxLayout(self.stats_frame)
        self.lbl_stat_original = QLabel("Original Size: -")
        self.lbl_stat_compressed = QLabel("Compressed Size: -")
        self.lbl_stat_savings = QLabel("Space Saved: -")
        self.lbl_stat_savings.setStyleSheet("font-weight: bold; color: #22c55e; font-size: 14px;")
        stats_layout.addWidget(self.lbl_stat_original)
        stats_layout.addWidget(self.lbl_stat_compressed)
        stats_layout.addWidget(self.lbl_stat_savings)
        c_layout.addWidget(self.stats_frame)

        layout.addWidget(card)
        layout.addStretch()

    # --- TAB 5: Protect Tab ---
    def _build_protect_tab(self) -> None:
        layout = QVBoxLayout(self.tab_protect)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel("Document Security & Password Encryption")
        lbl_t.setStyleSheet("font-weight: bold; font-size: 14px;")
        c_layout.addWidget(lbl_t)

        lbl_desc = QLabel("Encrypt PDF using AES-256 standard and restrict access or printing permissions.")
        lbl_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        c_layout.addWidget(lbl_desc)

        # Passwords
        c_layout.addWidget(QLabel("User Password (Required to Open):"))
        self.txt_protect_user_pwd = QLineEdit()
        self.txt_protect_user_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_protect_user_pwd.setPlaceholderText("Enter password to open PDF")
        c_layout.addWidget(self.txt_protect_user_pwd)

        c_layout.addWidget(QLabel("Owner Password (Optional, for permissions):"))
        self.txt_protect_owner_pwd = QLineEdit()
        self.txt_protect_owner_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_protect_owner_pwd.setPlaceholderText("Enter owner password to modify security")
        c_layout.addWidget(self.txt_protect_owner_pwd)

        self.chk_allow_print = QCheckBox("Allow Printing")
        self.chk_allow_print.setChecked(True)
        c_layout.addWidget(self.chk_allow_print)

        self.chk_allow_copy = QCheckBox("Allow Copying Content")
        self.chk_allow_copy.setChecked(True)
        c_layout.addWidget(self.chk_allow_copy)

        self.btn_run_protect = QPushButton("🔒 Apply Encryption & Save...")
        self.btn_run_protect.setProperty("class", "primaryButton")
        self.btn_run_protect.clicked.connect(self._execute_protect)
        c_layout.addWidget(self.btn_run_protect)

        layout.addWidget(card)
        layout.addStretch()

    # --- TAB 6: Annotate Tab ---
    def _build_annotate_tab(self) -> None:
        layout = QVBoxLayout(self.tab_annotate)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel("PDF Annotations, Stamps & Watermarks")
        lbl_t.setStyleSheet("font-weight: bold; font-size: 14px;")
        c_layout.addWidget(lbl_t)

        lbl_desc = QLabel("Stamp documents with approval tags, security watermarks, headers, or footers.")
        lbl_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        c_layout.addWidget(lbl_desc)

        # Text input
        c_layout.addWidget(QLabel("Watermark / Stamp Text:"))
        self.txt_annotate_text = QLineEdit("CONFIDENTIAL")
        c_layout.addWidget(self.txt_annotate_text)

        # Quick preset buttons
        preset_row = QHBoxLayout()
        for p_tag in ["CONFIDENTIAL", "APPROVED", "DRAFT", "FINAL", "COPY"]:
            btn_tag = QPushButton(p_tag)
            btn_tag.clicked.connect(lambda chk=False, t=p_tag: self.txt_annotate_text.setText(t))
            preset_row.addWidget(btn_tag)
        c_layout.addLayout(preset_row)

        # Type combo
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("Placement Style:"))
        self.combo_annotate_type = QComboBox()
        self.combo_annotate_type.addItems(["Diagonal Watermark", "Corner Stamp", "Top Header", "Bottom Footer"])
        row_type.addWidget(self.combo_annotate_type)

        row_type.addWidget(QLabel("Font Size:"))
        self.spin_annotate_size = QSpinBox()
        self.spin_annotate_size.setRange(10, 100)
        self.spin_annotate_size.setValue(36)
        row_type.addWidget(self.spin_annotate_size)

        row_type.addWidget(QLabel("Opacity (%):"))
        self.spin_annotate_opacity = QSpinBox()
        self.spin_annotate_opacity.setRange(5, 100)
        self.spin_annotate_opacity.setValue(35)
        row_type.addWidget(self.spin_annotate_opacity)
        c_layout.addLayout(row_type)

        self.btn_run_annotate = QPushButton("🖋️ Apply Annotation & Save...")
        self.btn_run_annotate.setProperty("class", "primaryButton")
        self.btn_run_annotate.clicked.connect(self._execute_annotate)
        c_layout.addWidget(self.btn_run_annotate)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_annotate(self) -> None:
        if not self.current_pdf_path:
            self._select_pdf_dialog()
            if not self.current_pdf_path:
                return

        text = self.txt_annotate_text.text().strip()
        if not text:
            QMessageBox.warning(self, "Text Required", "Please enter annotation or watermark text.")
            return

        type_map = {0: "watermark", 1: "stamp", 2: "header", 3: "footer"}
        ann_type = type_map.get(self.combo_annotate_type.currentIndex(), "watermark")
        font_size = self.spin_annotate_size.value()
        opacity = self.spin_annotate_opacity.value() / 100.0

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Annotated PDF", "annotated_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Applying Annotation to PDF...")
        worker = TaskWorker(
            PDFEngine.add_annotation,
            file_path=self.current_pdf_path,
            output_path=out_path,
            annotation_type=ann_type,
            text=text,
            font_size=font_size,
            opacity=opacity
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done("Annotated PDF", f"Annotation applied to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Annotation Failed", err))
        self.thread_pool.start(worker)

    # --- TAB 7: Advanced PDF Editor ---
    def _build_editor_tab(self) -> None:
        layout = QVBoxLayout(self.tab_editor)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Editor Header Controls
        header_frame = QFrame()
        header_frame.setProperty("class", "cardFrame")
        h_lay = QHBoxLayout(header_frame)
        h_lay.setContentsMargins(8, 6, 8, 6)
        h_lay.setSpacing(8)

        # Page Nav
        self.btn_ed_prev = QPushButton("◀ Prev")
        self.btn_ed_prev.clicked.connect(self._editor_prev_page)
        h_lay.addWidget(self.btn_ed_prev)

        self.lbl_ed_page = QLabel("Page 1 of 1")
        self.lbl_ed_page.setStyleSheet("font-weight: 600; color: #60a5fa;")
        h_lay.addWidget(self.lbl_ed_page)

        self.btn_ed_next = QPushButton("Next ▶")
        self.btn_ed_next.clicked.connect(self._editor_next_page)
        h_lay.addWidget(self.btn_ed_next)

        h_lay.addSpacing(16)

        # Zoom
        btn_zoom_in = QPushButton("🔍 Zoom In (+)")
        btn_zoom_in.clicked.connect(self._editor_zoom_in)
        h_lay.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍 Zoom Out (-)")
        btn_zoom_out.clicked.connect(self._editor_zoom_out)
        h_lay.addWidget(btn_zoom_out)

        self.lbl_zoom_val = QLabel("120%")
        self.lbl_zoom_val.setStyleSheet("color: #9ca3af; font-size: 11px;")
        h_lay.addWidget(self.lbl_zoom_val)

        h_lay.addStretch()

        self.btn_reload_page = QPushButton("🔄 Reload")
        self.btn_reload_page.clicked.connect(self._refresh_editor_canvas)
        h_lay.addWidget(self.btn_reload_page)

        layout.addWidget(header_frame)

        # Tools Sub-Tabs (Search/Redact, Insert Text, Insert Image, Highlight)
        tools_tab = QTabWidget()
        tools_tab.setFixedHeight(120)

        # Sub-Tab 1: Redaction & Text Replacement
        tab_redact = QWidget()
        r_lay = QHBoxLayout(tab_redact)
        r_lay.setContentsMargins(8, 6, 8, 6)
        r_lay.addWidget(QLabel("Find Text:"))
        self.txt_ed_search = QLineEdit()
        self.txt_ed_search.setPlaceholderText("Word or phrase to find/redact")
        r_lay.addWidget(self.txt_ed_search)

        r_lay.addWidget(QLabel("Replace With (optional):"))
        self.txt_ed_replace = QLineEdit()
        self.txt_ed_replace.setPlaceholderText("Leave empty to blackout redact")
        r_lay.addWidget(self.txt_ed_replace)

        btn_exec_redact = QPushButton("⬛ Apply Redaction / Replace...")
        btn_exec_redact.setProperty("class", "primaryButton")
        btn_exec_redact.clicked.connect(self._execute_redact_replace)
        r_lay.addWidget(btn_exec_redact)
        tools_tab.addTab(tab_redact, "⬛ Redact & Replace Text")

        # Sub-Tab 2: Insert Text Box
        tab_text = QWidget()
        t_lay = QHBoxLayout(tab_text)
        t_lay.setContentsMargins(8, 6, 8, 6)
        t_lay.addWidget(QLabel("Text:"))
        self.txt_ed_insert = QLineEdit("Sample Text")
        t_lay.addWidget(self.txt_ed_insert)

        t_lay.addWidget(QLabel("X:"))
        self.spin_ed_x = QSpinBox()
        self.spin_ed_x.setRange(0, 3000)
        self.spin_ed_x.setValue(80)
        t_lay.addWidget(self.spin_ed_x)

        t_lay.addWidget(QLabel("Y:"))
        self.spin_ed_y = QSpinBox()
        self.spin_ed_y.setRange(0, 3000)
        self.spin_ed_y.setValue(120)
        t_lay.addWidget(self.spin_ed_y)

        t_lay.addWidget(QLabel("Size:"))
        self.spin_ed_fsize = QSpinBox()
        self.spin_ed_fsize.setRange(8, 72)
        self.spin_ed_fsize.setValue(14)
        t_lay.addWidget(self.spin_ed_fsize)

        btn_exec_insert = QPushButton("🔤 Insert Text on Page...")
        btn_exec_insert.setProperty("class", "primaryButton")
        btn_exec_insert.clicked.connect(self._execute_insert_text)
        t_lay.addWidget(btn_exec_insert)
        tools_tab.addTab(tab_text, "🔤 Insert Text Box")

        # Sub-Tab 3: Insert Image / Stamp
        tab_img = QWidget()
        im_lay = QHBoxLayout(tab_img)
        im_lay.setContentsMargins(8, 6, 8, 6)
        self.btn_choose_stamp = QPushButton("Choose Image / Stamp...")
        self.btn_choose_stamp.clicked.connect(self._choose_stamp_image)
        im_lay.addWidget(self.btn_choose_stamp)

        self.lbl_stamp_path = QLabel("No image selected")
        self.lbl_stamp_path.setStyleSheet("color: #9ca3af; font-size: 11px;")
        im_lay.addWidget(self.lbl_stamp_path)

        im_lay.addWidget(QLabel("Width:"))
        self.spin_stamp_w = QSpinBox()
        self.spin_stamp_w.setRange(20, 1000)
        self.spin_stamp_w.setValue(160)
        im_lay.addWidget(self.spin_stamp_w)

        im_lay.addWidget(QLabel("Height:"))
        self.spin_stamp_h = QSpinBox()
        self.spin_stamp_h.setRange(20, 1000)
        self.spin_stamp_h.setValue(80)
        im_lay.addWidget(self.spin_stamp_h)

        btn_exec_stamp = QPushButton("🖼 Place Image on Page...")
        btn_exec_stamp.setProperty("class", "primaryButton")
        btn_exec_stamp.clicked.connect(self._execute_insert_image)
        im_lay.addWidget(btn_exec_stamp)
        tools_tab.addTab(tab_img, "🖼 Place Image / Signature Stamp")

        layout.addWidget(tools_tab)

        # Interactive High-Res Canvas Scroll Area
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_canvas_container = QWidget()
        c_vlay = QVBoxLayout(self.editor_canvas_container)
        c_vlay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.editor_canvas_lbl = QLabel()
        self.editor_canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor_canvas_lbl.setStyleSheet("background-color: #111215; border: 1px solid #282a30; border-radius: 4px;")
        self.editor_canvas_lbl.mousePressEvent = self._on_canvas_clicked
        c_vlay.addWidget(self.editor_canvas_lbl)

        self.editor_scroll.setWidget(self.editor_canvas_container)
        layout.addWidget(self.editor_scroll, stretch=1)

    def _choose_stamp_image(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select Image or Signature Stamp", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            self.lbl_stamp_path.setText(Path(p).name)
            self.lbl_stamp_path.setToolTip(p)

    def _on_canvas_clicked(self, event) -> None:
        # Update X and Y spinboxes on click relative to canvas
        pos = event.pos()
        zoom = max(self.editor_zoom, 0.1)
        pdf_x = int(pos.x() / zoom)
        pdf_y = int(pos.y() / zoom)
        self.spin_ed_x.setValue(pdf_x)
        self.spin_ed_y.setValue(pdf_y)

    def _editor_prev_page(self) -> None:
        if self.editor_current_page > 0:
            self.editor_current_page -= 1
            self._refresh_editor_canvas()

    def _editor_next_page(self) -> None:
        if self.editor_current_page < self.editor_total_pages - 1:
            self.editor_current_page += 1
            self._refresh_editor_canvas()

    def _editor_zoom_in(self) -> None:
        self.editor_zoom = min(3.0, self.editor_zoom + 0.2)
        self.lbl_zoom_val.setText(f"{int(self.editor_zoom * 100)}%")
        self._refresh_editor_canvas()

    def _editor_zoom_out(self) -> None:
        self.editor_zoom = max(0.5, self.editor_zoom - 0.2)
        self.lbl_zoom_val.setText(f"{int(self.editor_zoom * 100)}%")
        self._refresh_editor_canvas()

    def _refresh_editor_canvas(self) -> None:
        if not self.current_pdf_path or self.editor_total_pages == 0:
            self.editor_canvas_lbl.setText("Open a PDF file to view and edit pages.")
            return

        self.lbl_ed_page.setText(f"Page {self.editor_current_page + 1} of {self.editor_total_pages}")

        try:
            png_bytes = PDFEngine.render_page_hires(
                self.current_pdf_path,
                self.editor_current_page,
                zoom=self.editor_zoom
            )
            px = QPixmap()
            px.loadFromData(png_bytes)
            self.editor_canvas_lbl.setPixmap(px)
        except Exception as e:
            self.editor_canvas_lbl.setText(f"Error rendering page: {e}")

    def _execute_redact_replace(self) -> None:
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please open a PDF document first.")
            return

        search_term = self.txt_ed_search.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Search Term Required", "Please enter a word or phrase to find.")
            return

        replace_text = self.txt_ed_replace.text().strip() or None

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Redacted/Modified PDF", "edited_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Applying In-Place Redactions / Replacements...")
        worker = TaskWorker(
            PDFEngine.redact_and_replace_text,
            file_path=self.current_pdf_path,
            output_path=out_path,
            search_term=search_term,
            replacement_text=replace_text
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done(
            "Redaction Complete",
            f"Successfully redacted/replaced {res['occurrences_redacted']} occurrences and saved to {res['output_file']}",
            res['output_file']
        ))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Redaction Failed", err))
        self.thread_pool.start(worker)

    def _execute_insert_text(self) -> None:
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please open a PDF document first.")
            return

        text = self.txt_ed_insert.text().strip()
        if not text:
            return

        x = self.spin_ed_x.value()
        y = self.spin_ed_y.value()
        fsize = self.spin_ed_fsize.value()

        out_path, _ = QFileDialog.getSaveFileName(self, "Save PDF with Inserted Text", "edited_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        item = {
            "type": "text",
            "rect": (x, y, x + 350, y + 80),
            "text": text,
            "fontsize": fsize,
            "color": (0, 0, 0)
        }

        self.progress_card.start_task("Inserting Text on Page...")
        worker = TaskWorker(
            PDFEngine.insert_content_on_page,
            file_path=self.current_pdf_path,
            output_path=out_path,
            page_index=self.editor_current_page,
            items=[item]
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done("Text Inserted", f"Saved modified PDF to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Insert Failed", err))
        self.thread_pool.start(worker)

    def _execute_insert_image(self) -> None:
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please open a PDF document first.")
            return

        img_p = self.lbl_stamp_path.toolTip()
        if not img_p or not Path(img_p).exists():
            QMessageBox.warning(self, "No Image Selected", "Please choose an image or stamp file first.")
            return

        x = self.spin_ed_x.value()
        y = self.spin_ed_y.value()
        w = self.spin_stamp_w.value()
        h = self.spin_stamp_h.value()

        out_path, _ = QFileDialog.getSaveFileName(self, "Save PDF with Stamp", "stamped_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        item = {
            "type": "image",
            "rect": (x, y, x + w, y + h),
            "image_path": img_p
        }

        self.progress_card.start_task("Placing Image on Page...")
        worker = TaskWorker(
            PDFEngine.insert_content_on_page,
            file_path=self.current_pdf_path,
            output_path=out_path,
            page_index=self.editor_current_page,
            items=[item]
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done("Image Placed", f"Saved stamped PDF to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Placement Failed", err))
        self.thread_pool.start(worker)

    # --- Actions & Handlers ---
    def _select_pdf_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF Document", "", "PDF Files (*.pdf)")
        if file_path:
            self.load_pdf(file_path)

    def load_pdf(self, file_path: str) -> None:
        is_valid, msg = validate_file(file_path, expected_type="pdf")
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", msg)
            return

        self.current_pdf_path = file_path
        self.db.add_recent_file(file_path, file_type="pdf")

        # Load thumbnails asynchronously
        self.progress_card.start_task("Rendering Page Thumbnails...")
        self.organizer_drop.hide()

        def load_worker(progress_callback=None):
            info = PDFEngine.get_document_info(file_path)
            total_pages = info["page_count"]
            pages = []
            for i in range(total_pages):
                if progress_callback:
                    pct = int(((i + 1) / max(total_pages, 1)) * 100)
                    progress_callback(pct, f"Rendering page {i+1}/{total_pages}...")
                png_bytes = PDFEngine.render_page_thumbnail(file_path, i, target_width=180)
                pages.append({"orig_index": i, "rotation": 0, "pixmap_bytes": png_bytes})
            return info, pages

        worker = TaskWorker(load_worker)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(self._on_pdf_loaded)
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Failed to load PDF", err))
        self.thread_pool.start(worker)

    def _on_pdf_loaded(self, result: tuple) -> None:
        info, pages = result
        self.pages_data = pages
        self.editor_total_pages = info["page_count"]
        self.editor_current_page = 0
        self.lbl_pdf_info.setText(f"{info['file_name']} — {info['page_count']} pages ({format_file_size(info['file_size'])})")
        self.organizer_toolbar.show()
        self.thumbnail_scroll.show()
        self.progress_card.complete_task("Loaded document successfully.")
        self.progress_card.hide()
        self._refresh_thumbnail_grid()
        self._refresh_editor_canvas()

    def _refresh_thumbnail_grid(self) -> None:
        # Clear existing
        for w in self.thumbnail_widgets:
            w.setParent(None)
            w.deleteLater()
        self.thumbnail_widgets.clear()

        cols = 4  # 4 cards per row
        for i, item in enumerate(self.pages_data):
            row = i // cols
            col = i % cols
            card = ThumbnailCard(
                page_index=i,
                page_number=i + 1,
                pixmap_bytes=item["pixmap_bytes"]
            )
            card.rotate_requested.connect(self._on_card_rotate)
            card.delete_requested.connect(self._on_card_delete)
            card.move_left_requested.connect(self._on_card_move_left)
            card.move_right_requested.connect(self._on_card_move_right)

            self.thumbnail_grid.addWidget(card, row, col)
            self.thumbnail_widgets.append(card)

    def _on_card_rotate(self, index: int) -> None:
        if 0 <= index < len(self.pages_data):
            self.pages_data[index]["rotation"] = (self.pages_data[index]["rotation"] + 90) % 360
            # Rotate pixmap locally
            px = QPixmap()
            px.loadFromData(self.pages_data[index]["pixmap_bytes"])
            transform = px.transformed(px.trueMatrix(px.createHeuristicMask(), 90))
            # Store rotated bytes
            buf = px.toImage()
            # Reload thumbnail
            self.thumbnail_widgets[index].lbl_image.setPixmap(
                self.thumbnail_widgets[index].lbl_image.pixmap().transformed(
                    self.thumbnail_widgets[index].lbl_image.pixmap().trueMatrix(
                        self.thumbnail_widgets[index].lbl_image.pixmap().createHeuristicMask(), 90
                    )
                )
            )

    def _on_card_delete(self, index: int) -> None:
        if len(self.pages_data) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete all pages in document.")
            return
        del self.pages_data[index]
        self._refresh_thumbnail_grid()

    def _on_card_move_left(self, index: int) -> None:
        if index > 0:
            self.pages_data[index - 1], self.pages_data[index] = self.pages_data[index], self.pages_data[index - 1]
            self._refresh_thumbnail_grid()

    def _on_card_move_right(self, index: int) -> None:
        if index < len(self.pages_data) - 1:
            self.pages_data[index + 1], self.pages_data[index] = self.pages_data[index], self.pages_data[index + 1]
            self._refresh_thumbnail_grid()

    def _select_all_pages(self) -> None:
        for w in self.thumbnail_widgets:
            w.set_selected(True)

    def _deselect_all_pages(self) -> None:
        for w in self.thumbnail_widgets:
            w.set_selected(False)

    def _rotate_all_pages(self) -> None:
        for i in range(len(self.pages_data)):
            self.pages_data[i]["rotation"] = (self.pages_data[i]["rotation"] + 90) % 360
        self._refresh_thumbnail_grid()

    def _extract_selected_pages(self) -> None:
        if not self.current_pdf_path:
            return
        selected_indices = [
            self.pages_data[i]["orig_index"]
            for i, w in enumerate(self.thumbnail_widgets)
            if w.is_selected()
        ]
        if not selected_indices:
            QMessageBox.information(self, "Extraction", "Please select at least one page using the checkboxes.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Extracted Pages", "extracted_pages.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Extracting Selected Pages...")
        worker = TaskWorker(PDFEngine.extract_pages, self.current_pdf_path, selected_indices, out_path)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda res: self._on_operation_done("Extraction Complete", f"Saved to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Extraction Failed", err))
        self.thread_pool.start(worker)

    def _save_reordered_pdf(self) -> None:
        if not self.current_pdf_path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Reordered PDF", "reordered_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        order = [item["orig_index"] for item in self.pages_data]
        rotations = {i: item["rotation"] for i, item in enumerate(self.pages_data) if item["rotation"] != 0}

        self.progress_card.start_task("Saving Reordered PDF...")
        worker = TaskWorker(PDFEngine.reorder_and_rotate_pages, self.current_pdf_path, order, rotations, out_path)
        worker.signals.finished.connect(lambda res: self._on_operation_done("Reorder Complete", f"Saved to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Reorder Failed", err))
        self.thread_pool.start(worker)

    # --- Merge Logic ---
    def _add_files_to_merge_list(self, files: List[str]) -> None:
        for f in files:
            p = Path(f)
            if p.suffix.lower() == ".pdf" and str(p) not in self.merge_file_list:
                self.merge_file_list.append(str(p))
        self._refresh_merge_table()

    def _refresh_merge_table(self) -> None:
        self.table_merge.setRowCount(len(self.merge_file_list))
        for row, path_str in enumerate(self.merge_file_list):
            p = Path(path_str)
            item_order = QTableWidgetItem(str(row + 1))
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_name = QTableWidgetItem(p.name)
            item_size = QTableWidgetItem(format_file_size(p.stat().st_size) if p.exists() else "0 B")
            item_path = QTableWidgetItem(str(p))

            self.table_merge.setItem(row, 0, item_order)
            self.table_merge.setItem(row, 1, item_name)
            self.table_merge.setItem(row, 2, item_size)
            self.table_merge.setItem(row, 3, item_path)

    def _merge_move_up(self) -> None:
        row = self.table_merge.currentRow()
        if row > 0:
            self.merge_file_list[row - 1], self.merge_file_list[row] = self.merge_file_list[row], self.merge_file_list[row - 1]
            self._refresh_merge_table()
            self.table_merge.selectRow(row - 1)

    def _merge_move_down(self) -> None:
        row = self.table_merge.currentRow()
        if 0 <= row < len(self.merge_file_list) - 1:
            self.merge_file_list[row + 1], self.merge_file_list[row] = self.merge_file_list[row], self.merge_file_list[row + 1]
            self._refresh_merge_table()
            self.table_merge.selectRow(row + 1)

    def _merge_remove_file(self) -> None:
        row = self.table_merge.currentRow()
        if 0 <= row < len(self.merge_file_list):
            del self.merge_file_list[row]
            self._refresh_merge_table()

    def _merge_clear(self) -> None:
        self.merge_file_list.clear()
        self._refresh_merge_table()

    def _execute_merge(self) -> None:
        if len(self.merge_file_list) < 2:
            QMessageBox.warning(self, "Merge Warning", "Please add at least 2 PDF files to merge.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF", "merged_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Merging PDF Documents...")
        worker = TaskWorker(PDFEngine.merge_pdfs, self.merge_file_list, out_path)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda res: self._on_operation_done("Merge Finished", f"Saved merged PDF to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Merge Failed", err))
        self.thread_pool.start(worker)

    # --- Split Logic ---
    def _execute_split_ranges(self) -> None:
        if not self.current_pdf_path:
            self._select_pdf_dialog()
            if not self.current_pdf_path:
                return

        ranges_str = self.txt_ranges.text().strip()
        if not ranges_str:
            QMessageBox.warning(self, "Input Error", "Please provide page ranges, e.g. '1-3, 5, 8-10'.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder for Split Files")
        if not out_dir:
            return

        self.progress_card.start_task("Splitting PDF by Ranges...")
        worker = TaskWorker(PDFEngine.split_pdf_by_ranges, self.current_pdf_path, ranges_str, out_dir)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda files: self._on_operation_done("Split Complete", f"Generated {len(files)} files in output directory."))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Split Failed", err))
        self.thread_pool.start(worker)

    def _execute_split_chunks(self) -> None:
        if not self.current_pdf_path:
            self._select_pdf_dialog()
            if not self.current_pdf_path:
                return

        chunk_size = self.spin_chunk_size.value()
        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder for Split Files")
        if not out_dir:
            return

        self.progress_card.start_task(f"Splitting PDF every {chunk_size} pages...")
        worker = TaskWorker(PDFEngine.split_pdf_pages, self.current_pdf_path, out_dir, chunk_size=chunk_size)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda files: self._on_operation_done("Split Complete", f"Generated {len(files)} files."))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Split Failed", err))
        self.thread_pool.start(worker)

    # --- Compress Logic ---
    def _execute_compression(self) -> None:
        if not self.current_pdf_path:
            self._select_pdf_dialog()
            if not self.current_pdf_path:
                return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Compressed PDF", "compressed_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        level_map = {0: "low", 1: "medium", 2: "high"}
        q_level = level_map.get(self.combo_compress_level.currentIndex(), "medium")

        self.progress_card.start_task("Optimizing and Compressing PDF...")
        worker = TaskWorker(PDFEngine.compress_pdf, self.current_pdf_path, out_path, quality_level=q_level)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(self._on_compression_finished)
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Compression Failed", err))
        self.thread_pool.start(worker)

    def _on_compression_finished(self, stats: Dict[str, Any]) -> None:
        self.lbl_stat_original.setText(f"Original Size: {format_file_size(stats['original_size'])}")
        self.lbl_stat_compressed.setText(f"Compressed Size: {format_file_size(stats['compressed_size'])}")
        self.lbl_stat_savings.setText(f"Space Saved: {format_file_size(stats['savings_bytes'])} ({stats['savings_percent']:.1f}% reduction)")
        self._on_operation_done("Compression Complete", f"File compressed successfully! Saved {stats['savings_percent']:.1f}%.", stats["file_path"])

    # --- Protect Logic ---
    def _execute_protect(self) -> None:
        if not self.current_pdf_path:
            self._select_pdf_dialog()
            if not self.current_pdf_path:
                return

        pwd = self.txt_protect_user_pwd.text().strip()
        if not pwd:
            QMessageBox.warning(self, "Password Required", "Please enter a user password to protect the document.")
            return

        owner_pwd = self.txt_protect_owner_pwd.text().strip() or None
        allow_print = self.chk_allow_print.isChecked()
        allow_copy = self.chk_allow_copy.isChecked()

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Protected PDF", "protected_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Applying AES-256 Encryption...")
        worker = TaskWorker(
            PDFEngine.protect_pdf,
            self.current_pdf_path,
            out_path,
            user_password=pwd,
            owner_password=owner_pwd,
            allow_printing=allow_print,
            allow_copying=allow_copy
        )
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda res: self._on_operation_done("Protected", "Document encrypted with AES-256 password.", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Protection Failed", err))
        self.thread_pool.start(worker)

    def _on_operation_done(self, title: str, message: str, file_path: Optional[str] = None) -> None:
        self.progress_card.complete_task(message)
        if file_path:
            self.db.add_recent_file(file_path, "pdf")
        self.db.log_operation("PDF Manager", title, output_file=file_path, status="success")
        QMessageBox.information(self, title, message)

    def _on_worker_error(self, title: str, error_msg: str) -> None:
        self.progress_card.fail_task(error_msg)
        self.db.log_operation("PDF Manager", title, status="error", error_message=error_msg)
        QMessageBox.critical(self, title, f"An error occurred:\n{error_msg}")
