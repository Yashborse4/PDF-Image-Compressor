"""File, format, and input validation routines."""

from __future__ import annotations

from pathlib import Path

from app.core.exceptions import CorruptedFileError, UnsupportedFormatError, ValidationError
from app.core.logging import get_logger

logger = get_logger("validators")

# Magic signatures
PDF_MAGIC = b"%PDF-"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
GIF_MAGIC = (b"GIF87a", b"GIF89a")
DOCX_ZIP_MAGIC = b"PK\x03\x04"


class FileValidator:
    """Validator for file integrity and format compatibility."""

    @staticmethod
    def validate_file_exists(file_path: Path | str) -> Path:
        """Verify that the path exists and is a regular file."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise ValidationError(f"File does not exist: {path}")
        if not path.is_file():
            raise ValidationError(f"Path is not a regular file: {path}")
        if path.stat().st_size == 0:
            raise CorruptedFileError(f"File is empty (0 bytes): {path.name}")
        return path

    @classmethod
    def validate_pdf(cls, file_path: Path | str) -> Path:
        """Verify that the file is a valid readable PDF by checking magic header."""
        path = cls.validate_file_exists(file_path)

        with open(path, "rb") as f:
            header = f.read(1024)

        if PDF_MAGIC not in header:
            raise UnsupportedFormatError(
                f"File '{path.name}' does not appear to be a valid PDF document (missing %PDF- header)."
            )

        return path

    @classmethod
    def validate_image(cls, file_path: Path | str) -> Path:
        """Verify that the file is a supported image and can be opened."""
        path = cls.validate_file_exists(file_path)

        from PIL import Image

        try:
            with Image.open(path) as img:
                img.verify()
        except Exception as exc:
            raise CorruptedFileError(f"Image '{path.name}' is damaged or unreadable: {exc}") from exc

        return path

    @classmethod
    def validate_docx(cls, file_path: Path | str) -> Path:
        """Verify that the file is a valid Word .docx document (ZIP archive)."""
        path = cls.validate_file_exists(file_path)

        with open(path, "rb") as f:
            header = f.read(4)

        if header != DOCX_ZIP_MAGIC:
            raise UnsupportedFormatError(f"File '{path.name}' is not a valid modern Word DOCX document.")

        return path

    @staticmethod
    def parse_page_range(range_string: str, total_pages: int) -> list[int]:
        """Parse human page string (e.g. '1, 3-5, 8') into 0-indexed page integer list.

        1-based inputs become 0-based indices.
        Validates boundaries against total_pages.
        """
        if not range_string.strip():
            raise ValidationError("Page range specification cannot be empty.")

        selected_pages: set[int] = set()
        parts = [p.strip() for p in range_string.split(",") if p.strip()]

        for part in parts:
            if "-" in part:
                tokens = part.split("-")
                if len(tokens) != 2:
                    raise ValidationError(f"Invalid page range token: '{part}'")
                try:
                    start = int(tokens[0].strip())
                    end = int(tokens[1].strip())
                except ValueError:
                    raise ValidationError(f"Invalid non-numeric page range: '{part}'")

                if start > end:
                    raise ValidationError(f"Page range start ({start}) cannot exceed end ({end}).")
                if start < 1:
                    raise ValidationError(f"Page numbers must be 1 or greater, got {start}.")
                if end > total_pages:
                    raise ValidationError(f"Page {end} exceeds total pages ({total_pages}).")

                for p in range(start, end + 1):
                    selected_pages.add(p - 1)
            else:
                try:
                    page_num = int(part)
                except ValueError:
                    raise ValidationError(f"Invalid non-numeric page number: '{part}'")

                if page_num < 1:
                    raise ValidationError(f"Page numbers must be 1 or greater, got {page_num}.")
                if page_num > total_pages:
                    raise ValidationError(f"Page {page_num} exceeds total pages ({total_pages}).")

                selected_pages.add(page_num - 1)

        result = sorted(selected_pages)
        if not result:
            raise ValidationError("No valid pages selected.")
        return result
