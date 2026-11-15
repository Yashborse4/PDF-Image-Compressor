"""
All-in-One PDF Studio & Manager View for DocuTools.
Unified Single-Window PDF Workbench:
- Merge multiple PDFs into a single workspace
- Remove unneeded pages instantly (individual ✕ or bulk selection)
- Reorder and rotate pages visually with high-res thumbnails
- Large Page Inspector with zoom, selection, and rotation
- One-click Ready & Export with built-in compression, password protection, and watermarking
- All in the same window for rapid PDF assembly
- Additional sub-tabs for in-place text replacement/redaction and batch splitting
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.pdf_engine import PDFEngine
from docutools.core.validator import format_file_size, validate_file
from docutools.ui.components.drop_zone import DropZone
from docutools.ui.components.page_preview_dialog import PagePreviewDialog
from docutools.ui.components.progress_card import ProgressCard
from docutools.ui.components.thumbnail_card import ThumbnailCard
from docutools.workers.task_worker import TaskWorker

DOC_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]


class PDFManagerView(QWidget):
    """Integrated All-in-One PDF Studio and processing module."""

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool

        self.loaded_documents: List[Dict[str, Any]] = []
        self.pages_data: List[Dict[str, Any]] = []
        self.thumbnail_widgets: List[ThumbnailCard] = []

        self.thumbnail_card_w: int = 180
        self.thumbnail_card_h: int = 255

        # Advanced Editor state
        self.editor_current_page: int = 0
        self.editor_zoom: float = 1.2
        self.editor_total_pages: int = 0

        self._init_ui()

    @property
    def current_pdf_path(self) -> Optional[str]:
        if self.loaded_documents:
            return self.loaded_documents[0]["file_path"]
        return None

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("PDF Studio & Manager")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Combine multiple PDFs, remove unneeded pages, reorder, compress, and protect — all in one window.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.btn_open_pdf = QPushButton("➕ Add PDF(s)...")
        self.btn_open_pdf.setProperty("class", "primaryButton")
        self.btn_open_pdf.setStyleSheet("font-weight: 600; padding: 6px 14px;")
        self.btn_open_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_pdf.clicked.connect(self._select_multiple_pdfs_dialog)
        header_row.addWidget(self.btn_open_pdf)

        main_layout.addLayout(header_row)

        # Global Progress Card
        self.progress_card = ProgressCard()
        main_layout.addWidget(self.progress_card)

        # Main Navigation Tabs
        self.tabs = QTabWidget()
        self.tab_studio = QWidget()
        self.tab_editor = QWidget()
        self.tab_split = QWidget()

        self.tabs.addTab(self.tab_studio, "📑 All-in-One Studio")
        self.tabs.addTab(self.tab_editor, "✏️ In-Place Content Editor")
        self.tabs.addTab(self.tab_split, "✂️ Split Document")

        main_layout.addWidget(self.tabs, stretch=1)

        self._build_studio_tab()
        self._build_editor_tab()
        self._build_split_tab()

    # =========================================================================
    # TAB 1: ALL-IN-ONE SINGLE-WINDOW PDF STUDIO
    # =========================================================================
    def _build_studio_tab(self) -> None:
        layout = QVBoxLayout(self.tab_studio)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Top Document Summary Strip
        self.doc_strip_frame = QFrame()
        self.doc_strip_frame.setProperty("class", "cardFrame")
        self.doc_strip_frame.setStyleSheet(
            "background-color: #15161a; border: 1px solid #23252c; border-radius: 6px; padding: 4px;"
        )
        strip_layout = QHBoxLayout(self.doc_strip_frame)
        strip_layout.setContentsMargins(8, 4, 8, 4)
        strip_layout.setSpacing(8)

        lbl_doc_title = QLabel("Loaded Files:")
        lbl_doc_title.setStyleSheet("font-weight: 600; color: #94a3b8; font-size: 11px;")
        strip_layout.addWidget(lbl_doc_title)

        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(6)
        strip_layout.addWidget(self.chips_container)

        strip_layout.addStretch()

        self.lbl_workspace_stat = QLabel("0 pages in workspace")
        self.lbl_workspace_stat.setStyleSheet("font-weight: 600; color: #60a5fa; font-size: 11px;")
        strip_layout.addWidget(self.lbl_workspace_stat)

        self.btn_add_more = QPushButton("+ Add More...")
        self.btn_add_more.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        self.btn_add_more.clicked.connect(self._select_multiple_pdfs_dialog)
        strip_layout.addWidget(self.btn_add_more)

        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #ef4444;")
        self.btn_clear_all.clicked.connect(self._clear_studio)
        strip_layout.addWidget(self.btn_clear_all)

        self.doc_strip_frame.hide()
        layout.addWidget(self.doc_strip_frame)

        # 2. Page Organizer Action Toolbar
        self.organizer_toolbar = QFrame()
        self.organizer_toolbar.setProperty("class", "cardFrame")
        tb_layout = QHBoxLayout(self.organizer_toolbar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(6)

        # Selection tools
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._select_all_pages)
        tb_layout.addWidget(btn_sel_all)

        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(self._deselect_all_pages)
        tb_layout.addWidget(btn_desel_all)

        btn_invert = QPushButton("Invert")
        btn_invert.setToolTip("Invert page selections")
        btn_invert.clicked.connect(self._invert_selection)
        tb_layout.addWidget(btn_invert)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("color: #334155; margin: 0 4px;")
        tb_layout.addWidget(div1)

        # Bulk Remove
        self.btn_remove_selected = QPushButton("🗑️ Remove Selected Pages")
        self.btn_remove_selected.setToolTip("Delete all checked pages from the assembled document")
        self.btn_remove_selected.setStyleSheet(
            "background-color: #450a0a; color: #f87171; border: 1px solid #7f1d1d; border-radius: 4px; font-weight: 600; padding: 4px 10px;"
        )
        self.btn_remove_selected.clicked.connect(self._remove_selected_pages)
        tb_layout.addWidget(self.btn_remove_selected)

        # Bulk Rotate
        self.btn_rotate_selected = QPushButton("⟳ Rotate Selected 90°")
        self.btn_rotate_selected.setToolTip("Rotate checked pages 90 degrees clockwise")
        self.btn_rotate_selected.clicked.connect(self._rotate_selected_pages)
        tb_layout.addWidget(self.btn_rotate_selected)

        # Large View Inspector
        self.btn_inspect_large = QPushButton("🔍 View Large")
        self.btn_inspect_large.setToolTip("Open full-size page inspector with zoom, selection, and rotation")
        self.btn_inspect_large.setStyleSheet(
            "font-weight: 600; padding: 4px 10px; background-color: #1e3a8a; border: 1px solid #3b82f6; border-radius: 4px; color: #ffffff;"
        )
        self.btn_inspect_large.clicked.connect(lambda: self._open_large_preview(0))
        tb_layout.addWidget(self.btn_inspect_large)

        tb_layout.addStretch()

        # Thumbnail Size selector
        self.combo_thumb_size = QComboBox()
        self.combo_thumb_size.addItems(["Grid: Normal (180px)", "Grid: Large (240px)", "Grid: X-Large (310px)"])
        self.combo_thumb_size.setToolTip("Adjust thumbnail size in page organizer")
        self.combo_thumb_size.currentIndexChanged.connect(self._on_thumb_size_changed)
        tb_layout.addWidget(self.combo_thumb_size)

        self.organizer_toolbar.hide()
        layout.addWidget(self.organizer_toolbar)

        # 3. Main Central Splitter (Organizer Grid on Left + Ready Options Panel on Right)
        self.studio_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Container: Drop Zone + Thumbnail Grid ---
        self.grid_container = QWidget()
        grid_vbox = QVBoxLayout(self.grid_container)
        grid_vbox.setContentsMargins(0, 0, 0, 0)
        grid_vbox.setSpacing(0)

        self.studio_drop = DropZone(
            title="Drop one or more PDFs here to merge and prepare",
            subtitle="Combine documents, delete unneeded pages, reorder, compress & protect in one place",
            file_filter="PDF Files (*.pdf)",
            multi_select=True
        )
        self.studio_drop.files_dropped.connect(self.add_pdf_files)
        grid_vbox.addWidget(self.studio_drop)

        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setStyleSheet("background-color: #0d0e11; border: 1px solid #1f2127; border-radius: 6px;")
        self.thumbnail_container = QWidget()
        self.thumbnail_container.setStyleSheet("background-color: #0d0e11;")
        self.thumbnail_grid = QGridLayout(self.thumbnail_container)
        self.thumbnail_grid.setSpacing(12)
        self.thumbnail_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.thumbnail_scroll.setWidget(self.thumbnail_container)
        self.thumbnail_scroll.hide()
        grid_vbox.addWidget(self.thumbnail_scroll, stretch=1)

        self.studio_splitter.addWidget(self.grid_container)

        # --- Right Container: Ready & Export PDF Panel ---
        self.options_panel = QFrame()
        self.options_panel.setProperty("class", "cardFrame")
        self.options_panel.setMinimumWidth(320)
        self.options_panel.setMaximumWidth(420)
        self.options_panel.setStyleSheet("background-color: #141519; border: 1px solid #23252c; border-radius: 8px;")

        panel_scroll = QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setStyleSheet("border: none; background: transparent;")

        panel_inner = QWidget()
        panel_inner.setStyleSheet("background: transparent;")
        panel_layout = QVBoxLayout(panel_inner)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(12)

        lbl_panel_title = QLabel("Ready & Export PDF")
        lbl_panel_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #60a5fa;")
        panel_layout.addWidget(lbl_panel_title)

        lbl_panel_sub = QLabel("Configure all output options in this window and export your finished PDF instantly.")
        lbl_panel_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        lbl_panel_sub.setWordWrap(True)
        panel_layout.addWidget(lbl_panel_sub)

        # Live export summary card
        self.summary_badge = QFrame()
        self.summary_badge.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 8px;")
        sum_lay = QVBoxLayout(self.summary_badge)
        sum_lay.setContentsMargins(8, 8, 8, 8)
        sum_lay.setSpacing(4)
        self.lbl_sum_pages = QLabel("Pages to Export: 0")
        self.lbl_sum_pages.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 13px;")
        self.lbl_sum_docs = QLabel("Merged Documents: 0")
        self.lbl_sum_docs.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sum_lay.addWidget(self.lbl_sum_pages)
        sum_lay.addWidget(self.lbl_sum_docs)
        panel_layout.addWidget(self.summary_badge)

        # Scope Selection
        grp_scope = QGroupBox("Export Scope")
        grp_scope.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_scope = QVBoxLayout(grp_scope)
        lay_scope.setSpacing(6)
        self.rad_export_all = QRadioButton("Export All Remaining Pages")
        self.rad_export_all.setChecked(True)
        self.rad_export_all.toggled.connect(self._update_export_summary)
        self.rad_export_selected = QRadioButton("Export Selected Pages Only")
        self.rad_export_selected.toggled.connect(self._update_export_summary)
        lay_scope.addWidget(self.rad_export_all)
        lay_scope.addWidget(self.rad_export_selected)
        panel_layout.addWidget(grp_scope)

        # Option: Compression
        grp_comp = QGroupBox("📉 PDF Compression")
        grp_comp.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_comp = QVBoxLayout(grp_comp)
        lay_comp.setSpacing(6)
        self.chk_compress = QCheckBox("Compress Output PDF")
        self.chk_compress.setToolTip("Shrink file size via pikepdf stream deflation and media optimization")
        lay_comp.addWidget(self.chk_compress)

        row_prof = QHBoxLayout()
        row_prof.addWidget(QLabel("Profile:"))
        self.combo_compress_profile = QComboBox()
        self.combo_compress_profile.addItems(["Medium (Balanced)", "High (Maximum Compression)", "Low (Fast / High Quality)"])
        self.combo_compress_profile.setCurrentIndex(0)
        row_prof.addWidget(self.combo_compress_profile)
        lay_comp.addLayout(row_prof)
        panel_layout.addWidget(grp_comp)

        # Option: Security & Password
        grp_sec = QGroupBox("🔒 Password Protection")
        grp_sec.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_sec = QVBoxLayout(grp_sec)
        lay_sec.setSpacing(6)
        self.chk_protect = QCheckBox("Encrypt with AES-256")
        lay_sec.addWidget(self.chk_protect)

        self.txt_protect_pwd = QLineEdit()
        self.txt_protect_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_protect_pwd.setPlaceholderText("Enter password to open PDF")
        lay_sec.addWidget(self.txt_protect_pwd)

        row_perms = QHBoxLayout()
        self.chk_allow_print = QCheckBox("Allow Printing")
        self.chk_allow_print.setChecked(True)
        self.chk_allow_copy = QCheckBox("Allow Copying")
        self.chk_allow_copy.setChecked(True)
        row_perms.addWidget(self.chk_allow_print)
        row_perms.addWidget(self.chk_allow_copy)
        lay_sec.addLayout(row_perms)
        panel_layout.addWidget(grp_sec)

        # Option: Watermark
        grp_wm = QGroupBox("🖋️ Watermark / Stamp")
        grp_wm.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_wm = QVBoxLayout(grp_wm)
        lay_wm.setSpacing(6)
        self.chk_watermark = QCheckBox("Apply Watermark Across Pages")
        lay_wm.addWidget(self.chk_watermark)

        self.txt_watermark = QLineEdit("CONFIDENTIAL")
        lay_wm.addWidget(self.txt_watermark)

        row_tags = QHBoxLayout()
        row_tags.setSpacing(4)
        for tag in ["CONFIDENTIAL", "APPROVED", "DRAFT", "FINAL"]:
            btn_t = QPushButton(tag)
            btn_t.setStyleSheet("font-size: 10px; padding: 2px 5px;")
            btn_t.clicked.connect(lambda chk=False, t=tag: self.txt_watermark.setText(t))
            row_tags.addWidget(btn_t)
        lay_wm.addLayout(row_tags)
        panel_layout.addWidget(grp_wm)

        # Split shortcuts
        grp_split_quick = QGroupBox("✂️ Split Options")
        grp_split_quick.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_sq = QHBoxLayout(grp_split_quick)
        lay_sq.setSpacing(6)
        btn_sq_ranges = QPushButton("Split by Ranges...")
        btn_sq_ranges.clicked.connect(self._quick_split_ranges)
        btn_sq_chunks = QPushButton("Split Every N Pages...")
        btn_sq_chunks.clicked.connect(self._quick_split_chunks)
        lay_sq.addWidget(btn_sq_ranges)
        lay_sq.addWidget(btn_sq_chunks)
        panel_layout.addWidget(grp_split_quick)

        panel_layout.addStretch()

        # Primary Big Export Action Button
        self.btn_export_ready = QPushButton("🚀 Save / Export Ready PDF...")
        self.btn_export_ready.setProperty("class", "primaryButton")
        self.btn_export_ready.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 700; font-size: 13px; padding: 12px; border-radius: 6px;"
        )
        self.btn_export_ready.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_ready.clicked.connect(self._execute_assemble_ready_pdf)
        panel_layout.addWidget(self.btn_export_ready)

        panel_scroll.setWidget(panel_inner)
        panel_outer_layout = QVBoxLayout(self.options_panel)
        panel_outer_layout.setContentsMargins(0, 0, 0, 0)
        panel_outer_layout.addWidget(panel_scroll)

        self.studio_splitter.addWidget(self.options_panel)
        self.studio_splitter.setStretchFactor(0, 3)
        self.studio_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.studio_splitter, stretch=1)

    # =========================================================================
    # TAB 2: IN-PLACE CONTENT EDITOR (Redaction, Text Box, Stamps)
    # =========================================================================
    def _build_editor_tab(self) -> None:
        layout = QVBoxLayout(self.tab_editor)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Editor toolbar
        top_bar = QFrame()
        top_bar.setProperty("class", "cardFrame")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 6, 8, 6)
        tb_lay.setSpacing(8)

        btn_prev = QPushButton("◀ Prev Page")
        btn_prev.clicked.connect(self._editor_prev_page)
        tb_lay.addWidget(btn_prev)

        self.lbl_ed_page = QLabel("No document loaded")
        self.lbl_ed_page.setStyleSheet("font-weight: 600; color: #60a5fa;")
        tb_lay.addWidget(self.lbl_ed_page)

        btn_next = QPushButton("Next Page ▶")
        btn_next.clicked.connect(self._editor_next_page)
        tb_lay.addWidget(btn_next)

        tb_lay.addStretch()

        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.clicked.connect(self._editor_zoom_out)
        tb_lay.addWidget(btn_zoom_out)

        self.lbl_zoom_val = QLabel("120%")
        self.lbl_zoom_val.setStyleSheet("font-weight: 600; color: #93c5fd;")
        tb_lay.addWidget(self.lbl_zoom_val)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.clicked.connect(self._editor_zoom_in)
        tb_lay.addWidget(btn_zoom_in)

        layout.addWidget(top_bar)

        # Tool operations
        tools_tab = QTabWidget()

        # 1. Redact / Replace
        tab_redact = QWidget()
        r_lay = QHBoxLayout(tab_redact)
        r_lay.setContentsMargins(8, 6, 8, 6)
        r_lay.addWidget(QLabel("Find Text:"))
        self.txt_ed_search = QLineEdit()
        self.txt_ed_search.setPlaceholderText("Word or phrase to redact")
        r_lay.addWidget(self.txt_ed_search)

        r_lay.addWidget(QLabel("Replace With:"))
        self.txt_ed_replace = QLineEdit()
        self.txt_ed_replace.setPlaceholderText("Leave empty to black-out redact")
        r_lay.addWidget(self.txt_ed_replace)

        btn_exec_redact = QPushButton("⬛ Apply Redact / Replace...")
        btn_exec_redact.setProperty("class", "primaryButton")
        btn_exec_redact.clicked.connect(self._execute_redact_replace)
        r_lay.addWidget(btn_exec_redact)
        tools_tab.addTab(tab_redact, "⬛ Redact & Replace Text")

        # 2. Insert Text
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

        btn_exec_insert = QPushButton("🔤 Insert Text...")
        btn_exec_insert.setProperty("class", "primaryButton")
        btn_exec_insert.clicked.connect(self._execute_insert_text)
        t_lay.addWidget(btn_exec_insert)
        tools_tab.addTab(tab_text, "🔤 Insert Text Box")

        # 3. Insert Stamp
        tab_img = QWidget()
        im_lay = QHBoxLayout(tab_img)
        im_lay.setContentsMargins(8, 6, 8, 6)
        self.btn_choose_stamp = QPushButton("Choose Image / Stamp...")
        self.btn_choose_stamp.clicked.connect(self._choose_stamp_image)
        im_lay.addWidget(self.btn_choose_stamp)

        self.lbl_stamp_path = QLabel("No image selected")
        self.lbl_stamp_path.setStyleSheet("color: #9ca3af; font-size: 11px;")
        im_lay.addWidget(self.lbl_stamp_path)

        im_lay.addWidget(QLabel("W:"))
        self.spin_stamp_w = QSpinBox()
        self.spin_stamp_w.setRange(20, 1000)
        self.spin_stamp_w.setValue(160)
        im_lay.addWidget(self.spin_stamp_w)

        im_lay.addWidget(QLabel("H:"))
        self.spin_stamp_h = QSpinBox()
        self.spin_stamp_h.setRange(20, 1000)
        self.spin_stamp_h.setValue(80)
        im_lay.addWidget(self.spin_stamp_h)

        btn_exec_stamp = QPushButton("🖼 Place Stamp...")
        btn_exec_stamp.setProperty("class", "primaryButton")
        btn_exec_stamp.clicked.connect(self._execute_insert_image)
        im_lay.addWidget(btn_exec_stamp)
        tools_tab.addTab(tab_img, "🖼 Place Image / Stamp")

        layout.addWidget(tools_tab)

        # Editor Canvas
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_canvas_container = QWidget()
        c_vlay = QVBoxLayout(self.editor_canvas_container)
        c_vlay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.editor_canvas_lbl = QLabel("Open a PDF file to view and edit pages.")
        self.editor_canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor_canvas_lbl.setStyleSheet("background-color: #111215; border: 1px solid #282a30; border-radius: 4px;")
        self.editor_canvas_lbl.mousePressEvent = self._on_canvas_clicked
        c_vlay.addWidget(self.editor_canvas_lbl)

        self.editor_scroll.setWidget(self.editor_canvas_container)
        layout.addWidget(self.editor_scroll, stretch=1)

    # =========================================================================
    # TAB 3: SPLIT DOCUMENT
    # =========================================================================
    def _build_split_tab(self) -> None:
        layout = QVBoxLayout(self.tab_split)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        lbl_info = QLabel("Split Options for Current Workspace or Selected Document")
        lbl_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        card_layout.addWidget(lbl_info)

        grp_range = QGroupBox("Mode A: Split by Page Ranges")
        lay_range = QVBoxLayout(grp_range)
        lbl_hint = QLabel("Enter ranges separated by commas (e.g. '1-3, 5, 8-10'):")
        lbl_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.txt_ranges = QLineEdit("1-2, 3-4")
        lay_range.addWidget(lbl_hint)
        lay_range.addWidget(self.txt_ranges)
        self.btn_split_ranges = QPushButton("Split by Defined Ranges...")
        self.btn_split_ranges.setProperty("class", "primaryButton")
        self.btn_split_ranges.clicked.connect(self._quick_split_ranges)
        lay_range.addWidget(self.btn_split_ranges)
        card_layout.addWidget(grp_range)

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
        self.btn_split_chunks.clicked.connect(self._quick_split_chunks)
        lay_chunk.addWidget(self.btn_split_chunks)
        card_layout.addWidget(grp_chunk)

        layout.addWidget(card)
        layout.addStretch()

    # =========================================================================
    # MULTI-PDF INGESTION & DOCUMENT MANAGEMENT
    # =========================================================================
    def _select_multiple_pdfs_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF Document(s) to Add", "", "PDF Files (*.pdf)")
        if files:
            self.add_pdf_files(files)

    def _select_pdf_dialog(self) -> None:
        self._select_multiple_pdfs_dialog()

    def load_pdf(self, file_path: str) -> None:
        """Single file load compatibility."""
        self.add_pdf_files([file_path])

    def add_pdf_files(self, file_paths: List[str]) -> None:
        """Add one or more PDF files into the active workspace."""
        valid_paths = []
        for p_str in file_paths:
            is_valid, msg = validate_file(p_str, expected_type="pdf")
            if is_valid:
                valid_paths.append(str(Path(p_str).resolve()))
            else:
                QMessageBox.warning(self, "Invalid File", f"{Path(p_str).name}: {msg}")

        if not valid_paths:
            return

        self.progress_card.start_task(f"Importing {len(valid_paths)} PDF document(s)...")

        def import_worker(progress_callback=None):
            new_docs = []
            new_pages = []
            start_doc_id = len(self.loaded_documents) + 1

            for doc_idx, file_p in enumerate(valid_paths):
                curr_doc_id = start_doc_id + doc_idx
                color = DOC_PALETTE[(curr_doc_id - 1) % len(DOC_PALETTE)]

                info = PDFEngine.get_document_info(file_p)
                doc_name = info["file_name"]
                page_count = info["page_count"]

                new_docs.append({
                    "id": curr_doc_id,
                    "file_path": file_p,
                    "file_name": doc_name,
                    "file_size": info["file_size"],
                    "page_count": page_count,
                    "color": color,
                })

                for p_i in range(page_count):
                    if progress_callback:
                        pct = int(((doc_idx * 100) + ((p_i + 1) / max(page_count, 1) * 100)) / (len(valid_paths) * 100) * 100)
                        progress_callback(pct, f"Loading {doc_name} — page {p_i + 1}/{page_count}...")

                    thumb_bytes = PDFEngine.render_page_thumbnail(file_p, p_i, target_width=200)
                    new_pages.append({
                        "doc_id": curr_doc_id,
                        "doc_name": doc_name,
                        "doc_color": color,
                        "source_file": file_p,
                        "orig_index": p_i,
                        "rotation": 0,
                        "pixmap_bytes": thumb_bytes
                    })

            return new_docs, new_pages

        worker = TaskWorker(import_worker)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(self._on_files_imported)
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Failed to import PDF(s)", err))
        self.thread_pool.start(worker)

    def _on_files_imported(self, result: tuple) -> None:
        new_docs, new_pages = result
        self.loaded_documents.extend(new_docs)
        self.pages_data.extend(new_pages)

        for d in new_docs:
            self.db.add_recent_file(d["file_path"], file_type="pdf")

        self.editor_total_pages = len(self.pages_data)
        self.editor_current_page = 0

        self.progress_card.complete_task(f"Loaded {len(new_docs)} document(s) with {len(new_pages)} total page(s).")
        self.progress_card.hide()

        self._refresh_chips()
        self._refresh_thumbnail_grid()
        self._update_export_summary()
        self._refresh_editor_canvas()

    def _remove_document(self, doc_id: int) -> None:
        """Remove an entire document and its pages from the workspace."""
        self.loaded_documents = [d for d in self.loaded_documents if d["id"] != doc_id]
        self.pages_data = [p for p in self.pages_data if p["doc_id"] != doc_id]

        if not self.pages_data:
            self._clear_studio()
        else:
            self._refresh_chips()
            self._refresh_thumbnail_grid()
            self._update_export_summary()
            self._refresh_editor_canvas()

    def _clear_studio(self) -> None:
        """Reset workspace completely."""
        self.loaded_documents.clear()
        self.pages_data.clear()

        for w in self.thumbnail_widgets:
            w.setParent(None)
            w.deleteLater()
        self.thumbnail_widgets.clear()

        # Clear chips
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.doc_strip_frame.hide()
        self.organizer_toolbar.hide()
        self.thumbnail_scroll.hide()
        self.studio_drop.show()

        self.editor_total_pages = 0
        self.editor_current_page = 0
        self.editor_canvas_lbl.setText("Open a PDF file to view and edit pages.")

        self._update_export_summary()

    def _refresh_chips(self) -> None:
        """Render loaded document badges."""
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.loaded_documents:
            self.doc_strip_frame.hide()
            return

        for doc in self.loaded_documents:
            chip = QFrame()
            color = doc["color"]
            chip.setStyleSheet(
                f"background-color: #17181d; border: 1px solid {color}; border-radius: 4px; padding: 2px 6px;"
            )
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.setSpacing(6)

            lbl_name = QLabel(f"📄 {doc['file_name']} ({doc['page_count']}p)")
            lbl_name.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 11px;")
            c_lay.addWidget(lbl_name)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(16, 16)
            btn_del.setToolTip(f"Remove {doc['file_name']} from workspace")
            btn_del.setStyleSheet("padding: 0; font-size: 9px; color: #f87171; border: none; background: transparent;")
            btn_del.clicked.connect(lambda chk=False, d_id=doc["id"]: self._remove_document(d_id))
            c_lay.addWidget(btn_del)

            self.chips_layout.addWidget(chip)

        self.doc_strip_frame.show()

    # =========================================================================
    # THUMBNAIL GRID, REORDERING & REMOVAL
    # =========================================================================
    def _on_thumb_size_changed(self, idx: int) -> None:
        if idx == 0:
            self.thumbnail_card_w, self.thumbnail_card_h = 180, 255
        elif idx == 1:
            self.thumbnail_card_w, self.thumbnail_card_h = 240, 330
        elif idx == 2:
            self.thumbnail_card_w, self.thumbnail_card_h = 310, 420
        self._refresh_thumbnail_grid()

    def _refresh_thumbnail_grid(self) -> None:
        """Redraw thumbnail cards from current pages_data."""
        prev_selections = [w.is_selected() for w in self.thumbnail_widgets]

        for w in self.thumbnail_widgets:
            w.setParent(None)
            w.deleteLater()
        self.thumbnail_widgets.clear()

        if not self.pages_data:
            self.thumbnail_scroll.hide()
            self.organizer_toolbar.hide()
            self.studio_drop.show()
            return

        self.studio_drop.hide()
        self.organizer_toolbar.show()
        self.thumbnail_scroll.show()

        container_w = max(self.thumbnail_scroll.viewport().width(), 650)
        cols = max(1, container_w // (self.thumbnail_card_w + 16))

        for i, item in enumerate(self.pages_data):
            row = i // cols
            col = i % cols

            doc_label = f"Doc {item['doc_id']}" if len(self.loaded_documents) > 1 else ""
            card = ThumbnailCard(
                page_index=i,
                page_number=i + 1,
                pixmap_bytes=item["pixmap_bytes"],
                card_width=self.thumbnail_card_w,
                card_height=self.thumbnail_card_h,
                doc_label=doc_label,
                doc_color=item.get("doc_color", "#60a5fa")
            )
            card.selection_changed.connect(self._on_card_selection_changed)
            card.inspect_requested.connect(self._open_large_preview)
            card.rotate_requested.connect(self._on_card_rotate)
            card.delete_requested.connect(self._on_card_delete)
            card.move_left_requested.connect(self._on_card_move_left)
            card.move_right_requested.connect(self._on_card_move_right)

            if i < len(prev_selections):
                card.set_selected(prev_selections[i])

            self.thumbnail_grid.addWidget(card, row, col)
            self.thumbnail_widgets.append(card)

        self._update_export_summary()

    def _on_card_selection_changed(self, index: int, is_selected: bool) -> None:
        self._update_export_summary()

    def _select_all_pages(self) -> None:
        for w in self.thumbnail_widgets:
            w.set_selected(True)
        self._update_export_summary()

    def _deselect_all_pages(self) -> None:
        for w in self.thumbnail_widgets:
            w.set_selected(False)
        self._update_export_summary()

    def _invert_selection(self) -> None:
        for w in self.thumbnail_widgets:
            w.set_selected(not w.is_selected())
        self._update_export_summary()

    def _remove_selected_pages(self) -> None:
        """Remove all checked pages from the assembled document."""
        selected_indices = {i for i, w in enumerate(self.thumbnail_widgets) if w.is_selected()}
        if not selected_indices:
            QMessageBox.information(self, "No Pages Selected", "Please select at least one page using the checkboxes to remove.")
            return

        self.pages_data = [p for i, p in enumerate(self.pages_data) if i not in selected_indices]
        if not self.pages_data:
            self._clear_studio()
        else:
            self._refresh_thumbnail_grid()
            self._refresh_editor_canvas()

    def _rotate_selected_pages(self) -> None:
        """Rotate checked pages 90 degrees."""
        for i, w in enumerate(self.thumbnail_widgets):
            if w.is_selected() and i < len(self.pages_data):
                self._on_card_rotate(i)

    def _on_card_rotate(self, index: int) -> None:
        if 0 <= index < len(self.pages_data):
            self.pages_data[index]["rotation"] = (self.pages_data[index].get("rotation", 0) + 90) % 360
            px = QPixmap()
            px.loadFromData(self.pages_data[index]["pixmap_bytes"])
            transform = px.transformed(px.trueMatrix(px.createHeuristicMask(), 90))
            if index < len(self.thumbnail_widgets):
                scaled = transform.scaled(
                    max(self.thumbnail_card_w - 24, 120),
                    max(self.thumbnail_card_h - 75, 140),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail_widgets[index].lbl_image.setPixmap(scaled)

    def _on_card_delete(self, index: int) -> None:
        """Remove single page from workspace."""
        if 0 <= index < len(self.pages_data):
            del self.pages_data[index]
            if not self.pages_data:
                self._clear_studio()
            else:
                self._refresh_thumbnail_grid()
                self._refresh_editor_canvas()

    def _on_card_move_left(self, index: int) -> None:
        if index > 0:
            self.pages_data[index - 1], self.pages_data[index] = self.pages_data[index], self.pages_data[index - 1]
            self._refresh_thumbnail_grid()

    def _on_card_move_right(self, index: int) -> None:
        if index < len(self.pages_data) - 1:
            self.pages_data[index + 1], self.pages_data[index] = self.pages_data[index], self.pages_data[index + 1]
            self._refresh_thumbnail_grid()

    def _update_export_summary(self) -> None:
        """Update live counts on right-hand Ready panel."""
        total = len(self.pages_data)
        selected_count = sum(1 for w in self.thumbnail_widgets if w.is_selected())

        self.lbl_workspace_stat.setText(f"{total} page(s) in workspace")
        self.lbl_sum_pages.setText(f"Pages to Export: {selected_count if self.rad_export_selected.isChecked() else total}")
        self.lbl_sum_docs.setText(f"Merged Documents: {len(self.loaded_documents)}")

        self.rad_export_all.setText(f"Export All Remaining Pages ({total})")
        self.rad_export_selected.setText(f"Export Selected Pages Only ({selected_count})")

    # =========================================================================
    # LARGE PAGE INSPECTION
    # =========================================================================
    def _open_large_preview(self, initial_index: int = 0) -> None:
        """Open high-visibility page inspection dialog with zoom, rotate, select-all, and removal."""
        if not self.pages_data:
            QMessageBox.information(self, "No Document", "Please add at least one PDF document first.")
            return

        selected_indices = {i for i, w in enumerate(self.thumbnail_widgets) if w.is_selected()}
        primary_file = self.pages_data[0]["source_file"]

        dialog = PagePreviewDialog(
            file_path=primary_file,
            pages_data=self.pages_data,
            initial_index=initial_index,
            selected_indices=selected_indices,
            parent=self
        )

        def on_selection_changed(idx: int, is_sel: bool):
            if 0 <= idx < len(self.thumbnail_widgets):
                self.thumbnail_widgets[idx].set_selected(is_sel)
            self._update_export_summary()

        def on_select_all():
            self._select_all_pages()

        def on_deselect_all():
            self._deselect_all_pages()

        def on_rotate_page(idx: int):
            self._on_card_rotate(idx)

        def on_delete_page(idx: int):
            self._on_card_delete(idx)

        def on_extract(selected_list: list):
            dialog.accept()
            self._deselect_all_pages()
            for idx in selected_list:
                if 0 <= idx < len(self.thumbnail_widgets):
                    self.thumbnail_widgets[idx].set_selected(True)
            self.rad_export_selected.setChecked(True)
            self._execute_assemble_ready_pdf()

        dialog.selection_changed.connect(on_selection_changed)
        dialog.select_all_requested.connect(on_select_all)
        dialog.deselect_all_requested.connect(on_deselect_all)
        dialog.rotate_page_requested.connect(on_rotate_page)
        dialog.delete_page_requested.connect(on_delete_page)
        dialog.extract_requested.connect(on_extract)

        dialog.exec()

    # =========================================================================
    # ONE-CLICK READY & EXPORT ENGINE EXECUTION
    # =========================================================================
    def _execute_assemble_ready_pdf(self) -> None:
        """Assemble all remaining or selected pages with compression, security, and watermarking."""
        if not self.pages_data:
            QMessageBox.warning(self, "No Pages", "Workspace is empty. Please add PDF files first.")
            return

        if self.rad_export_selected.isChecked():
            pages_to_export = [p for i, p in enumerate(self.pages_data) if self.thumbnail_widgets[i].is_selected()]
            if not pages_to_export:
                QMessageBox.warning(self, "No Pages Selected", "Please select at least one page or choose 'Export All Remaining Pages'.")
                return
        else:
            pages_to_export = self.pages_data

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Ready PDF Document", "ready_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        # Profile string extraction (low, medium, high)
        comp_profile = self.combo_compress_profile.currentText().split()[0].lower()
        user_pwd = self.txt_protect_pwd.text().strip() if self.chk_protect.isChecked() else None
        wm_text = self.txt_watermark.text().strip() if self.chk_watermark.isChecked() else None

        self.progress_card.start_task("Assembling and Readying Final PDF...")

        worker = TaskWorker(
            PDFEngine.assemble_pdf,
            pages_spec=pages_to_export,
            output_path=out_path,
            compress=self.chk_compress.isChecked(),
            compress_profile=comp_profile,
            user_password=user_pwd,
            allow_printing=self.chk_allow_print.isChecked(),
            allow_copying=self.chk_allow_copy.isChecked(),
            watermark_text=wm_text,
        )
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(self._on_assembly_finished)
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("PDF Assembly Failed", err))
        self.thread_pool.start(worker)

    def _on_assembly_finished(self, result: Dict[str, Any]) -> None:
        out_file = result["output_file"]
        pages_count = result["pages_count"]
        size_str = format_file_size(result["file_size"])

        self.db.add_recent_file(out_file, file_type="pdf")
        self.db.add_history(
            operation="Ready PDF Export",
            source_file=Path(self.loaded_documents[0]["file_path"]).name if self.loaded_documents else "Multi-PDF",
            output_file=out_file,
            details=f"Exported {pages_count} pages (Size: {size_str}, Compressed: {result['compressed']}, Protected: {result['protected']})"
        )

        msg = f"Ready PDF successfully exported!\n\nPages: {pages_count}\nOutput Size: {size_str}\nPath: {out_file}"
        self._on_operation_done("PDF Ready", msg, out_file)

    def _quick_split_ranges(self) -> None:
        """Split workspace by ranges."""
        if not self.pages_data:
            QMessageBox.warning(self, "No Document", "Please add a PDF document first.")
            return

        ranges_str, ok = self.txt_ranges.text().strip(), True
        if not ranges_str:
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Split Files")
        if not out_dir:
            return

        # Assemble temporary current workspace PDF then split
        temp_doc = os.path.join(out_dir, "_temp_workspace.pdf")
        PDFEngine.assemble_pdf(self.pages_data, temp_doc)

        self.progress_card.start_task("Splitting Workspace PDF by Ranges...")
        worker = TaskWorker(PDFEngine.split_pdf_by_ranges, temp_doc, ranges_str, out_dir)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda files: self._on_operation_done("Split Complete", f"Created {len(files)} split files in {out_dir}."))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Split Failed", err))
        self.thread_pool.start(worker)

    def _quick_split_chunks(self) -> None:
        if not self.pages_data:
            QMessageBox.warning(self, "No Document", "Please add a PDF document first.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Split Files")
        if not out_dir:
            return

        chunk_size = self.spin_chunk_size.value()
        temp_doc = os.path.join(out_dir, "_temp_workspace.pdf")
        PDFEngine.assemble_pdf(self.pages_data, temp_doc)

        self.progress_card.start_task("Splitting Every N Pages...")
        worker = TaskWorker(PDFEngine.split_pdf_by_chunks, temp_doc, chunk_size, out_dir)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda files: self._on_operation_done("Split Complete", f"Generated {len(files)} files."))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Split Failed", err))
        self.thread_pool.start(worker)

    # =========================================================================
    # IN-PLACE CONTENT EDITOR METHODS
    # =========================================================================
    def _choose_stamp_image(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select Image or Signature Stamp", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            self.lbl_stamp_path.setText(Path(p).name)
            self.lbl_stamp_path.setToolTip(p)

    def _on_canvas_clicked(self, event) -> None:
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
        self.editor_zoom = min(3.0, round(self.editor_zoom + 0.2, 1))
        self.lbl_zoom_val.setText(f"{int(self.editor_zoom * 100)}%")
        self._refresh_editor_canvas()

    def _editor_zoom_out(self) -> None:
        self.editor_zoom = max(0.5, round(self.editor_zoom - 0.2, 1))
        self.lbl_zoom_val.setText(f"{int(self.editor_zoom * 100)}%")
        self._refresh_editor_canvas()

    def _refresh_editor_canvas(self) -> None:
        if not self.pages_data or self.editor_total_pages == 0:
            self.editor_canvas_lbl.setText("Add PDF documents to view and edit pages.")
            self.lbl_ed_page.setText("No document loaded")
            return

        self.editor_current_page = max(0, min(self.editor_current_page, len(self.pages_data) - 1))
        page_meta = self.pages_data[self.editor_current_page]
        self.lbl_ed_page.setText(f"Page {self.editor_current_page + 1} of {len(self.pages_data)} ({page_meta.get('doc_name', '')})")

        try:
            png_bytes = PDFEngine.render_page_hires(
                page_meta["source_file"],
                page_meta["orig_index"],
                zoom=self.editor_zoom,
                rotation=page_meta.get("rotation", 0)
            )
            px = QPixmap()
            px.loadFromData(png_bytes)
            self.editor_canvas_lbl.setPixmap(px)
        except Exception as e:
            self.editor_canvas_lbl.setText(f"Error rendering page: {e}")

    def _execute_redact_replace(self) -> None:
        if not self.pages_data:
            QMessageBox.warning(self, "No Document", "Please add a PDF document first.")
            return

        search_term = self.txt_ed_search.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Search Term Required", "Please enter a word or phrase to find.")
            return

        replace_text = self.txt_ed_replace.text().strip() or None
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Redacted/Modified PDF", "edited_document.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        page_meta = self.pages_data[self.editor_current_page]
        self.progress_card.start_task("Applying In-Place Redactions / Replacements...")
        worker = TaskWorker(
            PDFEngine.redact_and_replace_text,
            file_path=page_meta["source_file"],
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
        if not self.pages_data:
            QMessageBox.warning(self, "No Document", "Please add a PDF document first.")
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

        page_meta = self.pages_data[self.editor_current_page]
        self.progress_card.start_task("Inserting Text on Page...")
        worker = TaskWorker(
            PDFEngine.insert_content_on_page,
            file_path=page_meta["source_file"],
            output_path=out_path,
            page_index=page_meta["orig_index"],
            items=[item]
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done("Text Inserted", f"Saved modified PDF to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Insert Failed", err))
        self.thread_pool.start(worker)

    def _execute_insert_image(self) -> None:
        if not self.pages_data:
            QMessageBox.warning(self, "No Document", "Please add a PDF document first.")
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

        page_meta = self.pages_data[self.editor_current_page]
        self.progress_card.start_task("Placing Image on Page...")
        worker = TaskWorker(
            PDFEngine.insert_content_on_page,
            file_path=page_meta["source_file"],
            output_path=out_path,
            page_index=page_meta["orig_index"],
            items=[item]
        )
        worker.signals.finished.connect(lambda res: self._on_operation_done("Image Placed", f"Saved stamped PDF to {res}", res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Placement Failed", err))
        self.thread_pool.start(worker)

    # =========================================================================
    # COMMON FEEDBACK HANDLERS
    # =========================================================================
    def _on_operation_done(self, title: str, message: str, file_path: Optional[str] = None) -> None:
        self.progress_card.complete_task(message)
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Information)

        if file_path and Path(file_path).exists():
            btn_open_folder = box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            btn_ok = box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            box.exec()
            if box.clickedButton() == btn_open_folder:
                import subprocess
                subprocess.Popen(["explorer", "/select,", str(Path(file_path).resolve())])
        else:
            box.exec()

    def _on_worker_error(self, title: str, error_msg: str) -> None:
        self.progress_card.fail_task(error_msg)
        QMessageBox.critical(self, title, f"An error occurred during processing:\n\n{error_msg}")
