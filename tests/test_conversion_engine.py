"""
Unit tests for DocuTools Conversion Engine.
"""

import tempfile
from pathlib import Path
import fitz
from PIL import Image
from PySide6.QtWidgets import QApplication
from docutools.core.conversion_engine import ConversionEngine

# Ensure QApplication instance exists for QPrinter / QTextDocument tests
app = QApplication.instance() or QApplication([])


def _create_test_pdf(file_path: Path, num_pages: int = 2) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=400, height=300)
        page.insert_text(fitz.Point(30, 50), f"Test Page {i+1} Content", fontsize=16)
    doc.save(str(file_path))
    doc.close()


def test_pdf_to_images():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "doc.pdf"
        _create_test_pdf(pdf_path, num_pages=2)

        out_dir = Path(tmp_dir) / "images_out"
        images = ConversionEngine.pdf_to_images(pdf_path, out_dir, image_format="PNG", dpi=100)
        assert len(images) == 2
        assert Path(images[0]).exists()
        assert Path(images[1]).exists()


def test_images_to_pdf():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img1 = Path(tmp_dir) / "i1.jpg"
        img2 = Path(tmp_dir) / "i2.jpg"
        Image.new("RGB", (300, 200), color="red").save(img1)
        Image.new("RGB", (300, 200), color="blue").save(img2)

        out_pdf = Path(tmp_dir) / "combined.pdf"
        ConversionEngine.images_to_pdf([img1, img2], out_pdf)

        assert out_pdf.exists()
        doc = fitz.open(str(out_pdf))
        assert len(doc) == 2
        doc.close()


def test_pdf_to_text():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "doc.pdf"
        _create_test_pdf(pdf_path, num_pages=2)

        out_txt = Path(tmp_dir) / "extracted.txt"
        ConversionEngine.pdf_to_text(pdf_path, out_txt)

        assert out_txt.exists()
        content = out_txt.read_text(encoding="utf-8")
        assert "Test Page 1 Content" in content
        assert "Test Page 2 Content" in content


def test_convert_image_format():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_src = Path(tmp_dir) / "source.png"
        Image.new("RGB", (200, 200), color="green").save(img_src)

        out_converted = ConversionEngine.convert_image_format(img_src, output_format="WEBP")
        assert Path(out_converted).exists()
        assert out_converted.endswith(".webp")
