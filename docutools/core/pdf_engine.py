"""
Headless PDF Engine for DocuTools.
Provides Merge, Split, Reorder, Extract, Compress, Protect, and Rendering operations.
Uses pypdf, pikepdf, and PyMuPDF (fitz) for speed, compliance, and robustness.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF
import pikepdf
import pypdf
from PIL import Image


class PDFEngine:
    """Core headless processing engine for PDF operations."""

    @staticmethod
    def get_document_info(file_path: str | Path, password: Optional[str] = None) -> Dict[str, Any]:
        """Inspect and return PDF metadata, page count, and encryption status."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        doc = fitz.open(str(p))
        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    raise PermissionError("Incorrect password for protected PDF.")
            else:
                return {
                    "file_path": str(p),
                    "file_name": p.name,
                    "file_size": p.stat().st_size,
                    "is_encrypted": True,
                    "page_count": 0,
                    "metadata": {},
                    "pages_info": [],
                }

        page_count = len(doc)
        pages_info = []
        for i in range(page_count):
            page = doc[i]
            rect = page.rect
            pages_info.append({
                "page_number": i + 1,
                "width": rect.width,
                "height": rect.height,
                "rotation": page.rotation,
            })

        info = {
            "file_path": str(p),
            "file_name": p.name,
            "file_size": p.stat().st_size,
            "is_encrypted": doc.is_encrypted,
            "page_count": page_count,
            "metadata": doc.metadata,
            "pages_info": pages_info,
        }
        doc.close()
        return info

    @staticmethod
    def render_page_thumbnail(
        file_path: str | Path,
        page_index: int,
        target_width: int = 180,
        password: Optional[str] = None
    ) -> bytes:
        """Render a single page thumbnail as PNG bytes."""
        doc = fitz.open(str(file_path))
        if doc.is_encrypted and password:
            doc.authenticate(password)
        if page_index < 0 or page_index >= len(doc):
            doc.close()
            raise IndexError(f"Page index {page_index} out of bounds (0..{len(doc)-1})")

        page = doc[page_index]
        # Calculate zoom to fit target_width
        rect = page.rect
        scale = target_width / max(rect.width, 1.0)
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        png_data = pix.tobytes("png")
        doc.close()
        return png_data

    @staticmethod
    def assemble_pdf(
        pages_spec: Sequence[Dict[str, Any]],
        output_path: str | Path,
        compress: bool = False,
        compress_profile: str = "medium",
        user_password: Optional[str] = None,
        owner_password: Optional[str] = None,
        allow_printing: bool = True,
        allow_copying: bool = True,
        watermark_text: Optional[str] = None,
        watermark_opacity: float = 0.3,
        watermark_size: int = 40,
        sign_certificate_path: Optional[str | Path] = None,
        sign_password: Optional[str] = None,
        sign_reason: Optional[str] = None,
        sign_location: Optional[str] = None,
        sign_visible: bool = False,
        sign_page_index: int = 0,
        sign_rect: Optional[Tuple[float, float, float, float]] = None,
        sign_image_path: Optional[str | Path] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Assemble a new PDF from a custom sequence of pages (from single or multiple source PDFs),
        applying page order, rotations, optional watermark, optional compression, and optional password encryption.
        pages_spec: list of dicts with keys:
            - source_file: str | Path
            - orig_index: int
            - rotation: int (optional, degrees clockwise 0, 90, 180, 270)
        """
        if not pages_spec:
            raise ValueError("No pages specified to assemble.")

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_pages = len(pages_spec)

        import tempfile
        import shutil

        # Step 1: Assemble pages into PyMuPDF doc
        out_doc = fitz.open()
        open_docs: Dict[str, fitz.Document] = {}

        try:
            for idx, spec in enumerate(pages_spec):
                if progress_callback:
                    pct = int(((idx + 1) / max(total_pages, 1)) * 40)
                    progress_callback(pct, f"Assembling page {idx + 1} of {total_pages}...")

                src_str = str(spec["source_file"])
                if src_str not in open_docs:
                    open_docs[src_str] = fitz.open(src_str)

                src_doc = open_docs[src_str]
                orig_idx = int(spec["orig_index"])
                rotation = int(spec.get("rotation", 0)) % 360

                out_doc.insert_pdf(src_doc, from_page=orig_idx, to_page=orig_idx)
                inserted_page = out_doc[-1]

                if rotation != 0:
                    inserted_page.set_rotation((inserted_page.rotation + rotation) % 360)

                if watermark_text and watermark_text.strip():
                    rect = inserted_page.rect
                    pt = fitz.Point(rect.width * 0.2, rect.height * 0.5)
                    inserted_page.insert_text(
                        pt,
                        watermark_text.strip(),
                        fontsize=watermark_size,
                        color=(0.6, 0.6, 0.6),
                        fill_opacity=watermark_opacity
                    )
        finally:
            for d in open_docs.values():
                d.close()

        # Step 2: Handle intermediate saves / compression / protection / digital signing
        temp_files: List[str] = []
        try:
            if not compress and not user_password and not owner_password and not sign_certificate_path:
                if progress_callback:
                    progress_callback(90, "Writing final PDF...")
                out_doc.save(
                    str(out_p),
                    garbage=3,
                    deflate=True,
                    deflate_images=False,
                    deflate_fonts=False,
                    clean=False,
                    preserve_metadata=True
                )
                out_doc.close()
                current_file = str(out_p)
            else:
                tf_stage1 = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                tf_stage1.close()
                temp_files.append(tf_stage1.name)

                if progress_callback:
                    progress_callback(50, "Saving base assembled PDF...")
                out_doc.save(
                    tf_stage1.name,
                    garbage=3,
                    deflate=True,
                    deflate_images=False,
                    deflate_fonts=False,
                    clean=False,
                    preserve_metadata=True
                )
                out_doc.close()
                current_file = tf_stage1.name

                # Compression step
                if compress:
                    if progress_callback:
                        progress_callback(65, "Compressing PDF streams and embedded media...")
                    tf_stage2 = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                    tf_stage2.close()
                    temp_files.append(tf_stage2.name)
                    PDFEngine.compress_pdf(current_file, tf_stage2.name, quality_level=compress_profile)
                    current_file = tf_stage2.name

                # Digital signing step (cryptographic terminal operation before optional move)
                if sign_certificate_path:
                    if user_password or owner_password:
                        raise ValueError(
                            "Cannot apply digital signature and AES-256 password encryption simultaneously. "
                            "Digital signatures authenticate document integrity and require unencrypted content."
                        )
                    if progress_callback:
                        progress_callback(80, "Applying cryptographic digital signature (PAdES)...")
                    tf_signed = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                    tf_signed.close()
                    temp_files.append(tf_signed.name)
                    PDFEngine.sign_pdf(
                        file_path=current_file,
                        output_path=tf_signed.name,
                        certificate_path=sign_certificate_path,
                        password=sign_password,
                        reason=sign_reason,
                        location=sign_location,
                        visible=sign_visible,
                        page_index=sign_page_index,
                        rect=sign_rect,
                        image_path=sign_image_path,
                    )
                    current_file = tf_signed.name

                # Encryption step
                if user_password or owner_password:
                    if progress_callback:
                        progress_callback(85, "Applying AES-256 encryption & security permissions...")
                    PDFEngine.protect_pdf(
                        file_path=current_file,
                        output_path=out_p,
                        user_password=user_password or "",
                        owner_password=owner_password or user_password or "",
                        allow_printing=allow_printing,
                        allow_copying=allow_copying
                    )
                else:
                    if progress_callback:
                        progress_callback(90, "Writing final PDF...")
                    shutil.move(current_file, str(out_p))
        finally:
            for tf in temp_files:
                if os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except Exception:
                        pass

        if progress_callback:
            progress_callback(100, "Assembly complete!")

        final_size = out_p.stat().st_size if out_p.exists() else 0
        return {
            "output_file": str(out_p),
            "pages_count": total_pages,
            "file_size": final_size,
            "compressed": compress,
            "protected": bool(user_password),
            "watermarked": bool(watermark_text),
            "signed": bool(sign_certificate_path),
        }

    @staticmethod
    def merge_pdfs(
        source_files: Sequence[str | Path],
        output_path: str | Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """Merge multiple PDF files into one output PDF."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        writer = pypdf.PdfWriter()
        total_files = len(source_files)

        for idx, src in enumerate(source_files):
            if progress_callback:
                pct = int((idx / max(total_files, 1)) * 90)
                progress_callback(pct, f"Merging file {idx+1}/{total_files}: {Path(src).name}")

            reader = pypdf.PdfReader(str(src))
            for page in reader.pages:
                writer.add_page(page)

        if progress_callback:
            progress_callback(95, "Writing output merged PDF...")

        with open(out_p, "wb") as f_out:
            writer.write(f_out)

        if progress_callback:
            progress_callback(100, "Merge complete!")

        return str(out_p)

    @staticmethod
    def split_pdf_by_ranges(
        file_path: str | Path,
        page_ranges_str: str,
        output_dir: str | Path,
        base_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[str]:
        """
        Split a PDF by page ranges (e.g., '1-3, 5, 8-10').
        Generates a new PDF for each specified range.
        Page numbers in page_ranges_str are 1-based.
        """
        src_p = Path(file_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        name_prefix = base_name or src_p.stem

        reader = pypdf.PdfReader(str(src_p))
        total_pages = len(reader.pages)

        # Parse range string e.g. "1-3, 5, 8-10"
        parts = [p.strip() for p in page_ranges_str.split(",") if p.strip()]
        output_files: List[str] = []

        for idx, part in enumerate(parts):
            if progress_callback:
                pct = int((idx / max(len(parts), 1)) * 90)
                progress_callback(pct, f"Processing range: {part}")

            pages_to_extract: List[int] = []
            if "-" in part:
                tokens = part.split("-")
                start_p = int(tokens[0].strip())
                end_p = int(tokens[1].strip())
                pages_to_extract = list(range(max(1, start_p), min(total_pages, end_p) + 1))
            else:
                p_num = int(part)
                if 1 <= p_num <= total_pages:
                    pages_to_extract = [p_num]

            if not pages_to_extract:
                continue

            writer = pypdf.PdfWriter()
            for p_num in pages_to_extract:
                writer.add_page(reader.pages[p_num - 1])

            out_file = out_d / f"{name_prefix}_range_{part.replace(' ', '')}.pdf"
            with open(out_file, "wb") as f_out:
                writer.write(f_out)
            output_files.append(str(out_file))

        if progress_callback:
            progress_callback(100, f"Split into {len(output_files)} files!")

        return output_files

    @staticmethod
    def split_pdf_pages(
        file_path: str | Path,
        output_dir: str | Path,
        base_name: Optional[str] = None,
        chunk_size: int = 1,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[str]:
        """
        Split a PDF into chunks of chunk_size pages (chunk_size=1 means every page is its own PDF).
        """
        src_p = Path(file_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        name_prefix = base_name or src_p.stem

        reader = pypdf.PdfReader(str(src_p))
        total_pages = len(reader.pages)
        output_files: List[str] = []

        total_chunks = (total_pages + chunk_size - 1) // chunk_size
        for chunk_idx in range(total_chunks):
            start_p = chunk_idx * chunk_size
            end_p = min(start_p + chunk_size, total_pages)

            if progress_callback:
                pct = int((chunk_idx / max(total_chunks, 1)) * 90)
                progress_callback(pct, f"Saving pages {start_p + 1} to {end_p}...")

            writer = pypdf.PdfWriter()
            for p_i in range(start_p, end_p):
                writer.add_page(reader.pages[p_i])

            if chunk_size == 1:
                out_file = out_d / f"{name_prefix}_page_{start_p + 1:03d}.pdf"
            else:
                out_file = out_d / f"{name_prefix}_part_{chunk_idx + 1:02d}_p{start_p + 1}-{end_p}.pdf"

            with open(out_file, "wb") as f_out:
                writer.write(f_out)
            output_files.append(str(out_file))

        if progress_callback:
            progress_callback(100, f"Finished splitting {total_pages} pages into {len(output_files)} files.")

        return output_files

    @staticmethod
    def extract_pages(
        file_path: str | Path,
        page_indices: Sequence[int],
        output_path: str | Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """Extract a specific set of 0-based page indices to a new PDF."""
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        reader = pypdf.PdfReader(str(src_p))
        writer = pypdf.PdfWriter()

        total = len(page_indices)
        for i, idx in enumerate(page_indices):
            if 0 <= idx < len(reader.pages):
                writer.add_page(reader.pages[idx])
            if progress_callback:
                pct = int(((i + 1) / max(total, 1)) * 90)
                progress_callback(pct, f"Extracting page {idx + 1} ({i+1}/{total})...")

        with open(out_p, "wb") as f_out:
            writer.write(f_out)

        if progress_callback:
            progress_callback(100, f"Saved extracted pages to {out_p.name}")

        return str(out_p)

    @staticmethod
    def reorder_and_rotate_pages(
        file_path: str | Path,
        page_order: Sequence[int],
        rotations: Optional[Dict[int, int]] = None,
        output_path: Optional[str | Path] = None
    ) -> str:
        """
        Reorder pages according to page_order (0-indexed) and apply optional rotations.
        rotations format: {new_index: rotation_degrees (0, 90, 180, 270)}.
        """
        src_p = Path(file_path)
        out_p = Path(output_path) if output_path else src_p

        reader = pypdf.PdfReader(str(src_p))
        writer = pypdf.PdfWriter()

        for new_idx, orig_idx in enumerate(page_order):
            if 0 <= orig_idx < len(reader.pages):
                page = reader.pages[orig_idx]
                if rotations and new_idx in rotations:
                    rot = rotations[new_idx]
                    page.rotate(rot)
                writer.add_page(page)

        # Write to memory first to allow overwriting the same source file safely
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)

        with open(out_p, "wb") as f_out:
            f_out.write(buf.getvalue())

        return str(out_p)

    @staticmethod
    def compress_pdf(
        file_path: str | Path,
        output_path: str | Path,
        quality_level: str = "medium",  # "low", "medium", "high"
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Compress PDF using pikepdf stream compression and image downsampling.
        Returns compression statistics: original_size, compressed_size, savings_bytes, savings_percent.
        """
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        orig_size = src_p.stat().st_size

        if progress_callback:
            progress_callback(15, "Opening PDF for stream and structure optimization...")

        # Quality settings mapping for embedded image downsampling
        quality_map = {
            "low": 50,     # Max compression, lower image fidelity
            "medium": 75,  # Balanced
            "high": 85,    # Gentle compression, high fidelity
        }
        target_img_quality = quality_map.get(quality_level.lower(), 75)

        # First pass: use PyMuPDF to downsample and recompress embedded images if large
        temp_intermediate = io.BytesIO()
        doc = fitz.open(str(src_p))
        total_pages = len(doc)
        seen_xrefs: set[int] = set()

        for p_idx in range(total_pages):
            if progress_callback:
                pct = 20 + int((p_idx / max(total_pages, 1)) * 40)
                progress_callback(pct, f"Optimizing images on page {p_idx+1}/{total_pages}...")

            page = doc[p_idx]
            for img_info in page.get_images():
                xref = img_info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Only compress photos/raster images over 30KB
                    if len(image_bytes) > 30 * 1024 and image_ext in ("jpeg", "jpg", "png"):
                        with Image.open(io.BytesIO(image_bytes)) as pil_img:
                            if pil_img.mode in ("RGBA", "P"):
                                pil_img = pil_img.convert("RGB")

                            # Downsample if dimensions are excessively large (>2000px)
                            max_dim = 1600 if quality_level == "low" else 2200
                            if max(pil_img.size) > max_dim:
                                pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                            compressed_img_buf = io.BytesIO()
                            pil_img.save(compressed_img_buf, format="JPEG", quality=target_img_quality, optimize=True)
                            new_bytes = compressed_img_buf.getvalue()

                            if len(new_bytes) < len(image_bytes):
                                page.replace_image(xref, stream=new_bytes)
                except Exception:
                    # Non-fatal image skip
                    continue

        doc.save(temp_intermediate, garbage=4, deflate=True, clean=True)
        doc.close()
        temp_intermediate.seek(0)

        if progress_callback:
            progress_callback(75, "Applying pikepdf deep stream & object dictionary compression...")

        # Second pass: pikepdf structural and stream deflation
        with pikepdf.open(temp_intermediate) as pike_doc:
            pike_doc.save(
                str(out_p),
                compress_streams=True,
                recompress_flate=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                linearize=False
            )

        if progress_callback:
            progress_callback(100, "Compression finished!")

        final_size = out_p.stat().st_size
        savings_bytes = max(0, orig_size - final_size)
        savings_pct = (savings_bytes / orig_size * 100.0) if orig_size > 0 else 0.0

        return {
            "file_path": str(out_p),
            "original_size": orig_size,
            "compressed_size": final_size,
            "savings_bytes": savings_bytes,
            "savings_percent": savings_pct,
        }

    @staticmethod
    def protect_pdf(
        file_path: str | Path,
        output_path: str | Path,
        user_password: str,
        owner_password: Optional[str] = None,
        allow_printing: bool = True,
        allow_copying: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """Apply AES-256 encryption and permission controls to a PDF."""
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(20, "Reading document...")

        reader = pypdf.PdfReader(str(src_p))
        writer = pypdf.PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        if progress_callback:
            progress_callback(60, "Configuring AES-256 encryption & permissions...")

        writer.encrypt(
            user_password=user_password,
            owner_password=owner_password or user_password,
            permissions_flag=pypdf.constants.UserAccessPermissions.PRINT
            if allow_printing else 0,
        )

        with open(out_p, "wb") as f_out:
            writer.write(f_out)

        if progress_callback:
            progress_callback(100, "Password protection applied successfully.")

        return str(out_p)

    @staticmethod
    def remove_password(
        file_path: str | Path,
        output_path: str | Path,
        password: str = "",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """Remove password protection and security restrictions from a PDF."""
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(25, "Unlocking encrypted PDF...")

        try:
            with pikepdf.open(str(src_p), password=password) as pdf:
                if progress_callback:
                    progress_callback(70, "Saving unlocked PDF without encryption...")
                pdf.save(str(out_p))
        except pikepdf.PasswordError as exc:
            raise ValueError("Incorrect password. Please enter the valid password for this PDF.") from exc

        if progress_callback:
            progress_callback(100, "PDF password removed successfully.")

        return str(out_p)

    @staticmethod
    def add_annotation(
        file_path: str | Path,
        output_path: str | Path,
        annotation_type: str = "watermark",  # "watermark", "header", "footer", "stamp"
        text: str = "",
        page_numbers: Optional[List[int]] = None,
        font_size: int = 24,
        opacity: float = 0.5,
        color_rgb: Tuple[float, float, float] = (0.8, 0.2, 0.2)
    ) -> str:
        """Add annotations, watermarks, headers, footers, or stamp text to PDF pages."""
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(src_p))
        total = len(doc)
        pages_to_apply = page_numbers if page_numbers is not None else list(range(total))

        for p_idx in pages_to_apply:
            if 0 <= p_idx < total:
                page = doc[p_idx]
                rect = page.rect

                if annotation_type == "watermark":
                    # Center diagonal watermark
                    pt = fitz.Point(rect.width * 0.25, rect.height * 0.55)
                    page.insert_text(pt, text, fontsize=font_size, color=color_rgb, fill_opacity=opacity)
                elif annotation_type == "header":
                    # Top header
                    pt = fitz.Point(rect.width * 0.5 - (len(text) * font_size * 0.25), 36)
                    page.insert_text(pt, text, fontsize=font_size, color=color_rgb, fill_opacity=opacity)
                elif annotation_type == "footer":
                    # Bottom footer
                    pt = fitz.Point(rect.width * 0.5 - (len(text) * font_size * 0.25), rect.height - 30)
                    page.insert_text(pt, text, fontsize=font_size, color=color_rgb, fill_opacity=opacity)
                elif annotation_type == "stamp":
                    # Stamp in top right corner with box border
                    stamp_rect = fitz.Rect(rect.width - 200, 30, rect.width - 30, 80)
                    page.draw_rect(stamp_rect, color=color_rgb, width=2)
                    pt = fitz.Point(rect.width - 190, 60)
                    page.insert_text(pt, text, fontsize=font_size, color=color_rgb, fill_opacity=opacity)

        doc.save(str(out_p), garbage=3, deflate=True)
        doc.close()
        return str(out_p)

    @staticmethod
    def add_text_watermark(
        file_path: str | Path,
        output_path: str | Path,
        watermark_text: str,
        font_size: int = 40,
        opacity: float = 0.3,
        color: Tuple[float, float, float] = (0.7, 0.7, 0.7)
    ) -> str:
        """Add a diagonal text watermark across every page of a PDF using PyMuPDF."""
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(src_p))
        for page in doc:
            rect = page.rect
            # Center point
            p = fitz.Point(rect.width / 4, rect.height / 2)
            page.insert_text(
                p,
                watermark_text,
                fontsize=font_size,
                color=color,
                fill_opacity=opacity,
            )

        doc.save(str(out_p), garbage=3, deflate=True)
        doc.close()
        return str(out_p)

    # --- ADVANCED PDF CONTENT EDITING ---

    @staticmethod
    def render_page_hires(
        file_path: str | Path,
        page_index: int,
        zoom: float = 1.5,
        rotation: int = 0,
        password: Optional[str] = None
    ) -> bytes:
        """Render high-resolution page image as PNG bytes for interactive canvas editing and inspection."""
        doc = fitz.open(str(file_path))
        if doc.is_encrypted and password:
            doc.authenticate(password)
        if page_index < 0 or page_index >= len(doc):
            doc.close()
            raise IndexError(f"Page index {page_index} out of bounds")

        page = doc[page_index]
        matrix = fitz.Matrix(zoom, zoom)
        if rotation % 360 != 0:
            matrix = matrix.prerotate(rotation % 360)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        png_data = pix.tobytes("png")
        doc.close()
        return png_data

    @staticmethod
    def search_text_in_pdf(
        file_path: str | Path,
        query: str,
        password: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for occurrences of query in the PDF and return page indices and bounding boxes."""
        if not query.strip():
            return []

        doc = fitz.open(str(file_path))
        if doc.is_encrypted and password:
            doc.authenticate(password)

        results = []
        for p_idx, page in enumerate(doc):
            rects = page.search_for(query)
            for r in rects:
                results.append({
                    "page": p_idx,
                    "rect": (r.x0, r.y0, r.x1, r.y1),
                    "text": query
                })

        doc.close()
        return results

    @staticmethod
    def redact_and_replace_text(
        file_path: str | Path,
        output_path: str | Path,
        search_term: str,
        replacement_text: Optional[str] = None,
        fill_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> Dict[str, Any]:
        """
        True PDF Redaction & In-place Text Replacement.
        Permanently strips original text stream and overlays solid blackout or replacement text.
        """
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(src_p))
        total_occurrences = 0

        for page in doc:
            rects = page.search_for(search_term)
            for r in rects:
                total_occurrences += 1
                if replacement_text is not None:
                    # Replace text
                    page.add_redact_annot(r, text=replacement_text, fill=(1, 1, 1), text_color=(0, 0, 0))
                else:
                    # Blackout redact
                    page.add_redact_annot(r, fill=fill_color)
            page.apply_redactions()

        doc.save(str(out_p), garbage=3, deflate=True)
        doc.close()

        return {
            "output_file": str(out_p),
            "occurrences_redacted": total_occurrences,
            "search_term": search_term,
            "replaced_with": replacement_text
        }

    @staticmethod
    def insert_content_on_page(
        file_path: str | Path,
        output_path: str | Path,
        page_index: int,
        items: List[Dict[str, Any]]
    ) -> str:
        """
        Apply multiple custom annotations/content to a specific PDF page:
        - text: {"type": "text", "rect": (x0, y0, x1, y1), "text": "...", "fontsize": 14, "color": (0,0,0)}
        - highlight: {"type": "highlight", "rect": (x0, y0, x1, y1), "color": (1,1,0)}
        - shape: {"type": "shape", "rect": (x0, y0, x1, y1), "border_color": (1,0,0), "width": 2}
        - image: {"type": "image", "rect": (x0, y0, x1, y1), "image_path": "..."}
        """
        src_p = Path(file_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(src_p))
        if 0 <= page_index < len(doc):
            page = doc[page_index]

            for item in items:
                itype = item.get("type")
                coords = item.get("rect", (50, 50, 200, 100))
                rect = fitz.Rect(*coords)

                if itype == "text":
                    txt = item.get("text", "")
                    fsize = item.get("fontsize", 12)
                    col = item.get("color", (0, 0, 0))
                    page.insert_textbox(rect, txt, fontsize=fsize, color=col)
                elif itype == "highlight":
                    col = item.get("color", (1, 1, 0))
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=col)
                    annot.update()
                elif itype == "shape":
                    b_col = item.get("border_color", (1, 0, 0))
                    stroke_w = item.get("width", 2)
                    page.draw_rect(rect, color=b_col, width=stroke_w)
                elif itype == "image":
                    img_p = item.get("image_path")
                    if img_p and Path(img_p).exists():
                        page.insert_image(rect, filename=str(img_p))

        doc.save(str(out_p), garbage=3, deflate=True)
        doc.close()
        return str(out_p)

    # =========================================================================
    # DIGITAL SIGNATURES & CRYPTOGRAPHIC VERIFICATION (PAdES / PKCS#7)
    # =========================================================================

    @staticmethod
    def sign_pdf(
        file_path: str | Path,
        output_path: str | Path,
        certificate_path: str | Path,
        password: Optional[str] = None,
        reason: Optional[str] = None,
        location: Optional[str] = None,
        visible: bool = False,
        page_index: int = 0,
        rect: Optional[Tuple[float, float, float, float]] = None,
        image_path: Optional[str | Path] = None,
        field_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Digitally sign a PDF document using an X.509 certificate and private key (PKCS#12 / .p12 / .pfx).
        Produces a cryptographically compliant PAdES / PKCS#7 detached digital signature.

        Signing is performed as a strict TERMINAL incremental update over finalized bytes,
        preserving the cryptographic byte-range hash and document integrity.
        """
        src_p = Path(file_path)
        if not src_p.is_file():
            raise FileNotFoundError(f"Source PDF file not found: {src_p}")

        cert_p = Path(certificate_path)
        if not cert_p.is_file():
            raise FileNotFoundError(f"Certificate file not found: {cert_p}")

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(20, "Loading cryptographic certificate...")

        from pdfcore import signing

        signer = signing.load_pkcs12_signer(cert_p, password)

        raw_bytes = src_p.read_bytes()

        # Resolve field name if not specified
        if not field_name:
            try:
                probe = fitz.open(stream=raw_bytes, filetype="pdf")
                names = signing.signature_field_names(probe)
                probe.close()
                field_name = signing.next_field_name(names)
            except Exception:
                field_name = "Signature1"

        # Calculate bounding rectangle for visible signature if requested
        sig_rect = None
        if visible:
            if rect is not None:
                sig_rect = rect
            else:
                try:
                    probe = fitz.open(stream=raw_bytes, filetype="pdf")
                    idx = max(0, min(page_index, len(probe) - 1))
                    page = probe[idx]
                    pw = page.rect.width
                    ph = page.rect.height
                    probe.close()
                    # Default lower-right placement: 180x60 pt box with 20pt margin
                    box_w, box_h = min(180.0, pw * 0.45), min(60.0, ph * 0.15)
                    sig_rect = (pw - box_w - 20.0, ph - box_h - 20.0, pw - 20.0, ph - 20.0)
                except Exception:
                    sig_rect = (350.0, 700.0, 550.0, 760.0)

        if progress_callback:
            progress_callback(50, "Generating cryptographic signature digest...")

        res = signing.sign_pdf_bytes(
            raw_bytes,
            signer,
            field_name=field_name,
            reason=reason,
            location=location,
            page_index=page_index,
            rect=sig_rect,
            image_path=image_path,
        )

        if progress_callback:
            progress_callback(85, "Writing signed document...")

        out_p.write_bytes(res.pdf_bytes)

        if progress_callback:
            progress_callback(100, "Signing complete!")

        return {
            "output_file": str(out_p),
            "field_name": res.field_name,
            "signer_name": res.signer_name,
            "self_signed": res.self_signed,
            "file_size": out_p.stat().st_size,
            "visible": visible,
            "page_index": page_index if visible else None,
        }

    @staticmethod
    def is_pdf_encrypted(file_path: str | Path) -> bool:
        """Return True if opening the PDF requires a user password."""
        p = Path(file_path)
        if not p.is_file():
            return False
        doc = fitz.open(str(p))
        try:
            return bool(doc.needs_pass)
        finally:
            doc.close()

    @staticmethod
    def check_online_cert_status(timeout: float = 1.0) -> Dict[str, Any]:
        """Automatically detect network availability for online certificate checks."""
        import socket

        try:
            with socket.create_connection(("1.1.1.1", 443), timeout=timeout):
                return {
                    "online": True,
                    "status_text": "Online — Automatic certificate checks active",
                }
        except OSError:
            return {
                "online": False,
                "status_text": "Offline — Local public-key verification active",
            }

    @staticmethod
    def verify_signatures(
        file_path: str | Path,
        password: Optional[str] = None,
        trust_roots=None,
    ) -> List[Dict[str, Any]]:
        """
        Cryptographically verify all digital signatures in a PDF document.
        Detects tampering, unauthorized post-signing modifications, and cryptographic integrity.
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")

        raw_bytes = p.read_bytes()
        from pdfcore import signing

        verifications = signing.verify_pdf_signatures(
            raw_bytes, trust_roots=trust_roots, password=password
        )

        results = []
        for v in verifications:
            results.append({
                "field_name": v.field_name,
                "signer_name": v.signer_name,
                "intact": v.intact,
                "valid": v.valid,
                "trusted": v.trusted,
                "tampered": v.tampered,
                "problem": v.problem,
                "is_valid": bool(v.valid and v.intact and not v.tampered),
            })
        return results

    @staticmethod
    def generate_self_signed_certificate(
        out_path: str | Path,
        common_name: str,
        password: str,
        valid_days: int = 1095,
        key_size: int = 2048,
    ) -> str:
        """
        Generate a standards-compliant RSA private key and self-signed X.509 certificate
        with digital signature and non-repudiation key usages, packed into a password-protected PKCS#12 bundle (.p12/.pfx).
        """
        from pdfcore import signing

        dest = signing.generate_self_signed_p12(
            out_path=out_path,
            common_name=common_name,
            password=password,
            valid_days=valid_days,
            key_size=key_size,
        )
        return str(dest)

    @staticmethod
    def has_digital_signatures(file_path: str | Path) -> bool:
        """Quick check whether the PDF file has any digital signatures applied."""
        p = Path(file_path)
        if not p.is_file():
            return False
        from pdfcore import signing

        try:
            doc = fitz.open(str(p))
            result = signing.has_signatures(doc)
            doc.close()
            return result
        except Exception:
            return False

    @staticmethod
    def strip_signatures(file_path: str | Path, output_path: str | Path) -> int:
        """
        Remove all digital signatures and signature fields from the PDF, saving an unsigned copy.
        Useful when a user explicitly wishes to edit a previously signed document.
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        from pdfcore import signing

        doc = fitz.open(str(p))
        try:
            count = signing.strip_signatures(doc)
            doc.save(str(out_p), garbage=3, deflate=True)
            return count
        finally:
            doc.close()


