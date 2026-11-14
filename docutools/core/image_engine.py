"""
Headless Image Processing Engine for DocuTools.
Provides Resize, Crop, Format Conversion, and Target-Size / Quality Compression.
Built using Pillow (PIL) for maximum speed and format compatibility.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageOps


class ImageEngine:
    """Core headless engine for image transformations, optimization, and batch workflows."""

    RESAMPLE_FILTERS = {
        "Lanczos (Best Quality)": Image.Resampling.LANCZOS,
        "Bicubic (Smooth)": Image.Resampling.BICUBIC,
        "Bilinear (Balanced)": Image.Resampling.BILINEAR,
        "Nearest (Fastest / Pixelated)": Image.Resampling.NEAREST,
    }

    @staticmethod
    def get_image_info(file_path: str | Path) -> Dict[str, Any]:
        """Inspect image file and return dimensions, format, color mode, and byte size."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Image not found: {p}")

        size_bytes = p.stat().st_size
        with Image.open(p) as img:
            width, height = img.size
            img_format = (img.format or p.suffix.lstrip(".").upper())
            mode = img.mode

        return {
            "file_path": str(p),
            "file_name": p.name,
            "file_size": size_bytes,
            "width": width,
            "height": height,
            "aspect_ratio": width / max(height, 1),
            "format": img_format,
            "mode": mode,
        }

    @staticmethod
    def resize_image(
        image: Image.Image,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        maintain_aspect_ratio: bool = True,
        filter_name: str = "Lanczos (Best Quality)"
    ) -> Image.Image:
        """Resize a PIL Image with aspect ratio locking and high-quality resampling."""
        orig_w, orig_h = image.size
        resample = ImageEngine.RESAMPLE_FILTERS.get(filter_name, Image.Resampling.LANCZOS)

        if target_width is None and target_height is None:
            return image.copy()

        if maintain_aspect_ratio:
            if target_width is not None and target_height is not None:
                # Fit inside bounding box while preserving ratio
                ratio = min(target_width / orig_w, target_height / orig_h)
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
            elif target_width is not None:
                new_w = max(1, target_width)
                new_h = max(1, int(orig_h * (new_w / orig_w)))
            else:
                new_h = max(1, target_height)  # type: ignore
                new_w = max(1, int(orig_w * (new_h / orig_h)))
        else:
            new_w = max(1, target_width or orig_w)
            new_h = max(1, target_height or orig_h)

        return image.resize((new_w, new_h), resample=resample)

    @staticmethod
    def crop_image(
        image: Image.Image,
        crop_box: Tuple[int, int, int, int]  # (left, top, right, bottom)
    ) -> Image.Image:
        """Crop image to specific bounding box (left, top, right, bottom)."""
        left, top, right, bottom = crop_box
        w, h = image.size
        left = max(0, min(left, w - 1))
        top = max(0, min(top, h - 1))
        right = max(left + 1, min(right, w))
        bottom = max(top + 1, min(bottom, h))
        return image.crop((left, top, right, bottom))

    @staticmethod
    def compress_to_target_size(
        image: Image.Image,
        target_kb: int,
        output_format: str = "JPEG",
        tolerance_pct: float = 0.05
    ) -> Tuple[bytes, int]:
        """
        Compress image to reach a target file size in KB using binary search.
        For JPEG / WebP: iterative quality adjustment (plus dimensional downscale if needed).
        For PNG: progressive color quantization and compression level.
        Returns (compressed_bytes, actual_size_bytes).
        """
        target_bytes = target_kb * 1024
        fmt = output_format.upper()
        if fmt in ("JPG", "JPEG"):
            fmt = "JPEG"
        elif fmt == "WEBP":
            fmt = "WEBP"
        elif fmt == "PNG":
            fmt = "PNG"

        img = image.copy()
        if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            # JPEGs don't support alpha
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background

        # --- JPEG / WEBP Binary Search Optimization ---
        if fmt in ("JPEG", "WEBP"):
            low_q = 5
            high_q = 95
            best_buf: Optional[bytes] = None
            best_diff = float("inf")

            for _ in range(9):  # Binary search 9 iterations gives < 1 quality step precision
                mid_q = (low_q + high_q) // 2
                buf = io.BytesIO()
                save_kwargs: Dict[str, Any] = {"format": fmt, "quality": mid_q, "optimize": True}
                img.save(buf, **save_kwargs)
                curr_size = buf.tell()

                diff = abs(curr_size - target_bytes)
                if diff < best_diff or (curr_size <= target_bytes and (best_buf is None or len(best_buf) < curr_size)):
                    best_diff = diff
                    best_buf = buf.getvalue()

                # Within tolerance?
                if abs(curr_size - target_bytes) / target_bytes <= tolerance_pct:
                    return buf.getvalue(), curr_size

                if curr_size > target_bytes:
                    high_q = mid_q - 1
                else:
                    low_q = mid_q + 1

                if low_q > high_q:
                    break

            # If even at low quality the image is still too big, downscale dimensionally
            if best_buf and len(best_buf) > target_bytes:
                scale = 0.85
                curr_img = img
                while scale >= 0.2:
                    new_w = max(10, int(curr_img.width * scale))
                    new_h = max(10, int(curr_img.height * scale))
                    curr_img = curr_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    curr_img.save(buf, format=fmt, quality=35, optimize=True)
                    if buf.tell() <= target_bytes * 1.05:
                        return buf.getvalue(), buf.tell()
                    scale *= 0.8

            if best_buf is not None:
                return best_buf, len(best_buf)

        # --- PNG Quantization & Compression ---
        elif fmt == "PNG":
            # Test direct save first
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True, compress_level=9)
            if buf.tell() <= target_bytes:
                return buf.getvalue(), buf.tell()

            # Quantize colors progressively (256, 128, 64, 32)
            for colors in [256, 128, 64, 32]:
                q_img = img.convert("RGBA").quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
                buf = io.BytesIO()
                q_img.save(buf, format="PNG", optimize=True, compress_level=9)
                if buf.tell() <= target_bytes:
                    return buf.getvalue(), buf.tell()

            # If still over target, scale down
            scale = 0.8
            while scale >= 0.2:
                new_w = max(10, int(img.width * scale))
                new_h = max(10, int(img.height * scale))
                scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS).quantize(colors=128)
                buf = io.BytesIO()
                scaled.save(buf, format="PNG", optimize=True, compress_level=9)
                if buf.tell() <= target_bytes * 1.05:
                    return buf.getvalue(), buf.tell()
                scale *= 0.8

            return buf.getvalue(), buf.tell()

        # Fallback default save
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue(), buf.tell()

    @staticmethod
    def process_single_image(
        input_path: str | Path,
        output_path: str | Path,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        maintain_aspect_ratio: bool = True,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
        output_format: Optional[str] = None,
        quality: Optional[int] = None,
        target_kb: Optional[int] = None,
        filter_name: str = "Lanczos (Best Quality)"
    ) -> Dict[str, Any]:
        """
        Execute full image transformation pipeline on a file:
        Crop -> Resize -> Format conversion -> Compress (Quality or Target Size) -> Save.
        Returns metadata and compression statistics.
        """
        in_p = Path(input_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        initial_size = in_p.stat().st_size

        with Image.open(in_p) as raw_img:
            # Auto-orient based on EXIF tag
            img = ImageOps.exif_transpose(raw_img) or raw_img.copy()

            # 1. Crop if specified
            if crop_box:
                img = ImageEngine.crop_image(img, crop_box)

            # 2. Resize if specified
            if target_width or target_height:
                img = ImageEngine.resize_image(
                    img,
                    target_width=target_width,
                    target_height=target_height,
                    maintain_aspect_ratio=maintain_aspect_ratio,
                    filter_name=filter_name
                )

            # Determine format
            dest_fmt = (output_format or out_p.suffix.lstrip(".")).upper()
            if dest_fmt in ("JPG", "JPEG"):
                dest_fmt = "JPEG"
            elif dest_fmt not in ("PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO"):
                dest_fmt = "JPEG"

            # 3. Compression: Target KB vs Quality
            if target_kb and target_kb > 0:
                data_bytes, final_size = ImageEngine.compress_to_target_size(
                    img, target_kb=target_kb, output_format=dest_fmt
                )
                with open(out_p, "wb") as f_out:
                    f_out.write(data_bytes)
            else:
                # Quality slider or standard save
                if dest_fmt == "JPEG":
                    if img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                        img = bg
                    q = quality if quality is not None else 85
                    img.save(out_p, format="JPEG", quality=q, optimize=True)
                elif dest_fmt == "WEBP":
                    q = quality if quality is not None else 85
                    img.save(out_p, format="WEBP", quality=q, method=6)
                elif dest_fmt == "PNG":
                    img.save(out_p, format="PNG", optimize=True, compress_level=9)
                else:
                    img.save(out_p, format=dest_fmt)

                final_size = out_p.stat().st_size

        savings_bytes = max(0, initial_size - final_size)
        savings_pct = (savings_bytes / initial_size * 100.0) if initial_size > 0 else 0.0

        return {
            "input_file": str(in_p),
            "output_file": str(out_p),
            "initial_size": initial_size,
            "final_size": final_size,
            "savings_bytes": savings_bytes,
            "savings_percent": savings_pct,
            "width": img.width,
            "height": img.height,
            "format": dest_fmt,
        }

    @staticmethod
    def process_batch(
        file_paths: List[str | Path],
        output_directory: str | Path,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        maintain_aspect_ratio: bool = True,
        output_format: Optional[str] = None,
        quality: Optional[int] = None,
        target_kb: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """Batch process multiple images with progress callbacks."""
        out_dir = Path(output_directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        results: List[Dict[str, Any]] = []

        total = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            p = Path(file_path)
            ext = f".{output_format.lower()}" if output_format else p.suffix
            out_file = out_dir / f"{p.stem}_optimized{ext}"

            try:
                res = ImageEngine.process_single_image(
                    input_path=p,
                    output_path=out_file,
                    target_width=target_width,
                    target_height=target_height,
                    maintain_aspect_ratio=maintain_aspect_ratio,
                    output_format=output_format,
                    quality=quality,
                    target_kb=target_kb
                )
                results.append(res)
                if progress_callback:
                    pct = int(((idx + 1) / total) * 100)
                    progress_callback(pct, f"Processed {idx+1}/{total}: {p.name}", res)
            except Exception as e:
                err_res = {
                    "input_file": str(p),
                    "output_file": None,
                    "error": str(e),
                    "status": "error"
                }
                results.append(err_res)
                if progress_callback:
                    pct = int(((idx + 1) / total) * 100)
                    progress_callback(pct, f"Error processing {p.name}: {e}", err_res)

        return results
