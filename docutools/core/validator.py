"""
File validation and format utilities for DocuTools.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_DOCX_EXTENSIONS = {".docx", ".doc"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif"}


def format_file_size(size_bytes: int | float) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def validate_file(file_path: str | Path, expected_type: str | None = None) -> Tuple[bool, str]:
    """
    Validate that a file exists, is non-empty, and has an expected extension/type.
    expected_type can be 'pdf', 'docx', 'image', or None (any supported).
    """
    p = Path(file_path)
    if not p.exists():
        return False, f"File does not exist: {p.name}"
    if not p.is_file():
        return False, f"Path is not a regular file: {p.name}"
    if p.stat().st_size == 0:
        return False, f"File is empty (0 bytes): {p.name}"

    suffix = p.suffix.lower()
    if expected_type == "pdf":
        if suffix not in SUPPORTED_PDF_EXTENSIONS:
            return False, f"Expected a PDF file, got {suffix}"
    elif expected_type == "docx":
        if suffix not in SUPPORTED_DOCX_EXTENSIONS:
            return False, f"Expected a Word document (.docx), got {suffix}"
    elif expected_type == "image":
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            return False, f"Expected an image file, got {suffix}"
    else:
        all_supported = SUPPORTED_PDF_EXTENSIONS | SUPPORTED_DOCX_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS
        if suffix not in all_supported:
            return False, f"Unsupported file type: {suffix}"

    return True, "File is valid"


def get_file_type(file_path: str | Path) -> str:
    """Classify file type by extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix in SUPPORTED_PDF_EXTENSIONS:
        return "pdf"
    if suffix in SUPPORTED_DOCX_EXTENSIONS:
        return "docx"
    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    return "other"
