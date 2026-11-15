"""
Unit tests for All-in-One PDF Studio, multi-PDF merging, page removal, and single-window ready export.
"""

import os
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from docutools.core.database import Database
from docutools.core.pdf_engine import PDFEngine
from docutools.ui.views.pdf_manager_view import PDFManagerView
from PySide6.QtCore import QThreadPool


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def two_sample_pdfs(tmp_path):
    import fitz
    p1 = tmp_path / "doc_alpha.pdf"
    p2 = tmp_path / "doc_beta.pdf"

    # Doc Alpha has 3 pages
    d1 = fitz.open()
    for i in range(3):
        p = d1.new_page()
        p.insert_text((50, 50), f"Alpha Page {i+1}")
    d1.save(str(p1))
    d1.close()

    # Doc Beta has 4 pages
    d2 = fitz.open()
    for i in range(4):
        p = d2.new_page()
        p.insert_text((50, 50), f"Beta Page {i+1}")
    d2.save(str(p2))
    d2.close()

    return str(p1), str(p2)


def test_pdf_engine_assemble_multiple_and_remove_pages(two_sample_pdfs, tmp_path):
    p1, p2 = two_sample_pdfs
    out_file = tmp_path / "assembled_ready.pdf"

    # Assemble: Alpha page 1, Beta page 2 (rotated 90), Beta page 4
    spec = [
        {"source_file": p1, "orig_index": 0, "rotation": 0},
        {"source_file": p2, "orig_index": 1, "rotation": 90},
        {"source_file": p2, "orig_index": 3, "rotation": 0},
    ]

    res = PDFEngine.assemble_pdf(
        pages_spec=spec,
        output_path=out_file,
        compress=True,
        watermark_text="APPROVED"
    )

    assert out_file.exists()
    assert res["pages_count"] == 3
    assert res["compressed"] is True

    import fitz
    doc = fitz.open(str(out_file))
    assert len(doc) == 3
    assert doc[1].rotation == 90
    doc.close()


def test_pdf_engine_assemble_with_encryption(two_sample_pdfs, tmp_path):
    p1, p2 = two_sample_pdfs
    out_file = tmp_path / "encrypted_ready.pdf"

    spec = [
        {"source_file": p1, "orig_index": 1, "rotation": 0},
        {"source_file": p2, "orig_index": 0, "rotation": 0},
    ]

    res = PDFEngine.assemble_pdf(
        pages_spec=spec,
        output_path=out_file,
        user_password="pass1234Secure",
        allow_printing=True,
        allow_copying=False
    )

    assert out_file.exists()
    assert res["protected"] is True

    import fitz
    doc = fitz.open(str(out_file))
    assert doc.is_encrypted
    assert doc.authenticate("pass1234Secure")
    assert len(doc) == 2
    doc.close()


def test_pdf_manager_view_all_in_one_workflow(qapp, two_sample_pdfs, tmp_path):
    p1, p2 = two_sample_pdfs
    db = Database(str(tmp_path / "test_studio.db"))
    pool = QThreadPool()

    view = PDFManagerView(db, pool)

    # 1. Add multiple PDFs simultaneously
    view._on_files_imported(([
        {"id": 1, "file_path": p1, "file_name": "doc_alpha.pdf", "file_size": 1000, "page_count": 3, "color": "#3b82f6"},
        {"id": 2, "file_path": p2, "file_name": "doc_beta.pdf", "file_size": 1200, "page_count": 4, "color": "#10b981"}
    ], [
        {"doc_id": 1, "doc_name": "doc_alpha.pdf", "doc_color": "#3b82f6", "source_file": p1, "orig_index": i, "rotation": 0, "pixmap_bytes": b""}
        for i in range(3)
    ] + [
        {"doc_id": 2, "doc_name": "doc_beta.pdf", "doc_color": "#10b981", "source_file": p2, "orig_index": i, "rotation": 0, "pixmap_bytes": b""}
        for i in range(4)
    ]))

    assert len(view.loaded_documents) == 2
    assert len(view.pages_data) == 7
    assert len(view.thumbnail_widgets) == 7
    assert "7 page(s) in workspace" in view.lbl_workspace_stat.text()

    # 2. Remove unneeded single page (e.g. index 2)
    view._on_card_delete(2)
    assert len(view.pages_data) == 6
    assert len(view.thumbnail_widgets) == 6

    # 3. Bulk remove unneeded pages using selection
    view.thumbnail_widgets[0].set_selected(True)
    view.thumbnail_widgets[1].set_selected(True)
    view._remove_selected_pages()
    assert len(view.pages_data) == 4
    assert len(view.thumbnail_widgets) == 4

    # 4. Check UI Ready panel controls exist in the same window
    assert view.btn_export_ready is not None
    assert view.chk_compress is not None
    assert view.chk_protect is not None
    assert view.chk_watermark is not None

    # 5. Remove an entire document
    view._remove_document(1)
    # Remaining pages should only belong to doc_id 2
    assert all(p["doc_id"] == 2 for p in view.pages_data)

    view.close()


def test_multigeneration_lossless_retention(tmp_path):
    import fitz
    import io
    from PIL import Image

    # 1. Create a master PDF with vector text, vector line, and embedded image
    doc = fitz.open()
    p = doc.new_page(width=612, height=792)
    p.insert_text((72, 72), "Lossless Multi-Cycle Test Line 12345", fontsize=18)
    p.draw_line(fitz.Point(72, 90), fitz.Point(540, 90), color=(0.1, 0.5, 0.8), width=2)

    target_pixel = (35, 115, 205)
    pil_im = Image.new("RGB", (200, 200), color=target_pixel)
    buf = io.BytesIO()
    pil_im.save(buf, format="PNG")
    p.insert_image(fitz.Rect(72, 120, 272, 320), stream=buf.getvalue())

    master_path = tmp_path / "master_test.pdf"
    doc.save(str(master_path), garbage=3, deflate=True, deflate_images=False, deflate_fonts=False, clean=False)
    doc.close()

    # 2. Cycle 6 times through assemble_pdf
    curr_path = master_path
    for c in range(6):
        next_path = tmp_path / f"cycle_{c+1}.pdf"
        spec = [{"source_file": str(curr_path), "orig_index": 0, "rotation": 0}]
        PDFEngine.assemble_pdf(pages_spec=spec, output_path=next_path, compress=False)
        curr_path = next_path

    # 3. Verify the 6th generation PDF
    final_doc = fitz.open(str(curr_path))
    final_page = final_doc[0]

    # Verify text preservation
    extracted_text = final_page.get_text()
    assert "Lossless Multi-Cycle Test Line 12345" in extracted_text

    # Verify vector drawing preservation
    drawings = final_page.get_drawings()
    assert len(drawings) == 1

    # Verify pixel-exact image preservation
    images = final_page.get_images()
    assert len(images) == 1
    xref = images[0][0]
    pix = fitz.Pixmap(final_doc, xref)
    assert (pix.width, pix.height) == (200, 200)
    assert pix.pixel(50, 50) == target_pixel, f"Pixel drifted: expected {target_pixel}, got {pix.pixel(50, 50)}"

    final_doc.close()
