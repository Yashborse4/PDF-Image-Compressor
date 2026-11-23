"""
Unit and integration tests for PDF Digital Signing & Verification in DocuTools.
Covers cryptographic PAdES signing, X.509 certificate generation, tamper detection,
signature stripping, and UI dialog validation.
"""

import tempfile
from pathlib import Path
import fitz
import pytest

from docutools.core.pdf_engine import PDFEngine
from docutools.ui.components.digital_signature_dialog import DigitalSignatureDialog


def _create_sample_pdf(file_path: Path, num_pages: int = 2) -> None:
    """Create a clean multi-page test PDF document."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text(fitz.Point(50, 100), f"DocuTools Test Document - Page {i + 1}", fontsize=18)
    doc.save(str(file_path))
    doc.close()


def test_generate_self_signed_certificate(tmp_path):
    """Test generating a standards-compliant RSA PKCS#12 bundle."""
    cert_path = tmp_path / "test_signer.p12"
    result_path = PDFEngine.generate_self_signed_certificate(
        out_path=cert_path,
        common_name="John Doe",
        password="MySecretPassword123",
        valid_days=365,
        key_size=2048,
    )

    assert Path(result_path).is_file()
    assert cert_path.stat().st_size > 500


def test_sign_pdf_invisible_and_verify(tmp_path):
    """Test applying an invisible PAdES digital signature and cryptographically verifying it."""
    pdf_in = tmp_path / "contract.pdf"
    _create_sample_pdf(pdf_in, num_pages=2)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Alice Corp", "Pass1234")

    pdf_signed = tmp_path / "contract_signed.pdf"
    res = PDFEngine.sign_pdf(
        file_path=pdf_in,
        output_path=pdf_signed,
        certificate_path=cert_path,
        password="Pass1234",
        reason="Official Approval",
        location="Headquarters",
        visible=False,
    )

    assert pdf_signed.is_file()
    assert res["signer_name"] == "Alice Corp"
    assert res["self_signed"] is True
    assert res["visible"] is False
    assert PDFEngine.has_digital_signatures(pdf_signed) is True

    # Cryptographic verification
    verifs = PDFEngine.verify_signatures(pdf_signed)
    assert len(verifs) == 1
    v = verifs[0]
    assert v["signer_name"] == "Alice Corp"
    assert v["intact"] is True
    assert v["valid"] is True
    assert v["tampered"] is False
    assert v["is_valid"] is True


def test_sign_pdf_visible_and_verify(tmp_path):
    """Test applying a visible signature with automated coordinate calculation and verify."""
    pdf_in = tmp_path / "invoice.pdf"
    _create_sample_pdf(pdf_in, num_pages=3)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Billing Dept", "Pass1234")

    pdf_signed = tmp_path / "invoice_signed.pdf"
    res = PDFEngine.sign_pdf(
        file_path=pdf_in,
        output_path=pdf_signed,
        certificate_path=cert_path,
        password="Pass1234",
        reason="Paid & Certified",
        visible=True,
        page_index=2,  # Sign on page 3
    )

    assert pdf_signed.is_file()
    assert res["visible"] is True
    assert res["page_index"] == 2

    # Check that PyMuPDF detects the signature widget on page 3
    doc = fitz.open(str(pdf_signed))
    widgets = list(doc[2].widgets())
    assert len(widgets) >= 1
    assert any(w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE and w.is_signed for w in widgets)
    doc.close()

    # Verification
    verifs = PDFEngine.verify_signatures(pdf_signed)
    assert len(verifs) == 1
    assert verifs[0]["is_valid"] is True


def test_tamper_detection(tmp_path):
    """Test that modifying bytes after signing is immediately flagged as tampered / broken."""
    pdf_in = tmp_path / "secure.pdf"
    _create_sample_pdf(pdf_in, num_pages=2)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Auditor", "Pass1234")

    pdf_signed = tmp_path / "secure_signed.pdf"
    PDFEngine.sign_pdf(
        file_path=pdf_in,
        output_path=pdf_signed,
        certificate_path=cert_path,
        password="Pass1234",
    )

    # Corrupt a byte in the signed PDF stream
    data = bytearray(pdf_signed.read_bytes())
    stream_idx = data.find(b"stream")
    assert stream_idx != -1
    data[stream_idx + 16] ^= 0xFF

    pdf_tampered = tmp_path / "secure_tampered.pdf"
    pdf_tampered.write_bytes(data)

    verifs = PDFEngine.verify_signatures(pdf_tampered)
    assert len(verifs) == 1
    v = verifs[0]
    # Either tampered is True or intact is False or is_valid is False
    assert v["is_valid"] is False
    assert v["intact"] is False or v["tampered"] is True or not v["valid"]


def test_strip_signatures(tmp_path):
    """Test safely removing digital signatures from a signed PDF."""
    pdf_in = tmp_path / "doc.pdf"
    _create_sample_pdf(pdf_in, num_pages=2)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Signer", "Pass1234")

    pdf_signed = tmp_path / "doc_signed.pdf"
    PDFEngine.sign_pdf(
        file_path=pdf_in,
        output_path=pdf_signed,
        certificate_path=cert_path,
        password="Pass1234",
    )
    assert PDFEngine.has_digital_signatures(pdf_signed) is True

    pdf_stripped = tmp_path / "doc_stripped.pdf"
    count = PDFEngine.strip_signatures(pdf_signed, pdf_stripped)
    assert count >= 1
    assert PDFEngine.has_digital_signatures(pdf_stripped) is False
    assert len(PDFEngine.verify_signatures(pdf_stripped)) == 0


def test_assemble_pdf_with_digital_signing(tmp_path):
    """Test PDFEngine.assemble_pdf directly applying a digital signature during export."""
    pdf1 = tmp_path / "part1.pdf"
    pdf2 = tmp_path / "part2.pdf"
    _create_sample_pdf(pdf1, num_pages=2)
    _create_sample_pdf(pdf2, num_pages=2)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Assembly Signer", "Pass1234")

    pages_spec = [
        {"source_file": pdf1, "orig_index": 0, "rotation": 0},
        {"source_file": pdf2, "orig_index": 1, "rotation": 0},
    ]
    out_pdf = tmp_path / "assembled_and_signed.pdf"

    res = PDFEngine.assemble_pdf(
        pages_spec=pages_spec,
        output_path=out_pdf,
        compress=True,
        sign_certificate_path=cert_path,
        sign_password="Pass1234",
        sign_reason="Final Merge Review",
        sign_visible=True,
    )

    assert res["signed"] is True
    assert out_pdf.is_file()

    verifs = PDFEngine.verify_signatures(out_pdf)
    assert len(verifs) == 1
    assert verifs[0]["is_valid"] is True
    assert verifs[0]["signer_name"] == "Assembly Signer"


def test_digital_signing_error_handling(tmp_path):
    """Test error handling for bad passwords, non-existent files, and conflicting security."""
    pdf_in = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_in, num_pages=1)

    cert_path = tmp_path / "signer.p12"
    PDFEngine.generate_self_signed_certificate(cert_path, "Signer", "CorrectPassword")

    # 1. Wrong password
    with pytest.raises(Exception):
        PDFEngine.sign_pdf(
            file_path=pdf_in,
            output_path=tmp_path / "out.pdf",
            certificate_path=cert_path,
            password="WrongPassword",
        )

    # 2. Missing source PDF
    with pytest.raises(FileNotFoundError):
        PDFEngine.sign_pdf(
            file_path=tmp_path / "non_existent.pdf",
            output_path=tmp_path / "out.pdf",
            certificate_path=cert_path,
            password="CorrectPassword",
        )

    # 3. Conflicting AES-256 encryption and digital signing in assemble_pdf
    with pytest.raises(ValueError, match="Cannot apply digital signature and AES-256"):
        PDFEngine.assemble_pdf(
            pages_spec=[{"source_file": pdf_in, "orig_index": 0}],
            output_path=tmp_path / "conflict.pdf",
            user_password="LockPassword",
            sign_certificate_path=cert_path,
            sign_password="CorrectPassword",
        )


def test_digital_signature_dialog_ui(qapp, tmp_path):
    """Test offscreen instantiation of DigitalSignatureDialog."""
    pdf_in = tmp_path / "ui_test.pdf"
    _create_sample_pdf(pdf_in, num_pages=2)

    dialog = DigitalSignatureDialog(initial_pdf_path=pdf_in)

    assert dialog.tabs.count() == 3
    assert dialog.txt_verify_path.text() == str(pdf_in)
    assert dialog.txt_sign_input.text() == str(pdf_in)
    assert "ui_test_signed.pdf" in dialog.txt_sign_output.text()
    dialog.close()
