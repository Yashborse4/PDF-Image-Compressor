"""
Digital Signature & Verification Dialog for DocuTools.
Provides cryptographic PAdES / PKCS#7 signing, signature validation, tamper detection,
and self-signed X.509 certificate generation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.pdf_engine import PDFEngine
from docutools.workers.task_worker import TaskWorker


class DigitalSignatureDialog(QDialog):
    """Multi-tab cryptographic digital signing, validation, and certificate manager dialog."""

    signature_applied = Signal(str)  # Emitted with the output path of the signed PDF

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_pdf_path: Optional[str | Path] = None,
        database: Optional[Database] = None,
        thread_pool: Optional[QThreadPool] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("DocuTools — Digital Signature & Verification Suite")
        self.resize(880, 680)
        self.setMinimumSize(780, 560)

        self.db = database or Database()
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._initial_pdf = str(initial_pdf_path) if initial_pdf_path else ""

        self._init_ui()

        if self._initial_pdf and Path(self._initial_pdf).is_file():
            self.txt_verify_path.setText(self._initial_pdf)
            self.txt_sign_input.setText(self._initial_pdf)
            self._update_default_output_path(self._initial_pdf)
            # Auto-run verify on initial file
            self._execute_verification()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("🔏 Cryptographic Digital Signatures (PAdES / PKCS#7)")
        lbl_heading.setStyleSheet("font-size: 16px; font-weight: bold; color: #60a5fa;")
        lbl_sub = QLabel(
            "Certify document authenticity, verify cryptographic integrity, and detect unauthorized alterations."
        )
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        # Tab Widget
        self.tabs = QTabWidget(self)

        self.tab_verify = QWidget()
        self.tab_sign = QWidget()
        self.tab_cert = QWidget()

        self.tabs.addTab(self.tab_verify, "🔍 Verify Document Signatures")
        self.tabs.addTab(self.tab_sign, "✍️ Sign PDF Document")
        self.tabs.addTab(self.tab_cert, "🔑 Create Test Certificate")

        main_layout.addWidget(self.tabs, stretch=1)

        self._build_verify_tab()
        self._build_sign_tab()
        self._build_cert_tab()

        # Bottom Close Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        main_layout.addLayout(btn_row)

    # =========================================================================
    # TAB 1: SIGNATURE VERIFICATION & TAMPER DETECTION
    # =========================================================================
    def _build_verify_tab(self) -> None:
        layout = QVBoxLayout(self.tab_verify)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # File picker row
        file_box = QGroupBox("Select Document to Verify")
        file_lay = QHBoxLayout(file_box)
        self.txt_verify_path = QLineEdit()
        self.txt_verify_path.setPlaceholderText("Select or enter path to PDF document...")
        file_lay.addWidget(self.txt_verify_path, stretch=1)

        btn_browse = QPushButton("Browse PDF...")
        btn_browse.clicked.connect(self._browse_verify_file)
        file_lay.addWidget(btn_browse)

        btn_run_verify = QPushButton("🔍 Check Signatures")
        btn_run_verify.setProperty("class", "primaryButton")
        btn_run_verify.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 6px 14px; border-radius: 4px;"
        )
        btn_run_verify.clicked.connect(self._execute_verification)
        file_lay.addWidget(btn_run_verify)
        layout.addWidget(file_box)

        # Verdict Banner Frame
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("""
            QFrame {
                background-color: #1e222b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        banner_lay = QHBoxLayout(self.banner_frame)
        self.lbl_banner_icon = QLabel("ℹ️")
        self.lbl_banner_icon.setStyleSheet("font-size: 24px;")
        banner_lay.addWidget(self.lbl_banner_icon)

        self.lbl_banner_text = QLabel("No document verified yet. Select a PDF and click 'Check Signatures'.")
        self.lbl_banner_text.setWordWrap(True)
        self.lbl_banner_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #cbd5e1;")
        banner_lay.addWidget(self.lbl_banner_text, stretch=1)
        layout.addWidget(self.banner_frame)

        # Signatures Table
        layout.addWidget(QLabel("Embedded Digital Signatures:"))
        self.table_signatures = QTableWidget(0, 5)
        self.table_signatures.setHorizontalHeaderLabels([
            "Field Name", "Signer Common Name", "Integrity Status", "Cryptographic Check", "Details / Diagnostics"
        ])
        header = self.table_signatures.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_signatures.setAlternatingRowColors(True)
        self.table_signatures.setStyleSheet("""
            QTableWidget {
                background-color: #18191d;
                border: 1px solid #282a30;
                gridline-color: #282a30;
            }
        """)
        layout.addWidget(self.table_signatures, stretch=1)

    def _browse_verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to Verify", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.txt_verify_path.setText(path)
            self._execute_verification()

    def _execute_verification(self) -> None:
        file_path = self.txt_verify_path.text().strip()
        if not file_path or not Path(file_path).is_file():
            QMessageBox.warning(self, "Invalid File", "Please select a valid PDF file to verify.")
            return

        try:
            results = PDFEngine.verify_signatures(file_path)
            self.table_signatures.setRowCount(0)

            if not results:
                self.lbl_banner_icon.setText("⚪")
                self.lbl_banner_text.setText(
                    f"No digital signatures found in '{Path(file_path).name}'.\n"
                    "This document is unsigned or contains only standard non-cryptographic visual annotations."
                )
                self.banner_frame.setStyleSheet("""
                    QFrame {
                        background-color: #1e222b;
                        border: 1px solid #475569;
                        border-radius: 6px;
                        padding: 10px;
                    }
                """)
                return

            has_tampered = any(r.get("tampered") or not r.get("intact") for r in results)
            all_valid = all(r.get("is_valid") for r in results)

            if has_tampered:
                self.lbl_banner_icon.setText("🚨")
                self.lbl_banner_text.setText(
                    "TAMPERING DETECTED! The document has been altered or byte-modified after signing!\n"
                    "At least one digital signature was invalidated because the file was changed after application."
                )
                self.banner_frame.setStyleSheet("""
                    QFrame {
                        background-color: #450a0a;
                        border: 1px solid #ef4444;
                        border-radius: 6px;
                        padding: 10px;
                    }
                """)
            elif all_valid:
                self.lbl_banner_icon.setText("🛡️")
                self.lbl_banner_text.setText(
                    f"ALL SIGNATURES VALID & INTACT! ({len(results)} signature{'s' if len(results) > 1 else ''})\n"
                    "The document's cryptographic integrity is guaranteed. No modifications have occurred since signing."
                )
                self.banner_frame.setStyleSheet("""
                    QFrame {
                        background-color: #064e3b;
                        border: 1px solid #10b981;
                        border-radius: 6px;
                        padding: 10px;
                    }
                """)
            else:
                self.lbl_banner_icon.setText("⚠️")
                self.lbl_banner_text.setText(
                    "Signatures detected with warnings. One or more certificates may be self-signed or untrusted."
                )
                self.banner_frame.setStyleSheet("""
                    QFrame {
                        background-color: #451a03;
                        border: 1px solid #f59e0b;
                        border-radius: 6px;
                        padding: 10px;
                    }
                """)

            # Populate table
            for row, r in enumerate(results):
                self.table_signatures.insertRow(row)

                # Field name
                f_item = QTableWidgetItem(r.get("field_name") or "Signature")
                self.table_signatures.setItem(row, 0, f_item)

                # Signer name
                s_name = r.get("signer_name") or "(Unknown Signer)"
                s_item = QTableWidgetItem(s_name)
                self.table_signatures.setItem(row, 1, s_item)

                # Integrity
                intact = r.get("intact") and not r.get("tampered")
                integ_item = QTableWidgetItem("✅ Intact (Unmodified)" if intact else "❌ Modified / Tampered")
                integ_item.setForeground(Qt.GlobalColor.green if intact else Qt.GlobalColor.red)
                self.table_signatures.setItem(row, 2, integ_item)

                # Valid
                valid = r.get("valid")
                val_item = QTableWidgetItem("✅ Cryptographically Valid" if valid else "❌ Invalid Signature")
                val_item.setForeground(Qt.GlobalColor.green if valid else Qt.GlobalColor.red)
                self.table_signatures.setItem(row, 3, val_item)

                # Details
                prob = r.get("problem")
                trust = "Chains to Trusted Root" if r.get("trusted") else "Self-Signed / Local Certificate"
                detail_text = prob if prob else f"Integrity verified. {trust}."
                det_item = QTableWidgetItem(detail_text)
                self.table_signatures.setItem(row, 4, det_item)

            self.db.log_operation(
                module="Digital Signature",
                action="Verify Signatures",
                input_summary=f"Checked {len(results)} signatures in {Path(file_path).name}",
                output_file=file_path,
                status="success" if not has_tampered else "warning",
            )

        except Exception as exc:
            QMessageBox.critical(self, "Verification Error", f"Failed to verify signatures:\n{exc}")

    # =========================================================================
    # TAB 2: SIGN DOCUMENT
    # =========================================================================
    def _build_sign_tab(self) -> None:
        layout = QVBoxLayout(self.tab_sign)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Source & Output files
        grp_files = QGroupBox("Documents")
        lay_f = QVBoxLayout(grp_files)
        lay_f.setSpacing(6)

        row_in = QHBoxLayout()
        row_in.addWidget(QLabel("PDF to Sign:"))
        self.txt_sign_input = QLineEdit()
        self.txt_sign_input.setPlaceholderText("Select PDF to sign...")
        self.txt_sign_input.textChanged.connect(self._update_default_output_path)
        row_in.addWidget(self.txt_sign_input, stretch=1)
        btn_in_browse = QPushButton("Browse...")
        btn_in_browse.clicked.connect(self._browse_sign_input)
        row_in.addWidget(btn_in_browse)
        lay_f.addLayout(row_in)

        row_out = QHBoxLayout()
        row_out.addWidget(QLabel("Output File:"))
        self.txt_sign_output = QLineEdit()
        self.txt_sign_output.setPlaceholderText("Select where to save signed PDF...")
        row_out.addWidget(self.txt_sign_output, stretch=1)
        btn_out_browse = QPushButton("Save As...")
        btn_out_browse.clicked.connect(self._browse_sign_output)
        row_out.addWidget(btn_out_browse)
        lay_f.addLayout(row_out)
        layout.addWidget(grp_files)

        # 2. Certificate Credentials
        grp_cert = QGroupBox("Signing Certificate (.p12 / .pfx)")
        lay_c = QVBoxLayout(grp_cert)
        lay_c.setSpacing(6)

        row_cert = QHBoxLayout()
        row_cert.addWidget(QLabel("Certificate:"))
        self.txt_cert_file = QLineEdit()
        self.txt_cert_file.setPlaceholderText("Path to .p12 or .pfx certificate bundle...")
        saved_cert = self.db.get_setting("last_signing_cert", "")
        if saved_cert and Path(saved_cert).is_file():
            self.txt_cert_file.setText(saved_cert)
        row_cert.addWidget(self.txt_cert_file, stretch=1)
        btn_c_browse = QPushButton("Browse...")
        btn_c_browse.clicked.connect(self._browse_cert_file)
        row_cert.addWidget(btn_c_browse)

        btn_quick_create = QPushButton("🔑 Create New Cert...")
        btn_quick_create.setToolTip("Switch to certificate generator tab")
        btn_quick_create.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        row_cert.addWidget(btn_quick_create)
        lay_c.addLayout(row_cert)

        row_pwd = QHBoxLayout()
        row_pwd.addWidget(QLabel("Password:"))
        self.txt_cert_pwd = QLineEdit()
        self.txt_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_cert_pwd.setPlaceholderText("Enter password for PKCS#12 bundle")
        row_pwd.addWidget(self.txt_cert_pwd, stretch=1)

        self.btn_toggle_pwd = QPushButton("👁 Show")
        self.btn_toggle_pwd.setCheckable(True)
        self.btn_toggle_pwd.clicked.connect(self._toggle_pwd_visibility)
        row_pwd.addWidget(self.btn_toggle_pwd)
        lay_c.addLayout(row_pwd)
        layout.addWidget(grp_cert)

        # 3. Metadata & Signature Appearance
        grp_meta = QGroupBox("Signature Metadata & Visual Appearance")
        lay_m = QVBoxLayout(grp_meta)
        lay_m.setSpacing(6)

        row_m1 = QHBoxLayout()
        row_m1.addWidget(QLabel("Reason:"))
        self.txt_sign_reason = QLineEdit("Approved & Certified")
        self.txt_sign_reason.setPlaceholderText("e.g. Contract Sign-off, Approved for Release")
        row_m1.addWidget(self.txt_sign_reason, stretch=1)

        row_m1.addWidget(QLabel("Location:"))
        self.txt_sign_loc = QLineEdit()
        self.txt_sign_loc.setPlaceholderText("e.g. New York, USA")
        row_m1.addWidget(self.txt_sign_loc, stretch=1)
        lay_m.addLayout(row_m1)

        # Presets for reason
        row_chips = QHBoxLayout()
        row_chips.addWidget(QLabel("Presets:"))
        for preset in ["Approved", "Contract Sign-off", "Reviewed & Verified", "Final Release"]:
            b = QPushButton(preset)
            b.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            b.clicked.connect(lambda chk=False, t=preset: self.txt_sign_reason.setText(t))
            row_chips.addWidget(b)
        row_chips.addStretch()
        lay_m.addLayout(row_chips)

        # Appearance type
        row_app = QHBoxLayout()
        self.rad_invis = QRadioButton("Invisible Signature (PAdES Cryptographic Metadata only)")
        self.rad_vis = QRadioButton("Visible Signature (Visual Stamp & Field on Page)")
        self.rad_vis.setChecked(True)
        self.grp_rad = QButtonGroup(self)
        self.grp_rad.addButton(self.rad_invis)
        self.grp_rad.addButton(self.rad_vis)
        row_app.addWidget(self.rad_vis)
        row_app.addWidget(self.rad_invis)
        row_app.addStretch()
        lay_m.addLayout(row_app)

        # Visual settings container
        self.frame_vis_opts = QFrame()
        lay_vo = QHBoxLayout(self.frame_vis_opts)
        lay_vo.setContentsMargins(0, 4, 0, 0)
        lay_vo.setSpacing(10)

        lay_vo.addWidget(QLabel("Page Index (1-based):"))
        self.spin_page_idx = QSpinBox()
        self.spin_page_idx.setRange(1, 9999)
        self.spin_page_idx.setValue(1)
        lay_vo.addWidget(self.spin_page_idx)

        lay_vo.addWidget(QLabel("Position:"))
        self.combo_pos = QComboBox()
        self.combo_pos.addItems([
            "Bottom-Right (Standard)",
            "Bottom-Left",
            "Top-Right",
            "Top-Left"
        ])
        lay_vo.addWidget(self.combo_pos)

        lay_vo.addWidget(QLabel("Stamp Image (Optional):"))
        self.txt_stamp_img = QLineEdit()
        self.txt_stamp_img.setPlaceholderText("PNG / JPEG signature skin...")
        lay_vo.addWidget(self.txt_stamp_img, stretch=1)
        btn_img_browse = QPushButton("Browse...")
        btn_img_browse.clicked.connect(self._browse_stamp_img)
        lay_vo.addWidget(btn_img_browse)

        self.rad_vis.toggled.connect(self.frame_vis_opts.setVisible)
        lay_m.addWidget(self.frame_vis_opts)
        layout.addWidget(grp_meta)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_sign_status = QLabel("")
        self.lbl_sign_status.setStyleSheet("color: #60a5fa; font-weight: 500;")
        self.lbl_sign_status.hide()
        layout.addWidget(self.lbl_sign_status)

        # Sign Action Button
        btn_sign = QPushButton("✍️ Digitally Sign PDF Document...")
        btn_sign.setProperty("class", "primaryButton")
        btn_sign.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 700; font-size: 14px; padding: 10px; border-radius: 6px;"
        )
        btn_sign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sign.clicked.connect(self._execute_sign_pdf)
        layout.addWidget(btn_sign)
        layout.addStretch()

    def _toggle_pwd_visibility(self) -> None:
        if self.btn_toggle_pwd.isChecked():
            self.txt_cert_pwd.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pwd.setText("🔒 Hide")
        else:
            self.txt_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pwd.setText("👁 Show")

    def _browse_sign_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to Sign", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.txt_sign_input.setText(path)
            self._update_default_output_path(path)

    def _browse_sign_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Signed PDF Destination", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.txt_sign_output.setText(path)

    def _browse_cert_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Certificate Bundle", "", "PKCS#12 Bundles (*.p12 *.pfx);;All Files (*.*)"
        )
        if path:
            self.txt_cert_file.setText(path)
            self.db.set_setting("last_signing_cert", path)

    def _browse_stamp_img(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Signature Image", "", "Image Files (*.png *.jpg *.jpeg);;All Files (*.*)"
        )
        if path:
            self.txt_stamp_img.setText(path)

    def _update_default_output_path(self, in_path: str) -> None:
        if in_path:
            p = Path(in_path)
            suggested = p.parent / f"{p.stem}_signed{p.suffix}"
            self.txt_sign_output.setText(str(suggested))

    def _execute_sign_pdf(self) -> None:
        in_pdf = self.txt_sign_input.text().strip()
        out_pdf = self.txt_sign_output.text().strip()
        cert_path = self.txt_cert_file.text().strip()
        cert_pwd = self.txt_cert_pwd.text()
        reason = self.txt_sign_reason.text().strip()
        location = self.txt_sign_loc.text().strip()
        visible = self.rad_vis.isChecked()
        page_idx = max(0, self.spin_page_idx.value() - 1)
        img_path = self.txt_stamp_img.text().strip() or None

        if not in_pdf or not Path(in_pdf).is_file():
            QMessageBox.warning(self, "Missing Document", "Please select a valid PDF to sign.")
            return

        if not out_pdf:
            QMessageBox.warning(self, "Missing Output Path", "Please specify the destination signed PDF path.")
            return

        if not cert_path or not Path(cert_path).is_file():
            QMessageBox.warning(
                self, "Missing Certificate",
                "Please choose an existing .p12/.pfx certificate file, or click 'Create New Cert' to generate one."
            )
            return

        # Calculate coordinates based on position preset
        rect = None
        if visible:
            info = PDFEngine.get_document_info(in_pdf)
            page_count = info.get("page_count", 1)
            page_idx = min(page_idx, max(0, page_count - 1))
            pages_info = info.get("pages_info", [])
            pw = pages_info[page_idx]["width"] if pages_info else 595.0
            ph = pages_info[page_idx]["height"] if pages_info else 842.0

            pos = self.combo_pos.currentText()
            bw, bh = 180.0, 60.0
            margin = 20.0
            if "Bottom-Right" in pos:
                rect = (pw - bw - margin, ph - bh - margin, pw - margin, ph - margin)
            elif "Bottom-Left" in pos:
                rect = (margin, ph - bh - margin, margin + bw, ph - margin)
            elif "Top-Right" in pos:
                rect = (pw - bw - margin, margin, pw - margin, margin + bh)
            elif "Top-Left" in pos:
                rect = (margin, margin, margin + bw, margin + bh)

        self.progress_bar.show()
        self.progress_bar.setValue(10)
        self.lbl_sign_status.show()
        self.lbl_sign_status.setText("Signing document in background...")

        def _worker_fn(progress_callback=None):
            return PDFEngine.sign_pdf(
                file_path=in_pdf,
                output_path=out_pdf,
                certificate_path=cert_path,
                password=cert_pwd,
                reason=reason,
                location=location,
                visible=visible,
                page_index=page_idx,
                rect=rect,
                image_path=img_path,
                progress_callback=progress_callback,
            )

        worker = TaskWorker(_worker_fn)
        worker.signals.progress.connect(self._on_sign_progress)
        worker.signals.finished.connect(self._on_sign_success)
        worker.signals.error.connect(self._on_sign_error)
        self.thread_pool.start(worker)

    def _on_sign_progress(self, pct: int, msg: str) -> None:
        self.progress_bar.setValue(pct)
        self.lbl_sign_status.setText(msg)

    def _on_sign_success(self, result: Dict[str, Any]) -> None:
        self.progress_bar.hide()
        self.lbl_sign_status.hide()

        out_path = result.get("output_file")
        signer = result.get("signer_name") or "Signer"
        self_signed = result.get("self_signed", False)

        msg = (
            f"Successfully applied digital signature to:\n{out_path}\n\n"
            f"Signer: {signer}\n"
            f"Type: {'Self-Signed Certificate' if self_signed else 'CA-Issued Certificate'}\n"
            f"Timestamp & ByteRange hash locked."
        )
        QMessageBox.information(self, "Document Signed", msg)

        # Save last cert path
        cert_p = self.txt_cert_file.text().strip()
        if cert_p:
            self.db.set_setting("last_signing_cert", cert_p)

        self.db.log_operation(
            module="Digital Signature",
            action="Sign PDF",
            input_summary=f"Signed as {signer}",
            output_file=out_path,
            initial_size=Path(self.txt_sign_input.text()).stat().st_size,
            final_size=Path(out_path).stat().st_size,
            status="success",
        )

        self.signature_applied.emit(out_path)

        # Switch to Verify tab to show the new signature
        self.txt_verify_path.setText(out_path)
        self.tabs.setCurrentIndex(0)
        self._execute_verification()

    def _on_sign_error(self, err_msg: str, traceback_str: str) -> None:
        self.progress_bar.hide()
        self.lbl_sign_status.hide()
        QMessageBox.critical(self, "Signing Failed", f"Could not digitally sign PDF:\n\n{err_msg}")

    # =========================================================================
    # TAB 3: SELF-SIGNED CERTIFICATE GENERATOR
    # =========================================================================
    def _build_cert_tab(self) -> None:
        layout = QVBoxLayout(self.tab_cert)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        grp_info = QGroupBox("Certificate Identity & Security")
        lay_i = QVBoxLayout(grp_info)
        lay_i.setSpacing(8)

        row_cn = QHBoxLayout()
        row_cn.addWidget(QLabel("Full Name / Common Name (CN):"))
        self.txt_cert_cn = QLineEdit()
        self.txt_cert_cn.setPlaceholderText("e.g. John Doe, Acme Corporation")
        row_cn.addWidget(self.txt_cert_cn, stretch=1)
        lay_i.addLayout(row_cn)

        row_p1 = QHBoxLayout()
        row_p1.addWidget(QLabel("Certificate Password:"))
        self.txt_gen_pwd1 = QLineEdit()
        self.txt_gen_pwd1.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gen_pwd1.setPlaceholderText("Enter password to protect .p12 bundle")
        row_p1.addWidget(self.txt_gen_pwd1, stretch=1)

        row_p1.addWidget(QLabel("Confirm Password:"))
        self.txt_gen_pwd2 = QLineEdit()
        self.txt_gen_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gen_pwd2.setPlaceholderText("Re-type password")
        row_p1.addWidget(self.txt_gen_pwd2, stretch=1)
        lay_i.addLayout(row_p1)

        row_params = QHBoxLayout()
        row_params.addWidget(QLabel("Validity:"))
        self.combo_validity = QComboBox()
        self.combo_validity.addItems(["3 Years (1095 days)", "1 Year (365 days)", "5 Years (1825 days)"])
        row_params.addWidget(self.combo_validity)

        row_params.addWidget(QLabel("Key Size:"))
        self.combo_keysize = QComboBox()
        self.combo_keysize.addItems(["RSA 2048-bit (Standard)", "RSA 4096-bit (High Security)"])
        row_params.addWidget(self.combo_keysize)
        row_params.addStretch()
        lay_i.addLayout(row_params)

        row_dest = QHBoxLayout()
        row_dest.addWidget(QLabel("Save Certificate As:"))
        self.txt_cert_dest = QLineEdit()
        default_dir = Path.home() / "Documents" / "DocuTools"
        default_dir.mkdir(parents=True, exist_ok=True)
        self.txt_cert_dest.setText(str(default_dir / "my_signing_certificate.p12"))
        row_dest.addWidget(self.txt_cert_dest, stretch=1)
        btn_dest_browse = QPushButton("Browse...")
        btn_dest_browse.clicked.connect(self._browse_cert_dest)
        row_dest.addWidget(btn_dest_browse)
        lay_i.addLayout(row_dest)
        layout.addWidget(grp_info)

        lbl_note = QLabel(
            "ℹ️ Note: Self-signed certificates provide tamper-evident cryptographic authentication. "
            "PDF viewers (like Adobe Acrobat) will show the signature as intact and tamper-free, "
            "with an 'unknown/self-signed' issuer until trusted."
        )
        lbl_note.setWordWrap(True)
        lbl_note.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_note)

        btn_generate = QPushButton("🔑 Generate PKCS#12 Certificate (.p12)")
        btn_generate.setProperty("class", "primaryButton")
        btn_generate.setStyleSheet(
            "background-color: #059669; color: #ffffff; font-weight: 700; font-size: 13px; padding: 10px; border-radius: 6px;"
        )
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.clicked.connect(self._execute_generate_cert)
        layout.addWidget(btn_generate)
        layout.addStretch()

    def _browse_cert_dest(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Certificate Bundle", self.txt_cert_dest.text(), "PKCS#12 Bundles (*.p12 *.pfx)"
        )
        if path:
            self.txt_cert_dest.setText(path)

    def _execute_generate_cert(self) -> None:
        cn = self.txt_cert_cn.text().strip()
        pwd1 = self.txt_gen_pwd1.text()
        pwd2 = self.txt_gen_pwd2.text()
        dest = self.txt_cert_dest.text().strip()

        if not cn:
            QMessageBox.warning(self, "Missing Name", "Please enter a Common Name (e.g. your name or company).")
            return
        if not pwd1:
            QMessageBox.warning(self, "Missing Password", "Please enter a password to protect the certificate.")
            return
        if pwd1 != pwd2:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match. Please re-enter.")
            return
        if not dest:
            QMessageBox.warning(self, "Missing Destination", "Please specify a destination file path.")
            return

        valid_days = 1095
        if "1 Year" in self.combo_validity.currentText():
            valid_days = 365
        elif "5 Years" in self.combo_validity.currentText():
            valid_days = 1825

        key_size = 4096 if "4096" in self.combo_keysize.currentText() else 2048

        try:
            out_p = PDFEngine.generate_self_signed_certificate(
                out_path=dest,
                common_name=cn,
                password=pwd1,
                valid_days=valid_days,
                key_size=key_size,
            )
            QMessageBox.information(
                self, "Certificate Created",
                f"Successfully generated PKCS#12 certificate:\n{out_p}\n\n"
                f"Common Name: {cn}\n"
                f"Validity: {valid_days} days\n"
                f"Key Size: {key_size}-bit RSA"
            )

            # Auto-populate Tab 2
            self.txt_cert_file.setText(out_p)
            self.txt_cert_pwd.setText(pwd1)
            self.db.set_setting("last_signing_cert", out_p)
            self.tabs.setCurrentIndex(1)  # Switch to Sign tab

        except Exception as exc:
            QMessageBox.critical(self, "Certificate Error", f"Failed to generate certificate:\n{exc}")
