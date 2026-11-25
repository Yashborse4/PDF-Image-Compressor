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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.pdf_engine import PDFEngine
from docutools.core.validator import format_file_size, validate_file
from docutools.ui.components.digital_signature_dialog import DigitalSignatureDialog
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

    def _get_first_doc_path(self) -> Optional[str]:
        return self.current_pdf_path

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

        # Operation Mode Switcher Ribbon
        ribbon_frame = QFrame()
        ribbon_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        ribbon_lay = QHBoxLayout(ribbon_frame)
        ribbon_lay.setContentsMargins(6, 4, 6, 4)
        ribbon_lay.setSpacing(6)

        lbl_modes = QLabel("Quick Navigation:")
        lbl_modes.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px;")
        ribbon_lay.addWidget(lbl_modes)

        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.setExclusive(True)
        mode_buttons = [
            ("📑 Organize & Merge", 0),
            ("✂️ Split & Extract", 1),
            ("📉 Compress PDF", 2),
            ("🔒 Password Protect", 3),
            ("🔏 Digital Sign", 4),
            ("✏️ Edit Text", 5),
        ]
        for label, tab_idx in mode_buttons:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cbd5e1;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #ffffff;
                }
                QPushButton:checked {
                    background-color: rgba(96, 205, 255, 0.16);
                    color: #60cdff;
                    border: 1px solid rgba(96, 205, 255, 0.35);
                }
            """)
            btn.clicked.connect(lambda _, idx=tab_idx: self.switch_to_tab(idx))
            self.mode_btn_group.addButton(btn, tab_idx)
            ribbon_lay.addWidget(btn)
            if tab_idx == 0:
                btn.setChecked(True)

        ribbon_lay.addStretch()
        main_layout.addWidget(ribbon_frame)

        # Main Navigation Tabs
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tab_studio = QWidget()
        self.tab_split = QWidget()
        self.tab_compress = QWidget()
        self.tab_protect = QWidget()
        self.tab_sign = QWidget()
        self.tab_editor = QWidget()

        self.tabs.addTab(self.tab_studio, "📑 Organize & Merge")
        self.tabs.addTab(self.tab_split, "✂️ Split & Extract")
        self.tabs.addTab(self.tab_compress, "📉 Compress & Optimize")
        self.tabs.addTab(self.tab_protect, "🔒 Password & Permissions")
        self.tabs.addTab(self.tab_sign, "🔏 Digital Signatures")
        self.tabs.addTab(self.tab_editor, "✏️ In-Place Content Editor")

        main_layout.addWidget(self.tabs, stretch=1)

        self._build_studio_tab()
        self._build_split_tab()
        self._build_compress_tab()
        self._build_protect_tab()
        self._build_signing_tab()
        self._build_editor_tab()

    def _on_tab_changed(self, index: int) -> None:
        btn = self.mode_btn_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

    def switch_to_tab(self, target: str | int) -> None:
        """Switch active tab in PDF Manager."""
        tab_map = {
            "studio": 0,
            "organize": 0,
            "merge": 0,
            "split": 1,
            "compress": 2,
            "protect": 3,
            "security": 3,
            "sign": 4,
            "signature": 4,
            "editor": 5,
            "edit": 5,
        }
        if isinstance(target, str):
            idx = tab_map.get(target.lower(), 0)
        else:
            idx = max(0, min(5, target))
        self.tabs.setCurrentIndex(idx)
        btn = self.mode_btn_group.button(idx)
        if btn:
            btn.setChecked(True)

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

        # Digital Signature Suite
        self.btn_digital_sign = QPushButton("🔏 Digital Signature...")
        self.btn_digital_sign.setToolTip("Open cryptographic digital signature & verification suite")
        self.btn_digital_sign.setStyleSheet(
            "font-weight: 600; padding: 4px 10px; background-color: #065f46; border: 1px solid #059669; border-radius: 4px; color: #ffffff;"
        )
        self.btn_digital_sign.clicked.connect(self._open_digital_signature_suite)
        tb_layout.addWidget(self.btn_digital_sign)

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

        # Option: Digital Signature
        grp_sign = QGroupBox("🔏 Digital Signature (PAdES / PKCS#7)")
        grp_sign.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        lay_sign = QVBoxLayout(grp_sign)
        lay_sign.setSpacing(6)
        self.chk_sign = QCheckBox("Digitally Sign Output Document")
        self.chk_sign.setToolTip("Apply tamper-evident cryptographic digital signature with X.509 certificate")
        lay_sign.addWidget(self.chk_sign)

        self.frame_sign_opts = QFrame()
        lay_so = QVBoxLayout(self.frame_sign_opts)
        lay_so.setContentsMargins(0, 0, 0, 0)
        lay_so.setSpacing(6)

        row_c = QHBoxLayout()
        self.txt_sign_cert = QLineEdit()
        self.txt_sign_cert.setPlaceholderText("Path to .p12/.pfx certificate...")
        saved_c = self.db.get_setting("last_signing_cert", "")
        if saved_c and Path(saved_c).is_file():
            self.txt_sign_cert.setText(saved_c)
        row_c.addWidget(self.txt_sign_cert, stretch=1)
        btn_browse_c = QPushButton("Browse...")
        btn_browse_c.clicked.connect(self._browse_signing_cert)
        row_c.addWidget(btn_browse_c)
        lay_so.addLayout(row_c)

        self.txt_sign_pwd = QLineEdit()
        self.txt_sign_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_sign_pwd.setPlaceholderText("Certificate password")
        lay_so.addWidget(self.txt_sign_pwd)

        self.txt_sign_reason = QLineEdit("Approved")
        self.txt_sign_reason.setPlaceholderText("Signing reason (optional)")
        lay_so.addWidget(self.txt_sign_reason)

        self.txt_sign_loc = QLineEdit()
        self.txt_sign_loc.setPlaceholderText("Location (optional)")
        lay_so.addWidget(self.txt_sign_loc)

        self.chk_sign_visible = QCheckBox("Include Visual Signature Stamp")
        self.chk_sign_visible.setChecked(True)
        lay_so.addWidget(self.chk_sign_visible)

        btn_create_cert_link = QPushButton("🔑 Create Test Certificate...")
        btn_create_cert_link.setStyleSheet("font-size: 11px; color: #34d399; text-align: left; background: transparent; border: none; padding: 2px 0;")
        btn_create_cert_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create_cert_link.clicked.connect(self._open_create_cert_dialog)
        lay_so.addWidget(btn_create_cert_link)

        self.frame_sign_opts.hide()
        self.chk_sign.toggled.connect(self.frame_sign_opts.setVisible)
        lay_sign.addWidget(self.frame_sign_opts)
        panel_layout.addWidget(grp_sign)

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
    # TAB 3: DEDICATED PDF COMPRESSION & STREAM OPTIMIZATION
    # =========================================================================
    def _build_compress_tab(self) -> None:
        layout = QVBoxLayout(self.tab_compress)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        # Header
        h_box = QHBoxLayout()
        icon_lbl = QLabel("📉")
        icon_lbl.setStyleSheet("font-size: 24px;")
        h_box.addWidget(icon_lbl)
        h_text = QVBoxLayout()
        t_lbl = QLabel("Fast PDF Compression & Stream Optimization")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #60cdff;")
        s_lbl = QLabel("Shrink document size up to 80% using deep stream deflation and intelligent image downsampling.")
        s_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_text.addWidget(t_lbl)
        h_text.addWidget(s_lbl)
        h_box.addLayout(h_text)
        h_box.addStretch()
        card_layout.addLayout(h_box)

        # Source PDF Selection
        grp_source = QGroupBox("Source PDF File")
        lay_source = QHBoxLayout(grp_source)
        self.txt_compress_file = QLineEdit()
        self.txt_compress_file.setPlaceholderText("Select or drop a PDF document to compress...")
        if self._get_first_doc_path():
            self.txt_compress_file.setText(self._get_first_doc_path())
        lay_source.addWidget(self.txt_compress_file, stretch=1)
        btn_browse_comp = QPushButton("Browse...")
        btn_browse_comp.clicked.connect(self._browse_compress_file)
        lay_source.addWidget(btn_browse_comp)
        card_layout.addWidget(grp_source)

        # Compression Presets
        grp_level = QGroupBox("Compression Profile")
        lay_level = QVBoxLayout(grp_level)
        self.combo_compress_level = QComboBox()
        self.combo_compress_level.addItems([
            "Medium (Balanced — Recommended: Deflate streams & 75% quality raster media)",
            "High (Maximum Deflation — Aggressive compression for email, storage, and web sharing)",
            "Low (Gentle — Lossless stream deflation, retains 85% image quality)"
        ])
        self.combo_compress_level.setCurrentIndex(0)
        lay_level.addWidget(self.combo_compress_level)
        card_layout.addWidget(grp_level)

        # Output Destination
        grp_out = QGroupBox("Output File Destination")
        lay_out = QHBoxLayout(grp_out)
        self.txt_compress_out = QLineEdit()
        self.txt_compress_out.setPlaceholderText("Output PDF path (leave blank for automatic _compressed.pdf)...")
        lay_out.addWidget(self.txt_compress_out, stretch=1)
        btn_browse_out = QPushButton("Choose...")
        btn_browse_out.clicked.connect(self._browse_compress_out)
        lay_out.addWidget(btn_browse_out)
        card_layout.addWidget(grp_out)

        # Run action
        btn_run_compress = QPushButton("⚡ Compress PDF Now")
        btn_run_compress.setProperty("class", "primaryButton")
        btn_run_compress.setMinimumHeight(42)
        btn_run_compress.setStyleSheet("font-size: 13px; font-weight: 700;")
        btn_run_compress.clicked.connect(self._execute_compress_tab)
        card_layout.addWidget(btn_run_compress)

        layout.addWidget(card)
        layout.addStretch()

    def _browse_compress_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Compress", "", "PDF Files (*.pdf)")
        if file_path:
            self.txt_compress_file.setText(file_path)

    def _browse_compress_out(self) -> None:
        initial = self.txt_compress_out.text() or ""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Compressed PDF As", initial, "PDF Files (*.pdf)")
        if file_path:
            self.txt_compress_out.setText(file_path)

    def _execute_compress_tab(self) -> None:
        src = self.txt_compress_file.text().strip()
        if not src or not Path(src).is_file():
            QMessageBox.warning(self, "Invalid File", "Please select a valid PDF file to compress.")
            return

        out = self.txt_compress_out.text().strip()
        if not out:
            src_p = Path(src)
            out = str(src_p.parent / f"{src_p.stem}_compressed.pdf")
            self.txt_compress_out.setText(out)

        idx = self.combo_compress_level.currentIndex()
        level_map = {0: "medium", 1: "high", 2: "low"}
        profile = level_map.get(idx, "medium")

        self.progress_card.start_operation(f"Compressing {Path(src).name}...")

        def _worker_task(progress_callback=None):
            return PDFEngine.compress_pdf(
                file_path=src,
                output_path=out,
                quality_level=profile,
                progress_callback=progress_callback
            )

        def _on_success(res):
            self.progress_card.set_success("Compression complete!")
            orig_sz = format_file_size(res.get("original_size", 0))
            comp_sz = format_file_size(res.get("compressed_size", 0))
            pct = res.get("savings_percent", 0.0)
            msg = f"Successfully compressed PDF!\n\nOriginal: {orig_sz}\nCompressed: {comp_sz}\nSaved: {pct:.1f}%\n\nSaved to: {out}"
            self.db.log_operation(
                module="PDF Tools",
                action="Compress PDF",
                input_summary=Path(src).name,
                output_file=out,
                initial_size=res.get("original_size"),
                final_size=res.get("compressed_size"),
                status="success"
            )
            QMessageBox.information(self, "Compression Success", msg)

        def _on_error(err):
            self.progress_card.set_error(str(err))
            QMessageBox.critical(self, "Compression Failed", f"Could not compress PDF:\n{err}")

        worker = TaskWorker(_worker_task)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.result.connect(_on_success)
        worker.signals.error.connect(_on_error)
        self.thread_pool.start(worker)

    # =========================================================================
    # TAB 4: DEDICATED PDF PASSWORDS & SECURITY PERMISSIONS
    # =========================================================================
    def _build_protect_tab(self) -> None:
        layout = QVBoxLayout(self.tab_protect)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        # Header
        h_box = QHBoxLayout()
        icon_lbl = QLabel("🔒")
        icon_lbl.setStyleSheet("font-size: 24px;")
        h_box.addWidget(icon_lbl)
        h_text = QVBoxLayout()
        t_lbl = QLabel("PDF Security & AES-256 Encryption")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #60cdff;")
        s_lbl = QLabel("Protect documents with user passwords and fine-grained permissions (printing, copying).")
        s_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_text.addWidget(t_lbl)
        h_text.addWidget(s_lbl)
        h_box.addLayout(h_text)
        h_box.addStretch()
        card_layout.addLayout(h_box)

        # Source PDF Selection
        grp_source = QGroupBox("Source PDF File")
        lay_source = QHBoxLayout(grp_source)
        self.txt_protect_file = QLineEdit()
        self.txt_protect_file.setPlaceholderText("Select or drop a PDF document to encrypt...")
        if self._get_first_doc_path():
            self.txt_protect_file.setText(self._get_first_doc_path())
        lay_source.addWidget(self.txt_protect_file, stretch=1)
        btn_browse_prot = QPushButton("Browse...")
        btn_browse_prot.clicked.connect(self._browse_protect_file)
        lay_source.addWidget(btn_browse_prot)
        card_layout.addWidget(grp_source)

        # Passwords
        grp_pw = QGroupBox("Password Credentials")
        lay_pw = QGridLayout(grp_pw)
        lay_pw.setSpacing(10)
        lay_pw.addWidget(QLabel("User Open Password:"), 0, 0)
        self.txt_tab_user_pw = QLineEdit()
        self.txt_tab_user_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_tab_user_pw.setPlaceholderText("Required to view the document")
        lay_pw.addWidget(self.txt_tab_user_pw, 0, 1)

        lay_pw.addWidget(QLabel("Owner Permissions Password:"), 1, 0)
        self.txt_tab_owner_pw = QLineEdit()
        self.txt_tab_owner_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_tab_owner_pw.setPlaceholderText("Required to change permissions (optional, defaults to open pw)")
        lay_pw.addWidget(self.txt_tab_owner_pw, 1, 1)

        self.chk_show_passwords = QCheckBox("Show Passwords")
        self.chk_show_passwords.toggled.connect(self._toggle_show_passwords)
        lay_pw.addWidget(self.chk_show_passwords, 2, 1)
        card_layout.addWidget(grp_pw)

        # Permissions
        grp_perms = QGroupBox("Security Permissions")
        lay_perms = QVBoxLayout(grp_perms)
        self.chk_tab_allow_print = QCheckBox("Allow High-Quality Printing")
        self.chk_tab_allow_print.setChecked(True)
        self.chk_tab_allow_copy = QCheckBox("Allow Copying Text and Content")
        self.chk_tab_allow_copy.setChecked(False)
        lay_perms.addWidget(self.chk_tab_allow_print)
        lay_perms.addWidget(self.chk_tab_allow_copy)
        card_layout.addWidget(grp_perms)

        # Output Destination
        grp_out = QGroupBox("Output File Destination")
        lay_out = QHBoxLayout(grp_out)
        self.txt_protect_out = QLineEdit()
        self.txt_protect_out.setPlaceholderText("Output PDF path (leave blank for automatic _protected.pdf)...")
        lay_out.addWidget(self.txt_protect_out, stretch=1)
        btn_browse_out = QPushButton("Choose...")
        btn_browse_out.clicked.connect(self._browse_protect_out)
        lay_out.addWidget(btn_browse_out)
        card_layout.addWidget(grp_out)

        # Run action
        btn_run_protect = QPushButton("🔒 Apply AES-256 Protection")
        btn_run_protect.setProperty("class", "primaryButton")
        btn_run_protect.setMinimumHeight(42)
        btn_run_protect.setStyleSheet("font-size: 13px; font-weight: 700;")
        btn_run_protect.clicked.connect(self._execute_protect_tab)
        card_layout.addWidget(btn_run_protect)

        layout.addWidget(card)
        layout.addStretch()

    def _browse_protect_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Protect", "", "PDF Files (*.pdf)")
        if file_path:
            self.txt_protect_file.setText(file_path)

    def _browse_protect_out(self) -> None:
        initial = self.txt_protect_out.text() or ""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Protected PDF As", initial, "PDF Files (*.pdf)")
        if file_path:
            self.txt_protect_out.setText(file_path)

    def _toggle_show_passwords(self, show: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        self.txt_tab_user_pw.setEchoMode(mode)
        self.txt_tab_owner_pw.setEchoMode(mode)

    def _execute_protect_tab(self) -> None:
        src = self.txt_protect_file.text().strip()
        if not src or not Path(src).is_file():
            QMessageBox.warning(self, "Invalid File", "Please select a valid PDF file to protect.")
            return

        user_pw = self.txt_tab_user_pw.text()
        owner_pw = self.txt_tab_owner_pw.text() or user_pw
        if not user_pw and not owner_pw:
            QMessageBox.warning(self, "Missing Password", "Please specify at least a User Open Password.")
            return

        out = self.txt_protect_out.text().strip()
        if not out:
            src_p = Path(src)
            out = str(src_p.parent / f"{src_p.stem}_protected.pdf")
            self.txt_protect_out.setText(out)

        allow_print = self.chk_tab_allow_print.isChecked()
        allow_copy = self.chk_tab_allow_copy.isChecked()

        self.progress_card.start_operation(f"Encrypting {Path(src).name}...")

        def _worker_task(progress_callback=None):
            return PDFEngine.protect_pdf(
                file_path=src,
                output_path=out,
                user_password=user_pw,
                owner_password=owner_pw,
                allow_printing=allow_print,
                allow_copying=allow_copy,
                progress_callback=progress_callback
            )

        def _on_success(res):
            self.progress_card.set_success("Password encryption applied!")
            self.db.log_operation(
                module="PDF Tools",
                action="Protect PDF",
                input_summary=Path(src).name,
                output_file=out,
                status="success"
            )
            QMessageBox.information(
                self,
                "Protection Applied",
                f"Document successfully encrypted with AES-256!\n\nSaved to: {out}"
            )

        def _on_error(err):
            self.progress_card.set_error(str(err))
            QMessageBox.critical(self, "Protection Failed", f"Could not protect PDF:\n{err}")

        worker = TaskWorker(_worker_task)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.result.connect(_on_success)
        worker.signals.error.connect(_on_error)
        self.thread_pool.start(worker)

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

        if new_docs:
            first_path = new_docs[0]["file_path"]
            if hasattr(self, "txt_compress_file") and not self.txt_compress_file.text():
                self.txt_compress_file.setText(first_path)
            if hasattr(self, "txt_protect_file") and not self.txt_protect_file.text():
                self.txt_protect_file.setText(first_path)

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

        sign_cert = self.txt_sign_cert.text().strip() if self.chk_sign.isChecked() else None
        sign_pwd = self.txt_sign_pwd.text() if self.chk_sign.isChecked() else None
        sign_reason = self.txt_sign_reason.text().strip() if self.chk_sign.isChecked() else None
        sign_loc = self.txt_sign_loc.text().strip() if self.chk_sign.isChecked() else None
        sign_vis = self.chk_sign_visible.isChecked() if self.chk_sign.isChecked() else False

        if self.chk_sign.isChecked() and not sign_cert:
            QMessageBox.warning(
                self, "Missing Certificate",
                "Please provide a valid signing certificate (.p12/.pfx) or uncheck 'Digitally Sign Output Document'."
            )
            return

        if self.chk_sign.isChecked() and self.chk_protect.isChecked():
            QMessageBox.warning(
                self, "Conflicting Security Options",
                "Cannot apply digital signature and AES-256 password encryption simultaneously.\n"
                "Digital signatures require unencrypted content to maintain cryptographic integrity."
            )
            return

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
            sign_certificate_path=sign_cert,
            sign_password=sign_pwd,
            sign_reason=sign_reason,
            sign_location=sign_loc,
            sign_visible=sign_vis,
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
        is_signed = result.get("signed", False)
        self.db.add_history(
            operation="Ready PDF Export",
            source_file=Path(self.loaded_documents[0]["file_path"]).name if self.loaded_documents else "Multi-PDF",
            output_file=out_file,
            details=f"Exported {pages_count} pages (Size: {size_str}, Compressed: {result['compressed']}, Protected: {result['protected']}, Signed: {is_signed})"
        )

        signed_note = "\n🔏 Cryptographically digitally signed (PAdES)." if is_signed else ""
        msg = f"Ready PDF successfully exported!{signed_note}\n\nPages: {pages_count}\nOutput Size: {size_str}\nPath: {out_file}"
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

    # =========================================================================
    # TAB 4: DIGITAL SIGNING & VERIFICATION SUITE
    # =========================================================================
    def _build_signing_tab(self) -> None:
        layout = QVBoxLayout(self.tab_sign)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header card
        header_card = QFrame()
        header_card.setProperty("class", "cardFrame")
        header_card.setStyleSheet("""
            QFrame {
                background-color: #151821;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        h_lay = QHBoxLayout(header_card)
        h_text = QVBoxLayout()
        lbl_t = QLabel("🔏 Cryptographic PDF Digital Signatures & Validation")
        lbl_t.setStyleSheet("font-size: 15px; font-weight: bold; color: #60a5fa;")
        lbl_d = QLabel("Verify PAdES / PKCS#7 signatures, detect document modifications, and sign files with X.509 certificates.")
        lbl_d.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_text.addWidget(lbl_t)
        h_text.addWidget(lbl_d)
        h_lay.addLayout(h_text, stretch=1)

        btn_open_full_suite = QPushButton("🚀 Open Full Signature Center...")
        btn_open_full_suite.setProperty("class", "primaryButton")
        btn_open_full_suite.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 8px 16px; border-radius: 6px;"
        )
        btn_open_full_suite.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_full_suite.clicked.connect(self._open_digital_signature_suite)
        h_lay.addWidget(btn_open_full_suite)
        layout.addWidget(header_card)

        # Splitter for Verifier (Left) and Signer (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left: Quick Signature Verifier ---
        pane_verify = QFrame()
        pane_verify.setProperty("class", "cardFrame")
        pane_verify.setStyleSheet("background-color: #181a20; border: 1px solid #282a32; border-radius: 6px; padding: 10px;")
        v_lay = QVBoxLayout(pane_verify)
        v_lay.setSpacing(8)

        lbl_v_title = QLabel("🔍 Signature Inspector & Tamper Check")
        lbl_v_title.setStyleSheet("font-weight: bold; color: #e2e8f0; font-size: 13px;")
        v_lay.addWidget(lbl_v_title)

        row_v_file = QHBoxLayout()
        self.txt_tab_verify_file = QLineEdit()
        self.txt_tab_verify_file.setPlaceholderText("Select PDF to inspect...")
        if self._get_first_doc_path():
            self.txt_tab_verify_file.setText(self._get_first_doc_path())
        row_v_file.addWidget(self.txt_tab_verify_file, stretch=1)
        btn_browse_v = QPushButton("Browse...")
        btn_browse_v.clicked.connect(self._browse_tab_verify_file)
        row_v_file.addWidget(btn_browse_v)
        btn_do_verify = QPushButton("Verify")
        btn_do_verify.setStyleSheet("background-color: #0369a1; color: white; font-weight: 600; padding: 4px 10px;")
        btn_do_verify.clicked.connect(self._execute_tab_verify)
        row_v_file.addWidget(btn_do_verify)
        v_lay.addLayout(row_v_file)

        self.lbl_tab_verify_banner = QLabel("No document verified yet.")
        self.lbl_tab_verify_banner.setStyleSheet("background-color: #1e222b; border: 1px solid #334155; border-radius: 4px; padding: 8px; color: #cbd5e1; font-weight: 500;")
        self.lbl_tab_verify_banner.setWordWrap(True)
        v_lay.addWidget(self.lbl_tab_verify_banner)

        self.table_tab_signatures = QTableWidget(0, 3)
        self.table_tab_signatures.setHorizontalHeaderLabels(["Field", "Signer Common Name", "Status"])
        self.table_tab_signatures.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tab_signatures.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_tab_signatures.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        v_lay.addWidget(self.table_tab_signatures, stretch=1)
        splitter.addWidget(pane_verify)

        # --- Right: Quick Signer ---
        pane_sign = QFrame()
        pane_sign.setProperty("class", "cardFrame")
        pane_sign.setStyleSheet("background-color: #181a20; border: 1px solid #282a32; border-radius: 6px; padding: 10px;")
        s_lay = QVBoxLayout(pane_sign)
        s_lay.setSpacing(8)

        lbl_s_title = QLabel("✍️ Direct Digital Signer")
        lbl_s_title.setStyleSheet("font-weight: bold; color: #e2e8f0; font-size: 13px;")
        s_lay.addWidget(lbl_s_title)

        row_s_in = QHBoxLayout()
        row_s_in.addWidget(QLabel("PDF File:"))
        self.txt_tab_sign_in = QLineEdit()
        self.txt_tab_sign_in.setPlaceholderText("PDF to sign...")
        if self._get_first_doc_path():
            self.txt_tab_sign_in.setText(self._get_first_doc_path())
        row_s_in.addWidget(self.txt_tab_sign_in, stretch=1)
        btn_s_in = QPushButton("Browse...")
        btn_s_in.clicked.connect(self._browse_tab_sign_in)
        row_s_in.addWidget(btn_s_in)
        s_lay.addLayout(row_s_in)

        row_s_cert = QHBoxLayout()
        row_s_cert.addWidget(QLabel("Certificate:"))
        self.txt_tab_sign_cert = QLineEdit()
        self.txt_tab_sign_cert.setPlaceholderText("Path to .p12/.pfx...")
        saved_c = self.db.get_setting("last_signing_cert", "")
        if saved_c and Path(saved_c).is_file():
            self.txt_tab_sign_cert.setText(saved_c)
        row_s_cert.addWidget(self.txt_tab_sign_cert, stretch=1)
        btn_s_c = QPushButton("Browse...")
        btn_s_c.clicked.connect(self._browse_tab_sign_cert)
        row_s_cert.addWidget(btn_s_c)
        s_lay.addLayout(row_s_cert)

        row_s_pwd = QHBoxLayout()
        row_s_pwd.addWidget(QLabel("Password:"))
        self.txt_tab_sign_pwd = QLineEdit()
        self.txt_tab_sign_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_tab_sign_pwd.setPlaceholderText("Certificate password")
        row_s_pwd.addWidget(self.txt_tab_sign_pwd, stretch=1)
        s_lay.addLayout(row_s_pwd)

        row_s_meta = QHBoxLayout()
        row_s_meta.addWidget(QLabel("Reason:"))
        self.txt_tab_sign_reason = QLineEdit("Approved")
        row_s_meta.addWidget(self.txt_tab_sign_reason, stretch=1)
        row_s_meta.addWidget(QLabel("Location:"))
        self.txt_tab_sign_loc = QLineEdit()
        self.txt_tab_sign_loc.setPlaceholderText("City, Country")
        row_s_meta.addWidget(self.txt_tab_sign_loc, stretch=1)
        s_lay.addLayout(row_s_meta)

        self.chk_tab_sign_vis = QCheckBox("Place Visual Signature Stamp on Page")
        self.chk_tab_sign_vis.setChecked(True)
        s_lay.addWidget(self.chk_tab_sign_vis)

        row_s_actions = QHBoxLayout()
        btn_create_cert = QPushButton("🔑 Create New Certificate...")
        btn_create_cert.setStyleSheet("color: #34d399; font-size: 11px; background: transparent; border: none;")
        btn_create_cert.clicked.connect(self._open_create_cert_dialog)
        row_s_actions.addWidget(btn_create_cert)
        row_s_actions.addStretch()

        btn_run_sign = QPushButton("✍️ Sign PDF Now...")
        btn_run_sign.setProperty("class", "primaryButton")
        btn_run_sign.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 6px 14px; border-radius: 4px;")
        btn_run_sign.clicked.connect(self._execute_tab_sign)
        row_s_actions.addWidget(btn_run_sign)
        s_lay.addLayout(row_s_actions)
        s_lay.addStretch()

        splitter.addWidget(pane_sign)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

    # --- Digital Signature Event Handlers ---
    def _open_digital_signature_suite(self) -> None:
        first_doc = self._get_first_doc_path()
        dialog = DigitalSignatureDialog(
            parent=self,
            initial_pdf_path=first_doc,
            database=self.db,
            thread_pool=self.thread_pool,
        )
        dialog.signature_applied.connect(self._on_signature_applied_from_dialog)
        dialog.exec()

    def _open_create_cert_dialog(self) -> None:
        dialog = DigitalSignatureDialog(
            parent=self,
            database=self.db,
            thread_pool=self.thread_pool,
        )
        dialog.tabs.setCurrentIndex(2)  # Certificate generator tab
        dialog.exec()

    def _browse_signing_cert(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Signing Certificate", "", "PKCS#12 Bundles (*.p12 *.pfx);;All Files (*.*)"
        )
        if path:
            self.txt_sign_cert.setText(path)
            self.db.set_setting("last_signing_cert", path)

    def _browse_tab_verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to Inspect", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.txt_tab_verify_file.setText(path)
            self._execute_tab_verify()

    def _browse_tab_sign_in(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to Sign", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.txt_tab_sign_in.setText(path)

    def _browse_tab_sign_cert(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Certificate", "", "PKCS#12 Bundles (*.p12 *.pfx);;All Files (*.*)"
        )
        if path:
            self.txt_tab_sign_cert.setText(path)
            self.db.set_setting("last_signing_cert", path)

    def _execute_tab_verify(self) -> None:
        file_path = self.txt_tab_verify_file.text().strip()
        if not file_path or not Path(file_path).is_file():
            QMessageBox.warning(self, "Invalid File", "Please select a valid PDF file.")
            return

        try:
            results = PDFEngine.verify_signatures(file_path)
            self.table_tab_signatures.setRowCount(0)

            if not results:
                self.lbl_tab_verify_banner.setText("⚪ No digital signatures found in this document.")
                self.lbl_tab_verify_banner.setStyleSheet("background-color: #1e222b; border: 1px solid #475569; border-radius: 4px; padding: 8px; color: #94a3b8;")
                return

            has_tampered = any(r.get("tampered") or not r.get("intact") for r in results)
            all_valid = all(r.get("is_valid") for r in results)

            if has_tampered:
                self.lbl_tab_verify_banner.setText("🚨 TAMPER ALERT: Document was altered or modified after signing!")
                self.lbl_tab_verify_banner.setStyleSheet("background-color: #450a0a; border: 1px solid #ef4444; border-radius: 4px; padding: 8px; color: #f87171; font-weight: bold;")
            elif all_valid:
                self.lbl_tab_verify_banner.setText(f"🛡️ VALID & INTACT ({len(results)} signature{'s' if len(results) > 1 else ''}). No modifications detected.")
                self.lbl_tab_verify_banner.setStyleSheet("background-color: #064e3b; border: 1px solid #10b981; border-radius: 4px; padding: 8px; color: #6ee7b7; font-weight: bold;")
            else:
                self.lbl_tab_verify_banner.setText("⚠️ Signatures found with warnings or untrusted root certificate.")
                self.lbl_tab_verify_banner.setStyleSheet("background-color: #451a03; border: 1px solid #f59e0b; border-radius: 4px; padding: 8px; color: #fcd34d;")

            for row, r in enumerate(results):
                self.table_tab_signatures.insertRow(row)
                self.table_tab_signatures.setItem(row, 0, QTableWidgetItem(r.get("field_name") or "Sig"))
                self.table_tab_signatures.setItem(row, 1, QTableWidgetItem(r.get("signer_name") or "Unknown"))
                intact = r.get("intact") and not r.get("tampered")
                st_item = QTableWidgetItem("✅ Intact" if intact else "❌ Modified")
                st_item.setForeground(Qt.GlobalColor.green if intact else Qt.GlobalColor.red)
                self.table_tab_signatures.setItem(row, 2, st_item)

        except Exception as exc:
            QMessageBox.critical(self, "Verification Failed", f"Could not verify signatures:\n{exc}")

    def _execute_tab_sign(self) -> None:
        in_pdf = self.txt_tab_sign_in.text().strip()
        cert_p = self.txt_tab_sign_cert.text().strip()
        pwd = self.txt_tab_sign_pwd.text()
        reason = self.txt_tab_sign_reason.text().strip()
        location = self.txt_tab_sign_loc.text().strip()
        visible = self.chk_tab_sign_vis.isChecked()

        if not in_pdf or not Path(in_pdf).is_file():
            QMessageBox.warning(self, "Missing Document", "Please select a valid PDF to sign.")
            return

        if not cert_p or not Path(cert_p).is_file():
            QMessageBox.warning(self, "Missing Certificate", "Please select a valid .p12/.pfx certificate.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Signed PDF", str(Path(in_pdf).parent / f"{Path(in_pdf).stem}_signed.pdf"), "PDF Documents (*.pdf)"
        )
        if not out_path:
            return

        self.progress_card.start_task("Digitally signing document...")

        def _do_sign(progress_callback=None):
            return PDFEngine.sign_pdf(
                file_path=in_pdf,
                output_path=out_path,
                certificate_path=cert_p,
                password=pwd,
                reason=reason,
                location=location,
                visible=visible,
                progress_callback=progress_callback,
            )

        worker = TaskWorker(_do_sign)
        worker.signals.progress.connect(self.progress_card.update_progress)
        worker.signals.finished.connect(lambda res: self._on_tab_sign_success(res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Digital Signing Failed", err))
        self.thread_pool.start(worker)

    def _on_tab_sign_success(self, res: Dict[str, Any]) -> None:
        out_file = res["output_file"]
        signer = res.get("signer_name") or "Signer"
        self.db.add_recent_file(out_file, file_type="pdf")
        self.db.log_operation(
            module="Digital Signature",
            action="Direct Sign PDF",
            input_summary=f"Signed as {signer}",
            output_file=out_file,
            status="success",
        )
        self._on_operation_done(
            "Document Signed",
            f"Successfully applied cryptographic digital signature!\n\nSigner: {signer}\nOutput: {out_file}",
            out_file
        )
        self.txt_tab_verify_file.setText(out_file)
        self._execute_tab_verify()

    def _on_signature_applied_from_dialog(self, out_path: str) -> None:
        self.db.add_recent_file(out_path, file_type="pdf")
        self.txt_tab_verify_file.setText(out_path)
        self._execute_tab_verify()
