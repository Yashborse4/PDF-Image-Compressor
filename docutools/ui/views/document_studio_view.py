"""
Document Studio View for DocuTools.
Word-style document editor built on QTextEdit and python-docx.
Supports rich formatting, tables, images, DOCX reading/saving, and high-fidelity PDF export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextImageFormat,
    QTextListFormat,
    QTextTableFormat,
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.docx_engine import DocxEngine
from docutools.core.validator import validate_file
from docutools.ui.components.progress_card import ProgressCard
from docutools.workers.task_worker import TaskWorker


class DocumentStudioView(QWidget):
    """Word-style rich-text and DOCX document editor."""

    def __init__(self, db: Database, thread_pool: QThreadPool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.thread_pool = thread_pool
        self.current_docx_path: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(10)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Document Studio")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Create and edit Word DOCX documents with rich styling, tables, and vector PDF export.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.btn_new = QPushButton("📄 New")
        self.btn_new.clicked.connect(self._new_document)
        header_row.addWidget(self.btn_new)

        self.btn_open = QPushButton("📂 Open DOCX...")
        self.btn_open.clicked.connect(self._open_docx_dialog)
        header_row.addWidget(self.btn_open)

        self.btn_save_docx = QPushButton("💾 Save DOCX...")
        self.btn_save_docx.setProperty("class", "primaryButton")
        self.btn_save_docx.clicked.connect(self._save_docx_dialog)
        header_row.addWidget(self.btn_save_docx)

        self.btn_export_pdf = QPushButton("📑 Export PDF...")
        self.btn_export_pdf.setProperty("class", "successButton")
        self.btn_export_pdf.clicked.connect(self._export_pdf_dialog)
        header_row.addWidget(self.btn_export_pdf)

        main_layout.addLayout(header_row)

        # Progress Card
        self.progress_card = ProgressCard()
        main_layout.addWidget(self.progress_card)

        # Formatting Toolbar Frame
        tb_frame = QFrame()
        tb_frame.setProperty("class", "cardFrame")
        tb_layout = QHBoxLayout(tb_frame)
        tb_layout.setContentsMargins(6, 6, 6, 6)
        tb_layout.setSpacing(6)

        # Font Combo
        self.font_combo = QComboBox()
        self.font_combo.setEditable(False)
        fonts = ["Segoe UI", "Calibri", "Arial", "Times New Roman", "Consolas", "Georgia", "Verdana"]
        self.font_combo.addItems(fonts)
        self.font_combo.setCurrentText("Segoe UI")
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        tb_layout.addWidget(self.font_combo)

        # Font Size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(11)
        self.size_spin.valueChanged.connect(self._on_font_size_changed)
        tb_layout.addWidget(self.size_spin)

        # Formatting buttons (Bold, Italic, Underline, Strike)
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(30, 30)
        self.btn_bold.setStyleSheet("font-weight: bold;")
        self.btn_bold.clicked.connect(self._toggle_bold)
        tb_layout.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(30, 30)
        self.btn_italic.setStyleSheet("font-style: italic;")
        self.btn_italic.clicked.connect(self._toggle_italic)
        tb_layout.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("U")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(30, 30)
        self.btn_underline.setStyleSheet("text-decoration: underline;")
        self.btn_underline.clicked.connect(self._toggle_underline)
        tb_layout.addWidget(self.btn_underline)

        # Colors
        self.btn_color = QPushButton("🎨 Color")
        self.btn_color.clicked.connect(self._choose_text_color)
        tb_layout.addWidget(self.btn_color)

        self.btn_bg_color = QPushButton("🖍 Highlight")
        self.btn_bg_color.clicked.connect(self._choose_highlight_color)
        tb_layout.addWidget(self.btn_bg_color)

        # Alignments
        self.btn_align_left = QPushButton("⇤")
        self.btn_align_left.setToolTip("Align Left")
        self.btn_align_left.setFixedSize(30, 30)
        self.btn_align_left.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        tb_layout.addWidget(self.btn_align_left)

        self.btn_align_center = QPushButton("≡")
        self.btn_align_center.setToolTip("Align Center")
        self.btn_align_center.setFixedSize(30, 30)
        self.btn_align_center.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        tb_layout.addWidget(self.btn_align_center)

        self.btn_align_right = QPushButton("⇥")
        self.btn_align_right.setToolTip("Align Right")
        self.btn_align_right.setFixedSize(30, 30)
        self.btn_align_right.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignRight))
        tb_layout.addWidget(self.btn_align_right)

        self.btn_align_justify = QPushButton("⇋")
        self.btn_align_justify.setToolTip("Justify")
        self.btn_align_justify.setFixedSize(30, 30)
        self.btn_align_justify.clicked.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignJustify))
        tb_layout.addWidget(self.btn_align_justify)

        # Lists
        self.btn_bullet = QPushButton("• List")
        self.btn_bullet.setToolTip("Bulleted List")
        self.btn_bullet.clicked.connect(self._insert_bullet_list)
        tb_layout.addWidget(self.btn_bullet)

        self.btn_number = QPushButton("1. List")
        self.btn_number.setToolTip("Numbered List")
        self.btn_number.clicked.connect(self._insert_numbered_list)
        tb_layout.addWidget(self.btn_number)

        # Insert Table & Image
        self.btn_table = QPushButton("⊞ Table")
        self.btn_table.clicked.connect(self._insert_table_dialog)
        tb_layout.addWidget(self.btn_table)

        self.btn_image = QPushButton("🖼 Image")
        self.btn_image.clicked.connect(self._insert_image_dialog)
        tb_layout.addWidget(self.btn_image)

        tb_layout.addStretch()
        main_layout.addWidget(tb_frame)

        # Central Text Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Segoe UI", 11))
        self.editor.setPlaceholderText("Start typing your document, or open a Word DOCX file...")
        self.editor.textChanged.connect(self._update_stats)
        self.editor.cursorPositionChanged.connect(self._update_cursor_format)
        main_layout.addWidget(self.editor, stretch=1)

        # Status Footer
        footer = QHBoxLayout()
        self.lbl_file_status = QLabel("Untitled Document")
        self.lbl_file_status.setStyleSheet("color: #9ca3af; font-size: 12px;")
        footer.addWidget(self.lbl_file_status)

        footer.addStretch()

        self.lbl_stats = QLabel("Words: 0 | Characters: 0")
        self.lbl_stats.setStyleSheet("color: #9ca3af; font-size: 12px;")
        footer.addWidget(self.lbl_stats)

        main_layout.addLayout(footer)

    # --- Document Handlers ---
    def _new_document(self) -> None:
        if self.editor.toPlainText().strip():
            reply = QMessageBox.question(
                self, "New Document", "Clear current document and start new?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.editor.clear()
        self.current_docx_path = None
        self.lbl_file_status.setText("Untitled Document")

    def _open_docx_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Word Document", "", "Word Documents (*.docx *.doc)")
        if file_path:
            self.load_docx(file_path)

    def load_docx(self, file_path: str) -> None:
        is_valid, msg = validate_file(file_path, expected_type="docx")
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", msg)
            return

        self.progress_card.start_task("Opening and Parsing DOCX Document...")

        def read_worker():
            return DocxEngine.docx_to_html(file_path)

        worker = TaskWorker(read_worker)
        worker.signals.finished.connect(lambda html_str: self._on_docx_loaded(file_path, html_str))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Failed to Open DOCX", err))
        self.thread_pool.start(worker)

    def _on_docx_loaded(self, file_path: str, html_str: str) -> None:
        self.editor.setHtml(html_str)
        self.current_docx_path = file_path
        self.lbl_file_status.setText(f"Editing: {Path(file_path).name}")
        self.progress_card.complete_task("Document loaded.")
        self.progress_card.hide()
        self.db.add_recent_file(file_path, "docx")

    def _save_docx_dialog(self) -> None:
        default_name = Path(self.current_docx_path).name if self.current_docx_path else "document.docx"
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Document as DOCX", default_name, "Word Document (*.docx)")
        if not out_path:
            return

        html_content = self.editor.toHtml()
        self.progress_card.start_task("Saving Document as DOCX...")

        worker = TaskWorker(DocxEngine.html_to_docx, html_content, out_path)
        worker.signals.finished.connect(lambda res: self._on_saved_docx(res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("Save Failed", err))
        self.thread_pool.start(worker)

    def _on_saved_docx(self, file_path: str) -> None:
        self.current_docx_path = file_path
        self.lbl_file_status.setText(f"Saved: {Path(file_path).name}")
        self.progress_card.complete_task("Saved DOCX file.")
        self.db.add_recent_file(file_path, "docx")
        self.db.log_operation("Document Studio", "Saved DOCX", output_file=file_path, status="success")
        QMessageBox.information(self, "Document Saved", f"File saved successfully to:\n{file_path}")

    def _export_pdf_dialog(self) -> None:
        default_name = f"{Path(self.current_docx_path).stem if self.current_docx_path else 'document'}.pdf"
        out_path, _ = QFileDialog.getSaveFileName(self, "Export Document to PDF", default_name, "PDF Files (*.pdf)")
        if not out_path:
            return

        self.progress_card.start_task("Rendering High-Resolution Vector PDF...")

        def export_worker():
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(out_path)
            doc = self.editor.document()
            doc.print_(printer)
            return out_path

        worker = TaskWorker(export_worker)
        worker.signals.finished.connect(lambda res: self._on_pdf_exported(res))
        worker.signals.error.connect(lambda err, tb: self._on_worker_error("PDF Export Failed", err))
        self.thread_pool.start(worker)

    def _on_pdf_exported(self, file_path: str) -> None:
        self.progress_card.complete_task("PDF exported.")
        self.db.add_recent_file(file_path, "pdf")
        self.db.log_operation("Document Studio", "Exported PDF", output_file=file_path, status="success")
        QMessageBox.information(self, "PDF Export Complete", f"PDF successfully generated:\n{file_path}")

    # --- Formatting Operations ---
    def _on_font_changed(self, font_name: str) -> None:
        fmt = QTextCharFormat()
        fmt.setFontFamily(font_name)
        self._merge_format_on_selection(fmt)

    def _on_font_size_changed(self, size: int) -> None:
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self._merge_format_on_selection(fmt)

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.btn_bold.isChecked() else QFont.Weight.Normal)
        self._merge_format_on_selection(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.btn_italic.isChecked())
        self._merge_format_on_selection(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.btn_underline.isChecked())
        self._merge_format_on_selection(fmt)

    def _choose_text_color(self) -> None:
        col = QColorDialog.getColor(Qt.GlobalColor.black, self, "Select Text Color")
        if col.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(col)
            self._merge_format_on_selection(fmt)

    def _choose_highlight_color(self) -> None:
        col = QColorDialog.getColor(Qt.GlobalColor.yellow, self, "Select Highlight Color")
        if col.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(col)
            self._merge_format_on_selection(fmt)

    def _insert_bullet_list(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(fmt)

    def _insert_numbered_list(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.createList(fmt)

    def _insert_table_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Table")
        d_lay = QVBoxLayout(dialog)
        d_lay.setSpacing(10)

        row_lay = QHBoxLayout()
        row_lay.addWidget(QLabel("Rows:"))
        rows_spin = QSpinBox()
        rows_spin.setRange(1, 50)
        rows_spin.setValue(3)
        row_lay.addWidget(rows_spin)

        row_lay.addWidget(QLabel("Columns:"))
        cols_spin = QSpinBox()
        cols_spin.setRange(1, 20)
        cols_spin.setValue(3)
        row_lay.addWidget(cols_spin)
        d_lay.addLayout(row_lay)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Insert")
        btn_ok.setProperty("class", "primaryButton")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        d_lay.addLayout(btn_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            cursor = self.editor.textCursor()
            table_fmt = QTextTableFormat()
            table_fmt.setBorder(1)
            table_fmt.setCellPadding(6)
            table_fmt.setCellSpacing(0)
            cursor.insertTable(rows_spin.value(), cols_spin.value(), table_fmt)

    def _insert_image_dialog(self) -> None:
        img_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image to Insert", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not img_path:
            return

        cursor = self.editor.textCursor()
        img_fmt = QTextImageFormat()
        img_fmt.setName(img_path)
        img_fmt.setWidth(400)  # Standard fitted width
        cursor.insertImage(img_fmt)

    def _merge_format_on_selection(self, format: QTextCharFormat) -> None:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(format)
        self.editor.mergeCurrentCharFormat(format)

    def _update_cursor_format(self) -> None:
        fmt = self.editor.currentCharFormat()
        self.btn_bold.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_underline.setChecked(fmt.fontUnderline())

    def _update_stats(self) -> None:
        text = self.editor.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.lbl_stats.setText(f"Words: {words:,} | Characters: {chars:,}")

    def _on_worker_error(self, title: str, error_msg: str) -> None:
        self.progress_card.fail_task(error_msg)
        self.db.log_operation("Document Studio", title, status="error", error_message=error_msg)
        QMessageBox.critical(self, title, f"An error occurred:\n{error_msg}")
