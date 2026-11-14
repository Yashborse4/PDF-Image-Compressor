"""
Unit tests for DocuTools DOCX Engine.
"""

import tempfile
from pathlib import Path
from docx import Document
from docutools.core.docx_engine import DocxEngine


def _create_sample_docx(file_path: Path) -> None:
    doc = Document()
    doc.add_heading("DocuTools Test Document", level=1)
    p = doc.add_paragraph("This is a formatted test paragraph with ")
    run_b = p.add_run("bold text")
    run_b.bold = True
    p.add_run(" and ")
    run_i = p.add_run("italic text.")
    run_i.italic = True

    # Add a table
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Header 1"
    table.rows[0].cells[1].text = "Header 2"
    table.rows[1].cells[0].text = "Value A"
    table.rows[1].cells[1].text = "Value B"

    doc.save(str(file_path))


def test_docx_to_html():
    with tempfile.TemporaryDirectory() as tmp_dir:
        docx_path = Path(tmp_dir) / "test.docx"
        _create_sample_docx(docx_path)

        html_out = DocxEngine.docx_to_html(docx_path)
        assert "DocuTools Test Document" in html_out
        assert "<b>bold text</b>" in html_out
        assert "<i>italic text.</i>" in html_out
        assert "<table>" in html_out


def test_html_to_docx():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_html = (
            "<h1>Report Title</h1>"
            "<p>Here is an important sentence with <b>strong bold</b> text.</p>"
            "<table><tr><th>Col 1</th><th>Col 2</th></tr><tr><td>Val 1</td><td>Val 2</td></tr></table>"
        )
        out_docx = Path(tmp_dir) / "generated.docx"
        DocxEngine.html_to_docx(sample_html, out_docx)

        assert out_docx.exists()
        doc = Document(str(out_docx))
        assert len(doc.paragraphs) >= 2
        assert len(doc.tables) >= 1
