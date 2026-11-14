"""Safe file management, atomic writes, and disk space validation."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.core.exceptions import DiskSpaceError, DocuToolsError
from app.core.logging import get_logger

logger = get_logger("file_manager")


class FileManager:
    """Safe, atomic file system operations for DocuTools."""

    @staticmethod
    def check_disk_space(destination_path: Path | str, required_bytes: int = 10 * 1024 * 1024) -> None:
        """Verify destination drive has sufficient free space.

        Raises DiskSpaceError if available space is below required_bytes.
        """
        dest = Path(destination_path).resolve()
        target_dir = dest if dest.is_dir() else dest.parent

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        usage = shutil.disk_usage(target_dir)
        if usage.free < required_bytes:
            mb_free = usage.free / (1024 * 1024)
            mb_req = required_bytes / (1024 * 1024)
            raise DiskSpaceError(
                f"Insufficient disk space on {target_dir.anchor}. "
                f"Required: {mb_req:.1f} MB, Available: {mb_free:.1f} MB"
            )

    @staticmethod
    @contextmanager
    def safe_temp_file(
        suffix: str = ".tmp",
        prefix: str = "docutools_",
        dir: Path | str | None = None,
    ) -> Generator[Path, None, None]:
        """Create a temporary file that is automatically deleted when the context exits.

        Yields a Path object pointing to the closed temp file.
        """
        temp_dir = str(dir) if dir else None
        fd, temp_path_str = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
        os.close(fd)
        temp_path = Path(temp_path_str)

        try:
            yield temp_path
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as exc:
                    logger.warning("Could not delete temporary file %s: %s", temp_path, exc)

    @classmethod
    def atomic_replace(cls, source_temp_file: Path | str, target_destination: Path | str) -> Path:
        """Safely replace or create target_destination from source_temp_file.

        Uses atomic os.replace on Windows/NTFS to prevent partial file corruption.
        """
        src = Path(source_temp_file)
        dest = Path(target_destination).resolve()

        if not src.exists():
            raise DocuToolsError(f"Temporary source file does not exist: {src}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        cls.check_disk_space(dest.parent, src.stat().st_size)

        try:
            # os.replace is atomic on modern Windows filesystems
            os.replace(src, dest)
            logger.debug("Atomic file replacement successful: %s -> %s", src, dest)
            return dest
        except Exception as exc:
            logger.error("Atomic replace failed from %s to %s: %s", src, dest, exc)
            raise DocuToolsError(f"Failed to write destination file {dest.name}: {exc}") from exc

    @staticmethod
    def get_unique_filename(destination_dir: Path | str, base_name: str, extension: str) -> Path:
        """Generate a non-colliding file path in destination_dir if a file already exists."""
        target_dir = Path(destination_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        ext = extension if extension.startswith(".") else f".{extension}"
        candidate = target_dir / f"{base_name}{ext}"

        counter = 1
        while candidate.exists():
            candidate = target_dir / f"{base_name}_{counter}{ext}"
            counter += 1

        return candidate

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Convert byte count to human-readable string (KB, MB, GB)."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
