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
from pdfapp import portable
from pdfapp.document_view import DocumentView
from pdfapp.sign_dialog import SignDialog
from pdfapp.signature_manager_dialog import SignatureManagerDialog
from pdfapp.signature_store import STORE_FILENAME, SignatureStore
from pdfcore import signing
from pdfcore.document import PdfDocument

logger = get_logger("pdf_editor_view")


class AdvancedPdfEditorView(QWidget):
    """Full-featured interactive in-place PDF Editor workspace."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.doc: Optional[PdfDocument] = None
        self.doc_view: Optional[DocumentView] = None
        self._signatures = SignatureStore(portable.data_dir() / STORE_FILENAME)

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

        # Digital Signing Controls
        self.place_sig_btn = QPushButton(" Place Signature")
        self.place_sig_btn.setIcon(qta.icon("fa5s.file-signature", color="#9ca3af"))
        self.place_sig_btn.setToolTip("Drag a rectangle on any page to place a visual digital signature")
        self.place_sig_btn.setCheckable(True)
        self.place_sig_btn.setEnabled(False)
        self.place_sig_btn.clicked.connect(self._on_place_signature_clicked)
        self.toolbar.addWidget(self.place_sig_btn)

        self.sign_invis_action = QAction(qta.icon("fa5s.pen-nib", color="#9ca3af"), "Sign (Invisible)", self)
        self.sign_invis_action.setToolTip("Apply cryptographic PAdES digital signature without visible stamp")
        self.sign_invis_action.setEnabled(False)
        self.sign_invis_action.triggered.connect(self._sign_invisible)
        self.toolbar.addAction(self.sign_invis_action)

        self.sig_status_action = QAction(qta.icon("fa5s.shield-alt", color="#9ca3af"), "Signature Status", self)
        self.sig_status_action.setToolTip("Inspect and verify digital signatures in this document")
        self.sig_status_action.setEnabled(False)
        self.sig_status_action.triggered.connect(self._show_signature_status)
        self.toolbar.addAction(self.sig_status_action)

        self.manage_sigs_action = QAction(qta.icon("fa5s.id-card", color="#9ca3af"), "Manage Signatures", self)
        self.manage_sigs_action.setToolTip("Manage saved signing identities and certificates")
        self.manage_sigs_action.triggered.connect(self._manage_signatures)
        self.toolbar.addAction(self.manage_sigs_action)

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
            self.doc_view.open_password = ""

            # Connect digital signing signals from canvas & banner
            self.doc_view.signatureRectSelected.connect(
                lambda n, rect: self._run_sign_flow(page_index=n, rect=rect)
            )
            self.doc_view.signatureDetailsRequested.connect(self._show_signature_status)

            self.stack.addWidget(self.doc_view)
            self.stack.setCurrentWidget(self.doc_view)

            # Enable toolbar controls
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.edit_mode_btn.setEnabled(True)
            self.place_sig_btn.setEnabled(True)
            self.sign_invis_action.setEnabled(True)
            self.sig_status_action.setEnabled(True)
            self.zoom_in_action.setEnabled(True)
            self.zoom_out_action.setEnabled(True)
            self.fit_width_action.setEnabled(True)
            self.close_action.setEnabled(True)

            # Announce status if document is signed
            self._announce_signatures(path)

            logger.info("Loaded PDF into editor: %s (%d pages)", path.name, self.doc.page_count)
        except Exception as exc:
            logger.error("Failed to load PDF in editor: %s", exc)
            QMessageBox.critical(self, "Failed to Open PDF", f"Could not load PDF document:\n{exc}")

    def _announce_signatures(self, path: Path) -> None:
        """Inspect and surface any digital signatures in the opened document."""
        if not self.doc_view or not path.is_file():
            return
        try:
            checks = signing.verify_pdf_signatures(path.read_bytes(), password=self.doc_view.open_password)
            if not checks:
                return
            has_tampered = any(c.tampered or not c.intact for c in checks)
            if has_tampered:
                self.doc_view.set_signature_banner(
                    "tampered",
                    "This document has been modified or tampered with since being digitally signed."
                )
            elif all(c.valid and c.intact for c in checks):
                names = [c.signer_name for c in checks if c.signer_name]
                signer_str = f"by {', '.join(names)}" if names else ""
                self.doc_view.set_signature_banner(
                    "intact",
                    f"Digitally signed {signer_str} — all signatures are intact."
                )
            else:
                self.doc_view.set_signature_banner(
                    "problem",
                    "One or more digital signatures in this document could not be validated."
                )
        except Exception as exc:
            logger.warning("Could not verify signatures on open: %s", exc)

    def _on_place_signature_clicked(self) -> None:
        if self.doc_view:
            if self.doc_view.armed_action == "sign":
                self.doc_view.cancel_armed_mode()
                self.place_sig_btn.setChecked(False)
            else:
                self.doc_view.begin_place_signature()
                self.place_sig_btn.setChecked(True)

    def _sign_invisible(self) -> None:
        self._run_sign_flow(page_index=None, rect=None)

    def _show_signature_status(self) -> None:
        if not self.doc or not self.doc.path or not self.doc.path.is_file():
            QMessageBox.information(self, "Signature Status", "No document currently loaded.")
            return

        try:
            checks = signing.verify_pdf_signatures(
                self.doc.path.read_bytes(),
                password=getattr(self.doc_view, "open_password", "") or ""
            )
        except Exception as exc:
            QMessageBox.warning(self, "Signature Check Error", f"Could not inspect signatures:\n{exc}")
            return

        if not checks:
            if self.doc.has_signatures():
                QMessageBox.warning(
                    self, "Signature Status",
                    "This document contains a signature field, but it cannot be verified — treat as unsigned."
                )
            else:
                QMessageBox.information(
                    self, "Signature Status",
                    "This document has no digital signatures."
                )
            return

        lines = []
        for c in checks:
            who = c.signer_name or "Unknown Signer"
            if c.intact and c.valid:
                st = "✅ INTACT & VALID — Document unaltered since signed."
                if not c.trusted:
                    st += " (Self-signed or local certificate authority)"
            else:
                st = f"❌ BROKEN / MODIFIED — {c.problem}"
            lines.append(f"• Field '{c.field_name}' ({who}):\n  {st}")

        QMessageBox.information(self, "Signature Verification Details", "\n\n".join(lines))

    def _manage_signatures(self) -> None:
        dlg = SignatureManagerDialog(self, self._signatures)
        dlg.exec()

    def _run_sign_flow(self, page_index: Optional[int] = None, rect: Optional[tuple] = None) -> None:
        if not self.doc or not self.doc_view:
            return

        visible = rect is not None
        dialog = SignDialog(
            self,
            self._signatures.profiles(),
            visible_signature=visible,
        )
        if not dialog.exec():
            self.place_sig_btn.setChecked(False)
            if self.doc_view:
                self.doc_view.cancel_armed_mode()
            return

        signer = dialog.signer
        if not signer:
            return

        out_path_str, _ = QFileDialog.getSaveFileName(
            self, "Save Signed PDF", str(self.doc.path.parent / f"{self.doc.path.stem}_signed.pdf"), "PDF Files (*.pdf)"
        )
        if not out_path_str:
            self.place_sig_btn.setChecked(False)
            if self.doc_view:
                self.doc_view.cancel_armed_mode()
            return

        out_path = Path(out_path_str)
        try:
            profile = dialog.selected_profile()
            image_path = None
            if visible and profile and profile.signature_image and dialog.use_signature_image():
                image_path = profile.signature_image

            result = self.doc.save_signed(
                out_path,
                signer,
                field_name=signing.next_field_name(self.doc.signature_field_names()),
                reason=dialog.reason(),
                location=dialog.location(),
                page_index=page_index if page_index is not None else 0,
                rect=rect,
                image_path=image_path,
            )

            QMessageBox.information(
                self, "Document Signed",
                f"Successfully digitally signed and saved:\n{out_path.name}\n\n"
                f"Signer: {result.signer_name}\n"
                f"Type: {'Self-Signed (Tamper-evident)' if result.self_signed else 'CA-Issued'}"
            )
            # Open signed copy in editor
            self.load_pdf(str(out_path))

        except Exception as exc:
            logger.error("Digital signing failed: %s", exc)
            QMessageBox.critical(self, "Signing Failed", f"Could not sign document:\n{exc}")
        finally:
            self.place_sig_btn.setChecked(False)
            if self.doc_view:
                self.doc_view.cancel_armed_mode()

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
        self.place_sig_btn.setEnabled(False)
        self.place_sig_btn.setChecked(False)
        self.sign_invis_action.setEnabled(False)
        self.sig_status_action.setEnabled(False)
        self.zoom_in_action.setEnabled(False)
        self.zoom_out_action.setEnabled(False)
        self.fit_width_action.setEnabled(False)
        self.close_action.setEnabled(False)
