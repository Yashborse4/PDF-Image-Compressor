"""
Dedicated Batch Processing View for DocuTools.
Processes collections of documents and images in background queues with cancellation support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.conversion_engine import ConversionEngine
from docutools.core.database import Database
from docutools.core.docx_engine import DocxEngine
from docutools.core.image_engine import ImageEngine
from docutools.core.pdf_engine import PDFEngine
from docutools.core.validator import format_file_size, get_file_type
from docutools.ui.components.drop_zone import DropZone
from docutools.ui.components.pdf_preview_widget import PDFPreviewWidget
from docutools.ui.components.progress_card import ProgressCard
from docutools.workers.batch_worker import BatchWorker


class BatchProcessingView(QWidget):
    """Multi-file batch operation suite."""

    BATCH_OPERATIONS = [
        "📉 Batch PDF Compression",
        "🖼 Batch Image Target-Size Optimization (50/100/200 KB)",
        "🔄 Batch PDF to Images (PNG)",
        "📑 Batch Images to PDF",
        "📝 Batch DOCX to PDF",
    ]

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool
        self.queue_items: List[str] = []
        self.current_worker: Optional[BatchWorker] = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Batch Processing Center")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Automate large-scale document and image workflows with non-blocking concurrency.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        # Progress Card
        self.progress_card = ProgressCard()
        self.progress_card.cancelled.connect(self._cancel_batch)
        main_layout.addWidget(self.progress_card)

        # Configuration Bar
        config_frame = QFrame()
        config_frame.setProperty("class", "cardFrame")
        c_lay = QHBoxLayout(config_frame)
        c_lay.setContentsMargins(10, 8, 10, 8)
        c_lay.setSpacing(10)

        c_lay.addWidget(QLabel("Action:"))
        self.combo_op = QComboBox()
        self.combo_op.addItems(self.BATCH_OPERATIONS)
        self.combo_op.currentIndexChanged.connect(self._on_op_changed)
        c_lay.addWidget(self.combo_op)

        # Parameter 1: Quality / Target Size
        self.lbl_param1 = QLabel("Target Size:")
        self.combo_param1 = QComboBox()
        self.combo_param1.addItems(["50 KB", "100 KB", "200 KB", "500 KB"])
        self.combo_param1.setCurrentIndex(1)
        c_lay.addWidget(self.lbl_param1)
        c_lay.addWidget(self.combo_param1)

        c_lay.addStretch()
        main_layout.addWidget(config_frame)

        # Drop Zone
        self.drop_zone = DropZone(
            title="Drop multiple files to queue for batch processing",
            subtitle="Queue any number of PDFs, DOCX, or images",
            file_filter="All Supported Files (*.pdf *.docx *.png *.jpg *.jpeg *.webp *.bmp *.tiff)",
            multi_select=True
        )
        self.drop_zone.files_dropped.connect(self._add_files)
        main_layout.addWidget(self.drop_zone)

        # Batch Queue Table + Instant Output Viewer
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table_queue = QTableWidget(0, 6)
        self.table_queue.setHorizontalHeaderLabels(["File Name", "Original Size", "Output File", "Savings", "Status", ""])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table_queue.setColumnWidth(5, 44)
        self.splitter.addWidget(self.table_queue)

        self.preview_widget = PDFPreviewWidget()
        self.preview_widget.close_requested.connect(self.preview_widget.hide)
        self.preview_widget.hide()
        self.splitter.addWidget(self.preview_widget)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        main_layout.addWidget(self.splitter, stretch=1)

        # Bottom Bar: Output Folder & Controls
        bottom_frame = QFrame()
        bottom_frame.setProperty("class", "cardFrame")
        bot_lay = QHBoxLayout(bottom_frame)
        bot_lay.setContentsMargins(8, 8, 8, 8)

        bot_lay.addWidget(QLabel("Output Folder:"))
        self.txt_out_dir = QLineEdit(str(Path.home() / "Documents" / "DocuTools" / "BatchOutput"))
        bot_lay.addWidget(self.txt_out_dir, stretch=1)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._choose_output_dir)
        bot_lay.addWidget(btn_browse)

        btn_clear = QPushButton("Clear Queue")
        btn_clear.clicked.connect(self._clear_queue)
        bot_lay.addWidget(btn_clear)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "dangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_batch)
        bot_lay.addWidget(self.btn_cancel)

        self.btn_run = QPushButton("▶ Start Batch Execution")
        self.btn_run.setProperty("class", "primaryButton")
        self.btn_run.setMinimumHeight(38)
        self.btn_run.clicked.connect(self._execute_batch)
        bot_lay.addWidget(self.btn_run)

        main_layout.addWidget(bottom_frame)
        self._on_op_changed(0)

    def _on_op_changed(self, index: int) -> None:
        if index == 0:  # PDF Compression
            self.lbl_param1.setText("Level:")
            self.combo_param1.clear()
            self.combo_param1.addItems(["Low (High Quality)", "Medium (Balanced)", "High (Max Deflation)"])
            self.combo_param1.setCurrentIndex(1)
            self.lbl_param1.show()
            self.combo_param1.show()
        elif index == 1:  # Image Target Size
            self.lbl_param1.setText("Target Size:")
            self.combo_param1.clear()
            self.combo_param1.addItems(["50 KB", "100 KB", "200 KB", "500 KB"])
            self.combo_param1.setCurrentIndex(1)
            self.lbl_param1.show()
            self.combo_param1.show()
        else:
            self.lbl_param1.hide()
            self.combo_param1.hide()

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.txt_out_dir.text())
        if folder:
            self.txt_out_dir.setText(folder)

    def _add_files(self, files: List[str]) -> None:
        for f in files:
            p = Path(f)
            if p.is_file() and str(p) not in self.queue_items:
                self.queue_items.append(str(p))
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table_queue.setSortingEnabled(False)
        self.table_queue.setRowCount(len(self.queue_items))
        cell_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        for row, f_str in enumerate(self.queue_items):
            p = Path(f_str)
            item_name = QTableWidgetItem(p.name)
            item_size = QTableWidgetItem(format_file_size(p.stat().st_size) if p.exists() else "0 B")
            item_out = QTableWidgetItem("-")
            item_sav = QTableWidgetItem("-")
            item_status = QTableWidgetItem("Queued")

            for it in (item_name, item_size, item_out, item_sav, item_status):
                it.setFlags(cell_flags)

            self.table_queue.setItem(row, 0, item_name)
            self.table_queue.setItem(row, 1, item_size)
            self.table_queue.setItem(row, 2, item_out)
            self.table_queue.setItem(row, 3, item_sav)
            self.table_queue.setItem(row, 4, item_status)

            btn_remove = QPushButton("✕")
            btn_remove.setToolTip("Remove from queue")
            btn_remove.setFixedSize(28, 28)
            btn_remove.setStyleSheet(
                "QPushButton { background: transparent; color: #9ca3af; border: none; font-weight: bold; font-size: 14px; border-radius: 4px; }"
                "QPushButton:hover { background-color: rgba(239, 68, 68, 0.2); color: #ef4444; }"
            )
            btn_remove.clicked.connect(lambda _=False, r=row: self._remove_queue_item(r))
            self.table_queue.setCellWidget(row, 5, btn_remove)

    def _remove_queue_item(self, row: int) -> None:
        if 0 <= row < len(self.queue_items):
            self.queue_items.pop(row)
            self._refresh_table()

    def _clear_queue(self) -> None:
        self.queue_items.clear()
        self._refresh_table()

    def _execute_batch(self) -> None:
        if not self.queue_items:
            QMessageBox.warning(self, "Queue Empty", "Please add files to batch process.")
            return

        default_dir = self.txt_out_dir.text().strip() or str(Path.home() / "Documents")
        chosen_dir = QFileDialog.getExistingDirectory(self, "Select Export Location", default_dir)
        if not chosen_dir:
            return
        self.txt_out_dir.setText(chosen_dir)
        out_dir = Path(chosen_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        op_idx = self.combo_op.currentIndex()
        param_idx = self.combo_param1.currentIndex()

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_card.start_task(f"Running Batch Operation on {len(self.queue_items)} Files...")

        def process_item_fn(file_path: str, progress_cb):
            p = Path(file_path)
            if op_idx == 0:  # PDF Compression
                level_map = {0: "low", 1: "medium", 2: "high"}
                out_p = out_dir / f"{p.stem}_compressed.pdf"
                return PDFEngine.compress_pdf(p, out_p, quality_level=level_map[param_idx])
            elif op_idx == 1:  # Image Target Size
                target_map = {0: 50, 1: 100, 2: 200, 3: 500}
                out_p = out_dir / f"{p.stem}_opt{p.suffix}"
                return ImageEngine.process_single_image(p, out_p, target_kb=target_map[param_idx])
            elif op_idx == 2:  # PDF to Images (full resolution)
                return ConversionEngine.pdf_to_images(p, out_dir, image_format="PNG", dpi=300)
            elif op_idx == 3:  # Images to PDF
                out_p = out_dir / f"{p.stem}.pdf"
                return ConversionEngine.images_to_pdf([p], out_p)
            elif op_idx == 4:  # DOCX to PDF
                out_p = out_dir / f"{p.stem}.pdf"
                return ConversionEngine.docx_to_pdf(p, out_p)
            return None

        self.current_worker = BatchWorker(list(self.queue_items), process_item_fn)
        self.current_worker.signals.item_finished.connect(self._on_item_finished)
        self.current_worker.signals.item_error.connect(self._on_item_error)
        self.current_worker.signals.all_finished.connect(self._on_all_finished)
        self.thread_pool.start(self.current_worker)

    def _on_item_finished(self, row: int, result: Any) -> None:
        if row < self.table_queue.rowCount():
            if isinstance(result, dict) and "compressed_size" in result:
                self.table_queue.setItem(row, 2, QTableWidgetItem(Path(result["file_path"]).name))
                self.table_queue.setItem(row, 3, QTableWidgetItem(f"-{result['savings_percent']:.1f}%"))
            elif isinstance(result, dict) and "final_size" in result:
                self.table_queue.setItem(row, 2, QTableWidgetItem(Path(result["output_file"]).name))
                self.table_queue.setItem(row, 3, QTableWidgetItem(f"-{result['savings_percent']:.1f}%"))
            elif isinstance(result, str):
                self.table_queue.setItem(row, 2, QTableWidgetItem(Path(result).name))
                self.table_queue.setItem(row, 3, QTableWidgetItem("-"))
            elif isinstance(result, list):
                self.table_queue.setItem(row, 2, QTableWidgetItem(f"{len(result)} images"))
                self.table_queue.setItem(row, 3, QTableWidgetItem("-"))

            status_item = QTableWidgetItem("Success")
            status_item.setForeground(Qt.GlobalColor.green)
            self.table_queue.setItem(row, 4, status_item)

    def _on_item_error(self, row: int, err: str, tb: str) -> None:
        if row < self.table_queue.rowCount():
            status_item = QTableWidgetItem(f"Failed: {err[:30]}")
            status_item.setForeground(Qt.GlobalColor.red)
            self.table_queue.setItem(row, 4, status_item)

    def _on_all_finished(self, results: List[Any]) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_card.complete_task(f"Batch completed: {len(results)} files processed.")
        self.db.log_operation("Batch Center", self.combo_op.currentText(), status="success")
        self._clear_queue()
        for res in results:
            cand = res.get("file_path") if isinstance(res, dict) else (res if isinstance(res, str) else None)
            if cand and str(cand).lower().endswith(".pdf") and Path(cand).is_file():
                self.preview_widget.load_pdf(cand, is_output=True)
                self.preview_widget.show()
                break
        QMessageBox.information(self, "Batch Complete", f"Batch execution completed for {len(results)} items.")

    def _cancel_batch(self) -> None:
        if self.current_worker:
            self.current_worker.cancel()
            self.progress_card.fail_task("Batch processing cancelled by user.")
            self.btn_run.setEnabled(True)
            self.btn_cancel.setEnabled(False)
