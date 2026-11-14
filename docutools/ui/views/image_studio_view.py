"""
Image Studio View for DocuTools.
Features:
- Single Image Studio: Live preview, aspect ratio locked resizing, cropping presets,
  Target-size iterative compression (50 KB, 100 KB, 200 KB, custom KB), before/after size metrics
- Batch Optimizer: Multi-image queue, batch resizing, format conversion, target size compression,
  and comprehensive savings summary table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QPixmap
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
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.image_engine import ImageEngine
from docutools.core.validator import format_file_size, validate_file
from docutools.ui.components.drop_zone import DropZone
from docutools.ui.components.progress_card import ProgressCard
from docutools.workers.batch_worker import BatchWorker
from docutools.workers.task_worker import TaskWorker


class ImageStudioView(QWidget):
    """Integrated Image Studio module view."""

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool

        self.current_image_path: Optional[str] = None
        self.orig_width: int = 0
        self.orig_height: int = 0
        self.orig_aspect_ratio: float = 1.0

        self.batch_files: List[str] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Image Studio")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Resize, crop, and compress images with target-size binary search optimization.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.btn_open_img = QPushButton("📂 Open Image...")
        self.btn_open_img.setProperty("class", "primaryButton")
        self.btn_open_img.clicked.connect(self._select_image_dialog)
        header_row.addWidget(self.btn_open_img)

        main_layout.addLayout(header_row)

        # Progress Card
        self.progress_card = ProgressCard()
        main_layout.addWidget(self.progress_card)

        # Tabs: Single Image vs Batch Optimizer
        self.tabs = QTabWidget()
        self.tab_single = QWidget()
        self.tab_batch = QWidget()
        self.tabs.addTab(self.tab_single, "🖼 Single Image Studio")
        self.tabs.addTab(self.tab_batch, "📦 Batch Optimizer")
        main_layout.addWidget(self.tabs, stretch=1)

        self._build_single_tab()
        self._build_batch_tab()

    # --- TAB 1: Single Image Studio ---
    def _build_single_tab(self) -> None:
        layout = QHBoxLayout(self.tab_single)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        # Left Column: Image Preview
        left_col = QVBoxLayout()
        self.single_drop = DropZone(
            title="Drop Image to Optimize",
            subtitle="JPG, PNG, WebP, BMP, TIFF supported",
            file_filter="Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)",
            multi_select=False
        )
        self.single_drop.files_dropped.connect(lambda files: self.load_image(files[0]))
        left_col.addWidget(self.single_drop)

        # Preview Container
        self.preview_frame = QFrame()
        self.preview_frame.setProperty("class", "cardFrame")
        prev_lay = QVBoxLayout(self.preview_frame)
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setMinimumSize(320, 280)
        prev_lay.addWidget(self.lbl_preview)

        self.lbl_img_details = QLabel()
        self.lbl_img_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img_details.setStyleSheet("color: #9ca3af; font-size: 11px;")
        prev_lay.addWidget(self.lbl_img_details)

        self.preview_frame.hide()
        left_col.addWidget(self.preview_frame, stretch=1)

        # Before / After Stats Card
        self.single_stats_frame = QFrame()
        self.single_stats_frame.setStyleSheet("background-color: #17181c; border-radius: 8px; padding: 10px;")
        stat_lay = QHBoxLayout(self.single_stats_frame)
        self.lbl_single_orig = QLabel("Original: -")
        self.lbl_single_new = QLabel("Optimized: -")
        self.lbl_single_pct = QLabel("Savings: -")
        self.lbl_single_pct.setStyleSheet("font-weight: bold; color: #22c55e;")
        stat_lay.addWidget(self.lbl_single_orig)
        stat_lay.addWidget(self.lbl_single_new)
        stat_lay.addWidget(self.lbl_single_pct)
        left_col.addWidget(self.single_stats_frame)

        layout.addLayout(left_col, stretch=1)

        # Right Column: Controls Panel
        scroll_controls = QScrollArea()
        scroll_controls.setWidgetResizable(True)
        scroll_controls.setFixedWidth(380)
        controls_widget = QWidget()
        right_col = QVBoxLayout(controls_widget)
        right_col.setContentsMargins(8, 8, 8, 8)
        right_col.setSpacing(12)

        # 1. Resize Group
        grp_resize = QGroupBox("1. Resize & Dimensions")
        lay_res = QVBoxLayout(grp_resize)
        lay_res.setSpacing(8)

        # Width & Height
        row_dim = QHBoxLayout()
        row_dim.addWidget(QLabel("Width:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 15000)
        self.spin_width.setValue(1920)
        self.spin_width.valueChanged.connect(self._on_width_changed)
        row_dim.addWidget(self.spin_width)

        row_dim.addWidget(QLabel("Height:"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 15000)
        self.spin_height.setValue(1080)
        self.spin_height.valueChanged.connect(self._on_height_changed)
        row_dim.addWidget(self.spin_height)
        lay_res.addLayout(row_dim)

        self.chk_aspect = QCheckBox("Lock Aspect Ratio")
        self.chk_aspect.setChecked(True)
        lay_res.addWidget(self.chk_aspect)

        # Scaling buttons (25%, 50%, 75%, 200%)
        btn_scale_row = QHBoxLayout()
        for scale_val in [25, 50, 75, 200]:
            btn_s = QPushButton(f"{scale_val}%")
            btn_s.clicked.connect(lambda chk=False, s=scale_val: self._apply_scale_preset(s))
            btn_scale_row.addWidget(btn_s)
        lay_res.addLayout(btn_scale_row)
        right_col.addWidget(grp_resize)

        # 2. Compression Mode: Target Size vs Quality
        grp_comp = QGroupBox("2. Compression & Target File Size")
        lay_comp = QVBoxLayout(grp_comp)
        lay_comp.setSpacing(8)

        self.radio_target_size = QRadioButton("Target Exact File Size (Iterative Optimizer)")
        self.radio_target_size.setChecked(True)
        self.radio_target_size.toggled.connect(self._toggle_compression_mode)
        lay_comp.addWidget(self.radio_target_size)

        # Target presets row
        self.target_box = QFrame()
        lay_target = QVBoxLayout(self.target_box)
        lay_target.setContentsMargins(4, 2, 4, 4)
        target_preset_row = QHBoxLayout()
        target_preset_row.addWidget(QLabel("Target Size:"))
        self.combo_target_preset = QComboBox()
        self.combo_target_preset.addItems(["50 KB", "100 KB", "200 KB", "500 KB", "Custom KB"])
        self.combo_target_preset.setCurrentIndex(1)
        self.combo_target_preset.currentIndexChanged.connect(self._on_target_preset_changed)
        target_preset_row.addWidget(self.combo_target_preset)

        self.spin_custom_kb = QSpinBox()
        self.spin_custom_kb.setRange(5, 50000)
        self.spin_custom_kb.setValue(100)
        self.spin_custom_kb.setSuffix(" KB")
        self.spin_custom_kb.setEnabled(False)
        target_preset_row.addWidget(self.spin_custom_kb)
        lay_target.addLayout(target_preset_row)
        lay_comp.addWidget(self.target_box)

        # Manual Quality Slider
        self.radio_quality = QRadioButton("Manual Quality Slider")
        self.radio_quality.toggled.connect(self._toggle_compression_mode)
        lay_comp.addWidget(self.radio_quality)

        self.quality_box = QFrame()
        lay_q = QHBoxLayout(self.quality_box)
        lay_q.setContentsMargins(4, 2, 4, 4)
        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(1, 100)
        self.slider_quality.setValue(85)
        self.lbl_quality_val = QLabel("85%")
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_quality_val.setText(f"{v}%"))
        lay_q.addWidget(self.slider_quality)
        lay_q.addWidget(self.lbl_quality_val)
        self.quality_box.setEnabled(False)
        lay_comp.addWidget(self.quality_box)
        right_col.addWidget(grp_comp)

        # 3. Output Format
        grp_fmt = QGroupBox("3. Output Format")
        lay_fmt = QHBoxLayout(grp_fmt)
        lay_fmt.addWidget(QLabel("Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["Auto / Keep Original", "JPEG", "PNG", "WEBP", "BMP"])
        lay_fmt.addWidget(self.combo_format)
        right_col.addWidget(grp_fmt)

        # Action Button
        self.btn_save_single = QPushButton("💾 Process & Save Image...")
        self.btn_save_single.setProperty("class", "primaryButton")
        self.btn_save_single.setMinimumHeight(40)
        self.btn_save_single.clicked.connect(self._execute_single_process)
        right_col.addWidget(self.btn_save_single)

        right_col.addStretch()
        scroll_controls.setWidget(controls_widget)
        layout.addWidget(scroll_controls)

    # --- TAB 2: Batch Optimizer ---
    def _build_batch_tab(self) -> None:
        layout = QVBoxLayout(self.tab_batch)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Drop zone
        drop_batch = DropZone(
            title="Drop multiple images to batch optimize",
            subtitle="Resize, convert, and compress large collections of photos simultaneously",
            file_filter="Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)",
            multi_select=True
        )
        drop_batch.files_dropped.connect(self._add_batch_files)
        layout.addWidget(drop_batch)

        # Batch Queue Table
        self.table_batch = QTableWidget(0, 5)
        self.table_batch.setHorizontalHeaderLabels(["File Name", "Original Size", "Optimized Size", "Savings", "Status"])
        self.table_batch.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_batch, stretch=1)

        # Batch settings row
        settings_frame = QFrame()
        settings_frame.setProperty("class", "cardFrame")
        set_lay = QHBoxLayout(settings_frame)
        set_lay.setContentsMargins(8, 8, 8, 8)

        set_lay.addWidget(QLabel("Batch Target Size:"))
        self.combo_batch_target = QComboBox()
        self.combo_batch_target.addItems(["50 KB", "100 KB", "200 KB", "500 KB", "Keep Original Quality"])
        self.combo_batch_target.setCurrentIndex(1)
        set_lay.addWidget(self.combo_batch_target)

        set_lay.addWidget(QLabel("Output Format:"))
        self.combo_batch_fmt = QComboBox()
        self.combo_batch_fmt.addItems(["Keep Original", "JPEG", "PNG", "WEBP"])
        set_lay.addWidget(self.combo_batch_fmt)

        btn_clear_batch = QPushButton("Clear Queue")
        btn_clear_batch.clicked.connect(self._clear_batch)
        set_lay.addWidget(btn_clear_batch)

        set_lay.addStretch()

        self.btn_run_batch = QPushButton("▶ Start Batch Processing...")
        self.btn_run_batch.setProperty("class", "successButton")
        self.btn_run_batch.setMinimumHeight(36)
        self.btn_run_batch.clicked.connect(self._execute_batch)
        set_lay.addWidget(self.btn_run_batch)

        layout.addWidget(settings_frame)

    # --- Single Image Logic ---
    def _select_image_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path: str) -> None:
        is_valid, msg = validate_file(file_path, expected_type="image")
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", msg)
            return

        self.current_image_path = file_path
        self.single_drop.hide()
        self.preview_frame.show()

        # Load info & preview
        info = ImageEngine.get_image_info(file_path)
        self.orig_width = info["width"]
        self.orig_height = info["height"]
        self.orig_aspect_ratio = info["aspect_ratio"]

        # Update spinboxes without triggering loop
        self.spin_width.blockSignals(True)
        self.spin_height.blockSignals(True)
        self.spin_width.setValue(self.orig_width)
        self.spin_height.setValue(self.orig_height)
        self.spin_width.blockSignals(False)
        self.spin_height.blockSignals(False)

        # Update preview pixmap
        px = QPixmap(file_path)
        scaled = px.scaled(
            self.lbl_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_preview.setPixmap(scaled)

        self.lbl_img_details.setText(
            f"{info['file_name']} — {self.orig_width}×{self.orig_height} px | {info['format']} | {format_file_size(info['file_size'])}"
        )
        self.lbl_single_orig.setText(f"Original: {format_file_size(info['file_size'])}")
        self.db.add_recent_file(file_path, "image")

    def _on_width_changed(self, new_width: int) -> None:
        if self.chk_aspect.isChecked() and self.orig_width > 0:
            new_height = max(1, int(new_width / self.orig_aspect_ratio))
            self.spin_height.blockSignals(True)
            self.spin_height.setValue(new_height)
            self.spin_height.blockSignals(False)

    def _on_height_changed(self, new_height: int) -> None:
        if self.chk_aspect.isChecked() and self.orig_height > 0:
            new_width = max(1, int(new_height * self.orig_aspect_ratio))
            self.spin_width.blockSignals(True)
            self.spin_width.setValue(new_width)
            self.spin_width.blockSignals(False)

    def _apply_scale_preset(self, pct: int) -> None:
        if self.orig_width > 0:
            scale = pct / 100.0
            w = max(1, int(self.orig_width * scale))
            h = max(1, int(self.orig_height * scale))
            self.spin_width.setValue(w)
            self.spin_height.setValue(h)

    def _toggle_compression_mode(self) -> None:
        is_target = self.radio_target_size.isChecked()
        self.target_box.setEnabled(is_target)
        self.quality_box.setEnabled(not is_target)

    def _on_target_preset_changed(self, index: int) -> None:
        preset_map = {0: 50, 1: 100, 2: 200, 3: 500}
        if index in preset_map:
            self.spin_custom_kb.setValue(preset_map[index])
            self.spin_custom_kb.setEnabled(False)
        else:
            self.spin_custom_kb.setEnabled(True)

    def _execute_single_process(self) -> None:
        if not self.current_image_path:
            self._select_image_dialog()
            if not self.current_image_path:
                return

        # Determine target extension
        fmt_choice = self.combo_format.currentText()
        orig_ext = Path(self.current_image_path).suffix
        if fmt_choice == "Auto / Keep Original":
            dest_ext = orig_ext
            dest_fmt = None
        else:
            dest_ext = f".{fmt_choice.lower()}"
            dest_fmt = fmt_choice

        default_name = f"{Path(self.current_image_path).stem}_optimized{dest_ext}"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Optimized Image", default_name, f"Image (*{dest_ext})"
        )
        if not out_path:
            return

        w = self.spin_width.value()
        h = self.spin_height.value()
        target_kb = self.spin_custom_kb.value() if self.radio_target_size.isChecked() else None
        quality = self.slider_quality.value() if not self.radio_target_size.isChecked() else None

        self.progress_card.start_task("Optimizing Image...")

        worker = TaskWorker(
            ImageEngine.process_single_image,
            input_path=self.current_image_path,
            output_path=out_path,
            target_width=w,
            target_height=h,
            maintain_aspect_ratio=self.chk_aspect.isChecked(),
            output_format=dest_fmt,
            quality=quality,
            target_kb=target_kb
        )
        worker.signals.finished.connect(self._on_single_image_finished)
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Optimization Failed", err))
        self.thread_pool.start(worker)

    def _on_single_image_finished(self, stats: Dict[str, Any]) -> None:
        self.lbl_single_orig.setText(f"Original: {format_file_size(stats['initial_size'])}")
        self.lbl_single_new.setText(f"Optimized: {format_file_size(stats['final_size'])}")
        self.lbl_single_pct.setText(f"Saved: {stats['savings_percent']:.1f}% ({format_file_size(stats['savings_bytes'])})")
        self.progress_card.complete_task("Image optimized and saved successfully.")
        self.db.add_recent_file(stats["output_file"], "image")
        self.db.log_operation(
            "Image Studio", "Optimized Image",
            output_file=stats["output_file"],
            initial_size=stats["initial_size"],
            final_size=stats["final_size"],
            status="success"
        )
        QMessageBox.information(
            self, "Optimization Complete",
            f"Image saved successfully!\nSize: {format_file_size(stats['final_size'])} ({stats['savings_percent']:.1f}% reduction)"
        )

    # --- Batch Handlers ---
    def _add_batch_files(self, files: List[str]) -> None:
        for f in files:
            p = Path(f)
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"] and str(p) not in self.batch_files:
                self.batch_files.append(str(p))
        self._refresh_batch_table()

    def _refresh_batch_table(self) -> None:
        self.table_batch.setRowCount(len(self.batch_files))
        for row, f_str in enumerate(self.batch_files):
            p = Path(f_str)
            item_name = QTableWidgetItem(p.name)
            item_orig = QTableWidgetItem(format_file_size(p.stat().st_size) if p.exists() else "0 B")
            item_new = QTableWidgetItem("-")
            item_save = QTableWidgetItem("-")
            item_status = QTableWidgetItem("Queued")

            self.table_batch.setItem(row, 0, item_name)
            self.table_batch.setItem(row, 1, item_orig)
            self.table_batch.setItem(row, 2, item_new)
            self.table_batch.setItem(row, 3, item_save)
            self.table_batch.setItem(row, 4, item_status)

    def _clear_batch(self) -> None:
        self.batch_files.clear()
        self._refresh_batch_table()

    def _execute_batch(self) -> None:
        if not self.batch_files:
            QMessageBox.warning(self, "Batch Empty", "Please drop or select images to process in batch.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Batch Images")
        if not out_dir:
            return

        # Target size
        target_map = {0: 50, 1: 100, 2: 200, 3: 500, 4: None}
        target_kb = target_map.get(self.combo_batch_target.currentIndex())

        fmt = self.combo_batch_fmt.currentText()
        dest_fmt = None if fmt == "Keep Original" else fmt

        self.progress_card.start_task(f"Processing Batch of {len(self.batch_files)} Images...")

        def batch_process_fn(file_path: str, progress_cb):
            p = Path(file_path)
            ext = f".{dest_fmt.lower()}" if dest_fmt else p.suffix
            out_file = Path(out_dir) / f"{p.stem}_opt{ext}"
            return ImageEngine.process_single_image(
                input_path=p,
                output_path=out_file,
                output_format=dest_fmt,
                target_kb=target_kb
            )

        batch_worker = BatchWorker(self.batch_files, batch_process_fn)
        batch_worker.signals.item_finished.connect(self._on_batch_item_finished)
        batch_worker.signals.all_finished.connect(self._on_batch_all_finished)
        self.thread_pool.start(batch_worker)

    def _on_batch_item_finished(self, row: int, result: Dict[str, Any]) -> None:
        if row < self.table_batch.rowCount():
            self.table_batch.setItem(row, 2, QTableWidgetItem(format_file_size(result["final_size"])))
            self.table_batch.setItem(row, 3, QTableWidgetItem(f"-{result['savings_percent']:.1f}%"))
            item_status = QTableWidgetItem("Completed")
            item_status.setForeground(Qt.GlobalColor.green)
            self.table_batch.setItem(row, 4, item_status)

    def _on_batch_all_finished(self, all_results: List[Any]) -> None:
        self.progress_card.complete_task(f"All {len(all_results)} images processed successfully!")
        self.db.log_operation("Image Studio", "Batch Optimization", status="success")
        QMessageBox.information(self, "Batch Complete", f"Successfully processed all {len(all_results)} images!")

    def _on_worker_error(self, title: str, error_msg: str) -> None:
        self.progress_card.fail_task(error_msg)
        self.db.log_operation("Image Studio", title, status="error", error_message=error_msg)
        QMessageBox.critical(self, title, f"An error occurred:\n{error_msg}")
