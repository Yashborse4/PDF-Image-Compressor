"""
Unit tests for Large Page Preview & Inspection Dialog, Select All Pages, and Thumbnail inspection.
"""

import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from docutools.core.pdf_engine import PDFEngine
from docutools.ui.components.page_preview_dialog import PagePreviewDialog
from docutools.ui.components.thumbnail_card import ThumbnailCard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_pdf(tmp_path):
    import fitz
    pdf_path = tmp_path / "sample_multipage.pdf"
    doc = fitz.open()
    for i in range(5):
        p = doc.new_page(width=612, height=792)
        p.insert_text((50, 50), f"Sample Page {i+1}", fontsize=24)
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_thumbnail_card_inspect_signal(qapp):
    # Dummy 1x1 png bytes
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="blue").save(buf, format="PNG")
    png_bytes = buf.getvalue()

    card = ThumbnailCard(page_index=2, page_number=3, pixmap_bytes=png_bytes)

    received_inspect = []
    card.inspect_requested.connect(lambda idx: received_inspect.append(idx))

    # Click inspect button
    card.btn_inspect.click()
    assert received_inspect == [2]


def test_page_preview_dialog_init_and_navigation(qapp, sample_pdf):
    info = PDFEngine.get_document_info(sample_pdf)
    assert info["page_count"] == 5

    pages_data = [
        {"orig_index": i, "rotation": 0, "pixmap_bytes": PDFEngine.render_page_thumbnail(sample_pdf, i)}
        for i in range(5)
    ]

    dialog = PagePreviewDialog(
        file_path=sample_pdf,
        pages_data=pages_data,
        initial_index=0,
        selected_indices={1}
    )

    assert dialog.total_pages == 5
    assert dialog.current_index == 0
    assert not dialog.chk_current_page.isChecked()  # page 0 not selected initially

    # Navigate to page 1
    dialog._go_next_page()
    assert dialog.current_index == 1
    assert dialog.chk_current_page.isChecked()  # page 1 was in initial selected_indices

    # Navigate back
    dialog._go_previous_page()
    assert dialog.current_index == 0
    dialog.close()


def test_page_preview_dialog_select_all_and_deselect(qapp, sample_pdf):
    pages_data = [
        {"orig_index": i, "rotation": 0, "pixmap_bytes": PDFEngine.render_page_thumbnail(sample_pdf, i)}
        for i in range(5)
    ]

    dialog = PagePreviewDialog(
        file_path=sample_pdf,
        pages_data=pages_data,
        initial_index=0
    )

    all_signals = []
    deselect_signals = []
    dialog.select_all_requested.connect(lambda: all_signals.append(True))
    dialog.deselect_all_requested.connect(lambda: deselect_signals.append(True))

    # Select all pages
    dialog.btn_select_all.click()
    assert len(all_signals) == 1
    assert dialog.selected_indices == {0, 1, 2, 3, 4}
    assert dialog.chk_current_page.isChecked()
    assert "5 of 5 pages selected" in dialog.lbl_selection_summary.text()

    # Deselect all pages
    dialog.btn_deselect_all.click()
    assert len(deselect_signals) == 1
    assert len(dialog.selected_indices) == 0
    assert not dialog.chk_current_page.isChecked()
    assert "0 of 5 pages selected" in dialog.lbl_selection_summary.text()

    dialog.close()


def test_page_preview_dialog_rotate_and_extract(qapp, sample_pdf):
    pages_data = [
        {"orig_index": i, "rotation": 0, "pixmap_bytes": PDFEngine.render_page_thumbnail(sample_pdf, i)}
        for i in range(5)
    ]

    dialog = PagePreviewDialog(
        file_path=sample_pdf,
        pages_data=pages_data,
        initial_index=2
    )

    rotate_events = []
    dialog.rotate_page_requested.connect(lambda idx: rotate_events.append(idx))

    dialog.btn_rotate.click()
    assert rotate_events == [2]
    assert pages_data[2]["rotation"] == 90

    # Test extract request
    extract_events = []
    dialog.extract_requested.connect(lambda lst: extract_events.append(lst))

    dialog.select_all_pages()
    dialog.btn_extract_selected.click()
    assert extract_events == [[0, 1, 2, 3, 4]]

    dialog.close()


def test_page_preview_dialog_no_version_strings(qapp, sample_pdf):
    pages_data = [
        {"orig_index": 0, "rotation": 0, "pixmap_bytes": PDFEngine.render_page_thumbnail(sample_pdf, 0)}
    ]
    dialog = PagePreviewDialog(sample_pdf, pages_data)
    title = dialog.windowTitle().lower()
    assert "v1." not in title
    assert "v2." not in title
    assert "version" not in title
    dialog.close()
