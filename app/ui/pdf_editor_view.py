"""Advanced PDF Editor Workspace for DocuTools.
Embeds interactive canvas, in-place text editing, annotations, and signing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.logging import get_logger
from app.ui.widgets import FileDropArea
from pdfapp.document_view import DocumentView
from pdfcore.document import PdfDocument

logger = get_logger("pdf_editor_view")


class AdvancedPdfEditorView(QWidget):
    """Full-featured interactive in-place PDF Editor workspace."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.doc: Optional[PdfDocument] = None
        self.doc_view: Optional[DocumentView] = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. Editor Toolbar
        self._build_toolbar()

        # 2. Main Stack (Drop zone if no file open, DocumentView when open)
        self.stack = QStackedWidget(self)

        # Empty State Widget
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(28, 24, 28, 24)
        empty_layout.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(4)
        t_label = QLabel("Advanced PDF Editor")
        t_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.addWidget(t_label)

        sub_label = QLabel(
            "Select existing text on any PDF page to edit it in place, modify images, add highlights, and sign."
        )
        sub_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        header.addWidget(sub_label)
        empty_layout.addLayout(header)

        self.drop_area = FileDropArea(
            prompt_text="Drag & drop a PDF document here to open in editor",
            accepted_extensions={".pdf"},
        )
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        empty_layout.addWidget(self.drop_area)

        choose_row = QHBoxLayout()
        choose_btn = QPushButton("Open PDF File...")
        choose_btn.setProperty("variant", "accent")
        choose_btn.clicked.connect(self._browse_pdf)
        choose_row.addWidget(choose_btn)
        choose_row.addStretch()
        empty_layout.addLayout(choose_row)
        empty_layout.addStretch()

        self.stack.addWidget(self.empty_widget)  # Index 0
        self.layout.addWidget(self.stack)

    def _build_toolbar(self) -> None:
        import qtawesome as qta

        self.toolbar = QToolBar("PDF Editor Controls")
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setStyleSheet("QToolBar { border-bottom: 1px solid #383842; padding: 4px; }")

        # Open
        open_action = QAction(qta.icon("fa5s.folder-open", color="#9ca3af"), "Open PDF", self)
        open_action.triggered.connect(self._browse_pdf)
        self.toolbar.addAction(open_action)

        # Save
        self.save_action = QAction(qta.icon("fa5s.save", color="#9ca3af"), "Save Changes", self)
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self._save_doc)
        self.toolbar.addAction(self.save_action)

        # Save As
        self.save_as_action = QAction(qta.icon("fa5s.file-export", color="#9ca3af"), "Save As...", self)
        self.save_as_action.setEnabled(False)
        self.save_as_action.triggered.connect(self._save_doc_as)
        self.toolbar.addAction(self.save_as_action)

        self.toolbar.addSeparator()

        # Edit Mode Toggle
        self.edit_mode_btn = QPushButton(" Edit Mode")
        self.edit_mode_btn.setIcon(qta.icon("fa5s.pencil-alt", color="#9ca3af"))
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.setEnabled(False)
        self.edit_mode_btn.clicked.connect(self._toggle_edit_mode)
        self.toolbar.addWidget(self.edit_mode_btn)

        self.toolbar.addSeparator()

        # Zoom Controls
        self.zoom_out_action = QAction(qta.icon("fa5s.search-minus", color="#9ca3af"), "Zoom Out", self)
        self.zoom_out_action.setEnabled(False)
        self.zoom_out_action.triggered.connect(lambda: self.doc_view.zoom_out() if self.doc_view else None)
        self.toolbar.addAction(self.zoom_out_action)

        self.zoom_in_action = QAction(qta.icon("fa5s.search-plus", color="#9ca3af"), "Zoom In", self)
        self.zoom_in_action.setEnabled(False)
        self.zoom_in_action.triggered.connect(lambda: self.doc_view.zoom_in() if self.doc_view else None)
        self.toolbar.addAction(self.zoom_in_action)

        self.fit_width_action = QAction(qta.icon("fa5s.arrows-alt-h", color="#9ca3af"), "Fit Width", self)
        self.fit_width_action.setEnabled(False)
        self.fit_width_action.triggered.connect(lambda: self.doc_view.zoom_fit_width() if self.doc_view else None)
        self.toolbar.addAction(self.fit_width_action)

        # Close File
        self.toolbar.addSeparator()
        self.close_action = QAction(qta.icon("fa5s.times", color="#9ca3af"), "Close Document", self)
        self.close_action.setEnabled(False)
        self.close_action.triggered.connect(self.close_document)
        self.toolbar.addAction(self.close_action)

        self.layout.addWidget(self.toolbar)

    def _browse_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF Document to Edit",
            "",
            "PDF Documents (*.pdf);;All Files (*.*)",
        )
        if file_path:
            self.load_pdf(file_path)

    def _on_files_dropped(self, files: list[str]) -> None:
        if files:
            self.load_pdf(files[0])

    def load_pdf(self, file_path: str) -> None:
        """Open PDF in the interactive DocumentView."""
        path = Path(file_path)
        if not path.exists():
            return

        try:
            # Close existing if open
            self.close_document()

            self.doc = PdfDocument.open(path)
            self.doc_view = DocumentView(self.doc, parent=self)

            self.stack.addWidget(self.doc_view)
            self.stack.setCurrentWidget(self.doc_view)

            # Enable toolbar controls
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.edit_mode_btn.setEnabled(True)
            self.zoom_in_action.setEnabled(True)
            self.zoom_out_action.setEnabled(True)
            self.fit_width_action.setEnabled(True)
            self.close_action.setEnabled(True)

            logger.info("Loaded PDF into editor: %s (%d pages)", path.name, self.doc.page_count)
        except Exception as exc:
            logger.error("Failed to load PDF in editor: %s", exc)
            QMessageBox.critical(self, "Failed to Open PDF", f"Could not load PDF document:\n{exc}")

    def _toggle_edit_mode(self) -> None:
        if self.doc_view:
            checked = self.edit_mode_btn.isChecked()
            self.doc_view.set_edit_mode(checked)
            self.edit_mode_btn.setText(" Edit Mode (Active)" if checked else " Edit Mode")

    def _save_doc(self) -> None:
        if self.doc_view:
            try:
                self.doc_view.save()
                QMessageBox.information(self, "Saved", "Document saved successfully.")
            except Exception as exc:
                QMessageBox.critical(self, "Save Error", f"Failed to save document:\n{exc}")

    def _save_doc_as(self) -> None:
        if self.doc_view:
            dest, _ = QFileDialog.getSaveFileName(self, "Save PDF As", "", "PDF Document (*.pdf)")
            if dest:
                try:
                    self.doc_view.save_as(Path(dest))
                    QMessageBox.information(self, "Saved", f"Document saved as:\n{dest}")
                except Exception as exc:
                    QMessageBox.critical(self, "Save Error", f"Failed to save document:\n{exc}")

    def close_document(self) -> None:
        """Close current document view and reset toolbar."""
        if self.doc_view:
            self.stack.removeWidget(self.doc_view)
            self.doc_view.deleteLater()
            self.doc_view = None

        if self.doc:
            self.doc.close()
            self.doc = None

        self.stack.setCurrentWidget(self.empty_widget)
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)
        self.edit_mode_btn.setEnabled(False)
        self.edit_mode_btn.setChecked(False)
        self.edit_mode_btn.setText(" Edit Mode")
        self.zoom_in_action.setEnabled(False)
        self.zoom_out_action.setEnabled(False)
        self.fit_width_action.setEnabled(False)
        self.close_action.setEnabled(False)
