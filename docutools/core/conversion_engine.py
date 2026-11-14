"""
Universal Conversion Engine for DocuTools.
Supports multi-directional conversions between PDF, DOCX, and images.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import fitz  # PyMuPDF
from PIL import Image
from PySide6.QtGui import QTextDocument
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter

from docutools.core.docx_engine import DocxEngine
from docutools.core.validator import validate_file


class ConversionEngine:
    """Core headless engine handling format conversions."""

    @staticmethod
    def pdf_to_images(
        pdf_path: str | Path,
        output_dir: str | Path,
        image_format: str = "PNG",  # PNG, JPEG, WEBP
        dpi: int = 200,
        page_indices: Optional[Sequence[int]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[str]:
        """Convert PDF pages to image files."""
        src_p = Path(pdf_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        ext = image_format.lower()
        if ext == "jpeg":
            ext = "jpg"

        doc = fitz.open(str(src_p))
        total_pages = len(doc)
        pages = page_indices if page_indices is not None else list(range(total_pages))
        generated_files: List[str] = []

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for i, p_idx in enumerate(pages):
            if 0 <= p_idx < total_pages:
                if progress_callback:
                    pct = int(((i + 1) / max(len(pages), 1)) * 100)
                    progress_callback(pct, f"Rendering page {p_idx+1}/{total_pages}...")

                page = doc[p_idx]
                pix = page.get_pixmap(matrix=matrix, alpha=(ext == "png"))
                out_file = out_d / f"{src_p.stem}_page_{p_idx+1:03d}.{ext}"
                pix.save(str(out_file))
                generated_files.append(str(out_file))

        doc.close()
        return generated_files

    @staticmethod
    def images_to_pdf(
        image_paths: Sequence[str | Path],
        output_pdf_path: str | Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """Combine multiple images into a single PDF document."""
        out_p = Path(output_pdf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open()
        total = len(image_paths)

        for idx, img_path in enumerate(image_paths):
            if progress_callback:
                pct = int(((idx + 1) / max(total, 1)) * 90)
                progress_callback(pct, f"Adding image {idx+1}/{total}: {Path(img_path).name}")

            p = Path(img_path)
            with Image.open(p) as pil_img:
                w, h = pil_img.size

            # Create PDF page with image dimensions
            rect = fitz.Rect(0, 0, w, h)
            page = doc.new_page(width=w, height=h)
            page.insert_image(rect, filename=str(p))

        if progress_callback:
            progress_callback(95, "Saving consolidated PDF...")

        doc.save(str(out_p), garbage=3, deflate=True)
        doc.close()

        if progress_callback:
            progress_callback(100, f"Saved PDF with {total} pages!")

        return str(out_p)

    @staticmethod
    def docx_to_pdf(
        docx_path: str | Path,
        output_pdf_path: str | Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """
        Convert DOCX to PDF by converting DOCX to rich HTML and printing via Qt's QPrinter/QTextDocument.
        Requires no external Office dependencies.
        """
        src_p = Path(docx_path)
        out_p = Path(output_pdf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(20, "Extracting DOCX structure and styles...")

        html_content = DocxEngine.docx_to_html(src_p)

        if progress_callback:
            progress_callback(50, "Rendering document layout...")

        doc = QTextDocument()
        doc.setHtml(html_content)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(out_p))

        if progress_callback:
            progress_callback(80, "Writing vector PDF output...")

        doc.print_(printer)

        if progress_callback:
            progress_callback(100, "DOCX converted to PDF successfully!")

        return str(out_p)

    @staticmethod
    def pdf_to_text(
        pdf_path: str | Path,
        output_txt_path: Optional[str | Path] = None
    ) -> str:
        """Extract clean text from a PDF file."""
        src_p = Path(pdf_path)
        doc = fitz.open(str(src_p))
        text_parts = []
        for p in doc:
            text_parts.append(p.get_text("text"))
        doc.close()

        full_text = "\n\n--- Page Break ---\n\n".join(text_parts)

        if output_txt_path:
            out_p = Path(output_txt_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(full_text)
            return str(out_p)

        return full_text

    @staticmethod
    def convert_image_format(
        input_image_path: str | Path,
        output_format: str,
        output_dir: Optional[str | Path] = None
    ) -> str:
        """Convert an image from one format to another (PNG, JPG, WEBP, BMP, etc.)."""
        src_p = Path(input_image_path)
        dest_ext = output_format.lower()
        if dest_ext == "jpeg":
            dest_ext = "jpg"

        out_d = Path(output_dir) if output_dir else src_p.parent
        out_d.mkdir(parents=True, exist_ok=True)
        out_p = out_d / f"{src_p.stem}.{dest_ext}"

        with Image.open(src_p) as img:
            fmt = dest_ext.upper()
            if fmt == "JPG":
                fmt = "JPEG"

            if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = bg

            img.save(str(out_p), format=fmt)

        return str(out_p)
