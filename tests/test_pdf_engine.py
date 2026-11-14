"""
Unit tests for DocuTools PDF processing engine.
"""

import tempfile
from pathlib import Path
import fitz
from docutools.core.pdf_engine import PDFEngine


def _create_sample_pdf(file_path: Path, num_pages: int = 3) -> None:
    """Helper to generate a clean multi-page test PDF."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text(fitz.Point(50, 100), f"Test Document - Page {i + 1}", fontsize=20)
    doc.save(str(file_path))
    doc.close()


def test_pdf_info_and_thumbnails():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf_path, num_pages=4)

        info = PDFEngine.get_document_info(pdf_path)
        assert info["page_count"] == 4
        assert not info["is_encrypted"]
        assert len(info["pages_info"]) == 4

        thumb_bytes = PDFEngine.render_page_thumbnail(pdf_path, 0, target_width=150)
        assert len(thumb_bytes) > 0
        assert thumb_bytes.startswith(b"\x89PNG")  # Valid PNG signature


def test_pdf_merge():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf1 = Path(tmp_dir) / "part1.pdf"
        pdf2 = Path(tmp_dir) / "part2.pdf"
        _create_sample_pdf(pdf1, num_pages=2)
        _create_sample_pdf(pdf2, num_pages=3)

        out_merged = Path(tmp_dir) / "merged.pdf"
        PDFEngine.merge_pdfs([pdf1, pdf2], out_merged)

        assert out_merged.exists()
        merged_info = PDFEngine.get_document_info(out_merged)
        assert merged_info["page_count"] == 5


def test_pdf_split_ranges():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=6)

        out_dir = Path(tmp_dir) / "split_out"
        files = PDFEngine.split_pdf_by_ranges(pdf, "1-2, 4, 5-6", out_dir)
        assert len(files) == 3

        # Range 1-2 has 2 pages
        info_r1 = PDFEngine.get_document_info(files[0])
        assert info_r1["page_count"] == 2


def test_pdf_extract_pages():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=5)

        out_extracted = Path(tmp_dir) / "extracted.pdf"
        PDFEngine.extract_pages(pdf, [0, 2, 4], out_extracted)

        assert out_extracted.exists()
        info = PDFEngine.get_document_info(out_extracted)
        assert info["page_count"] == 3


def test_pdf_reorder():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=3)

        out_reordered = Path(tmp_dir) / "reordered.pdf"
        # Reverse order: [2, 1, 0]
        PDFEngine.reorder_and_rotate_pages(pdf, [2, 1, 0], output_path=out_reordered)

        assert out_reordered.exists()
        info = PDFEngine.get_document_info(out_reordered)
        assert info["page_count"] == 3


def test_pdf_compress():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=3)

        out_compressed = Path(tmp_dir) / "compressed.pdf"
        stats = PDFEngine.compress_pdf(pdf, out_compressed, quality_level="medium")

        assert out_compressed.exists()
        assert stats["compressed_size"] > 0


def test_pdf_protect():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=2)

        out_protected = Path(tmp_dir) / "protected.pdf"
        PDFEngine.protect_pdf(pdf, out_protected, user_password="SecretPassword123")

        assert out_protected.exists()
        info = PDFEngine.get_document_info(out_protected)
        assert info["is_encrypted"]


def test_pdf_annotation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=2)

        out_annotated = Path(tmp_dir) / "annotated.pdf"
        PDFEngine.add_annotation(
            file_path=pdf,
            output_path=out_annotated,
            annotation_type="stamp",
            text="APPROVED",
            font_size=20
        )

        assert out_annotated.exists()
        info = PDFEngine.get_document_info(out_annotated)
        assert info["page_count"] == 2


def test_pdf_search_and_redact():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=2)

        # Search
        results = PDFEngine.search_text_in_pdf(pdf, "Page 1")
        assert len(results) >= 1
        assert results[0]["page"] == 0

        # Redact / In-place replace
        out_redacted = Path(tmp_dir) / "redacted.pdf"
        stats = PDFEngine.redact_and_replace_text(
            file_path=pdf,
            output_path=out_redacted,
            search_term="Page 1",
            replacement_text="CENSORED"
        )
        assert out_redacted.exists()
        assert stats["occurrences_redacted"] >= 1

        # High-res rendering verification
        hires_bytes = PDFEngine.render_page_hires(out_redacted, 0, zoom=1.5)
        assert len(hires_bytes) > 0
        assert hires_bytes.startswith(b"\x89PNG")


def test_pdf_insert_content():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf, num_pages=1)

        out_content = Path(tmp_dir) / "content.pdf"
        items = [
            {"type": "text", "rect": (50, 50, 250, 90), "text": "Added Text Block", "fontsize": 14},
            {"type": "highlight", "rect": (50, 100, 250, 120), "color": (1, 1, 0)},
            {"type": "shape", "rect": (50, 130, 200, 180), "border_color": (0, 0, 1), "width": 2}
        ]

        PDFEngine.insert_content_on_page(pdf, out_content, page_index=0, items=items)
        assert out_content.exists()
        info = PDFEngine.get_document_info(out_content)
        assert info["page_count"] == 1
