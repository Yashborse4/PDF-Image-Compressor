"""
Conversion Center View for DocuTools.
Unified file format converter between PDF, DOCX, and image formats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.conversion_engine import ConversionEngine
from docutools.core.database import Database
from docutools.core.validator import format_file_size, get_file_type
from docutools.ui.components.drop_zone import DropZone
from docutools.ui.components.progress_card import ProgressCard
from docutools.workers.batch_worker import BatchWorker
from docutools.workers.task_worker import TaskWorker


class ConversionView(QWidget):
    """Universal Conversion Center."""

    CONVERSION_MODES = [
        ("PDF to Images", "pdf", ["PNG", "JPEG", "WEBP"]),
        ("Images to PDF", "image", ["PDF (Combined)", "PDF (Separate)"]),
        ("DOCX to PDF", "docx", ["PDF"]),
        ("PDF to Text", "pdf", ["TXT"]),
        ("Image Format Converter", "image", ["PNG", "JPEG", "WEBP", "BMP", "TIFF"]),
    ]

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool
        self.queue_files: List[str] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Conversion Center")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Convert seamlessly between PDF, DOCX, and high-resolution images.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        # Progress Card
        self.progress_card = ProgressCard()
        main_layout.addWidget(self.progress_card)

        # Mode Selection Bar
        mode_frame = QFrame()
        mode_frame.setProperty("class", "cardFrame")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(10, 8, 10, 8)
        mode_layout.addWidget(QLabel("Conversion Pipeline:"))

        self.combo_mode = QComboBox()
        for mode_title, _, _ in self.CONVERSION_MODES:
            self.combo_mode.addItem(mode_title)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.combo_mode)

        mode_layout.addWidget(QLabel("Target Format:"))
        self.combo_target_fmt = QComboBox()
        mode_layout.addWidget(self.combo_target_fmt)

        # DPI option (for PDF to Image)
        self.lbl_dpi = QLabel("DPI:")
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setValue(200)
        mode_layout.addWidget(self.lbl_dpi)
        mode_layout.addWidget(self.spin_dpi)

        mode_layout.addStretch()
        main_layout.addWidget(mode_frame)

        # Drop Zone
        self.drop_zone = DropZone(
            title="Drop files here to convert",
            subtitle="Queue documents or images for one-click background conversion",
            file_filter="All Supported Files (*.pdf *.docx *.png *.jpg *.jpeg *.webp *.bmp *.tiff)",
            multi_select=True
        )
        self.drop_zone.files_dropped.connect(self._add_files_to_queue)
        main_layout.addWidget(self.drop_zone)

        # Conversion Queue Table
        self.table_queue = QTableWidget(0, 5)
        self.table_queue.setHorizontalHeaderLabels(["File Name", "Type", "File Size", "Target", "Status"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table_queue, stretch=1)

        # Bottom Bar: Output directory + Convert Button
        bottom_frame = QFrame()
        bottom_frame.setProperty("class", "cardFrame")
        bot_layout = QHBoxLayout(bottom_frame)
        bot_layout.setContentsMargins(8, 8, 8, 8)

        bot_layout.addWidget(QLabel("Output Folder:"))
        self.txt_output_dir = QLineEdit(str(Path.home() / "Documents" / "DocuTools" / "Conversions"))
        bot_layout.addWidget(self.txt_output_dir, stretch=1)

        btn_browse_out = QPushButton("Browse...")
        btn_browse_out.clicked.connect(self._choose_output_dir)
        bot_layout.addWidget(btn_browse_out)

        btn_clear = QPushButton("Clear Queue")
        btn_clear.clicked.connect(self._clear_queue)
        bot_layout.addWidget(btn_clear)

        self.btn_convert_all = QPushButton("🔄 Convert All Files Now")
        self.btn_convert_all.setProperty("class", "primaryButton")
        self.btn_convert_all.setMinimumHeight(38)
        self.btn_convert_all.clicked.connect(self._execute_conversion)
        bot_layout.addWidget(self.btn_convert_all)

        main_layout.addWidget(bottom_frame)

        self._on_mode_changed(0)

    def _on_mode_changed(self, index: int) -> None:
        _, _, targets = self.CONVERSION_MODES[index]
        self.combo_target_fmt.clear()
        self.combo_target_fmt.addItems(targets)

        # Show/hide DPI
        is_pdf_to_img = (index == 0)
        self.lbl_dpi.setVisible(is_pdf_to_img)
        self.spin_dpi.setVisible(is_pdf_to_img)

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.txt_output_dir.text())
        if folder:
            self.txt_output_dir.setText(folder)

    def _add_files_to_queue(self, files: List[str]) -> None:
        for f in files:
            p = Path(f)
            if p.is_file() and str(p) not in self.queue_files:
                self.queue_files.append(str(p))
        self._refresh_queue_table()

    def _refresh_queue_table(self) -> None:
        self.table_queue.setRowCount(len(self.queue_files))
        target_fmt = self.combo_target_fmt.currentText()

        for row, f_str in enumerate(self.queue_files):
            p = Path(f_str)
            item_name = QTableWidgetItem(p.name)
            item_type = QTableWidgetItem(get_file_type(p).upper())
            item_size = QTableWidgetItem(format_file_size(p.stat().st_size) if p.exists() else "0 B")
            item_target = QTableWidgetItem(target_fmt)
            item_status = QTableWidgetItem("Ready")

            self.table_queue.setItem(row, 0, item_name)
            self.table_queue.setItem(row, 1, item_type)
            self.table_queue.setItem(row, 2, item_size)
            self.table_queue.setItem(row, 3, item_target)
            self.table_queue.setItem(row, 4, item_status)

    def _clear_queue(self) -> None:
        self.queue_files.clear()
        self._refresh_queue_table()

    def _execute_conversion(self) -> None:
        if not self.queue_files:
            QMessageBox.warning(self, "Queue Empty", "Please add files to the conversion queue first.")
            return

        out_dir = Path(self.txt_output_dir.text().strip())
        out_dir.mkdir(parents=True, exist_ok=True)

        mode_idx = self.combo_mode.currentIndex()
        target_fmt = self.combo_target_fmt.currentText()
        dpi = self.spin_dpi.value()

        self.progress_card.start_task(f"Converting {len(self.queue_files)} items...")

        # Case 2: Images to PDF (combined into 1 single file)
        if mode_idx == 1 and "Combined" in target_fmt:
            out_pdf = out_dir / "converted_combined.pdf"
            worker = TaskWorker(ConversionEngine.images_to_pdf, self.queue_files, out_pdf)
            worker.signals.progress.connect(self.progress_card.update_progress)
            worker.signals.finished.connect(lambda res: self._on_single_conversion_done("Images to PDF", res))
            worker.signals.error.connect(lambda err, tb: self._on_worker_error("Conversion Failed", err))
            self.thread_pool.start(worker)
            return

        # Sequential batch conversion
        def process_item_fn(file_path: str, progress_cb):
            p = Path(file_path)
            if mode_idx == 0:  # PDF to Images
                return ConversionEngine.pdf_to_images(p, out_dir, image_format=target_fmt, dpi=dpi)
            elif mode_idx == 1:  # Images to PDF (separate)
                out_p = out_dir / f"{p.stem}.pdf"
                return ConversionEngine.images_to_pdf([p], out_p)
            elif mode_idx == 2:  # DOCX to PDF
                out_p = out_dir / f"{p.stem}.pdf"
                return ConversionEngine.docx_to_pdf(p, out_p)
            elif mode_idx == 3:  # PDF to Text
                out_p = out_dir / f"{p.stem}.txt"
                return ConversionEngine.pdf_to_text(p, out_p)
            elif mode_idx == 4:  # Image Format Converter
                return ConversionEngine.convert_image_format(p, target_fmt, out_dir)
            return None

        batch_worker = BatchWorker(self.queue_files, process_item_fn)
        batch_worker.signals.item_finished.connect(self._on_batch_item_finished)
        batch_worker.signals.all_finished.connect(self._on_batch_all_finished)
        self.thread_pool.start(batch_worker)

    def _on_batch_item_finished(self, row: int, result: Any) -> None:
        if row < self.table_queue.rowCount():
            item_status = QTableWidgetItem("Converted")
            item_status.setForeground(Qt.GlobalColor.green)
            self.table_queue.setItem(row, 4, item_status)

    def _on_single_conversion_done(self, op_name: str, out_file: str) -> None:
        self.progress_card.complete_task(f"Generated {Path(out_file).name}")
        self.db.log_operation("Conversion Center", op_name, output_file=out_file, status="success")
        self.db.add_recent_file(out_file, get_file_type(out_file))
        QMessageBox.information(self, "Conversion Complete", f"Successfully converted and saved to:\n{out_file}")

    def _on_batch_all_finished(self, all_results: List[Any]) -> None:
        self.progress_card.complete_task(f"All {len(all_results)} files converted!")
        self.db.log_operation("Conversion Center", "Batch Conversion", status="success")
        QMessageBox.information(
            self, "Conversion Complete",
            f"Successfully converted all {len(all_results)} files to:\n{self.txt_output_dir.text()}"
        )

    def _on_worker_error(self, title: str, error_msg: str) -> None:
        self.progress_card.fail_task(error_msg)
        self.db.log_operation("Conversion Center", title, status="error", error_message=error_msg)
        QMessageBox.critical(self, title, f"An error occurred:\n{error_msg}")
