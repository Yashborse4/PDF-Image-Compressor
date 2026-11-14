"""Processing history and recent files data access object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import MAX_RECENT_FILES, SUPPORTED_DOC_EXTENSIONS, SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_PDF_EXTENSIONS
from app.database.database import Database
from app.core.logging import get_logger

logger = get_logger("history")


@dataclass
class HistoryEntry:
    """Record of a document or image processing task."""

    id: int
    timestamp: str
    operation_type: str
    source_file: str
    output_file: str | None
    original_size: int
    output_size: int
    duration_ms: int
    status: str
    details: str | None

    @property
    def space_saved_bytes(self) -> int:
        """Calculate bytes saved (positive if smaller)."""
        if self.original_size > 0 and self.output_size > 0:
            return max(0, self.original_size - self.output_size)
        return 0

    @property
    def compression_ratio_percent(self) -> float:
        """Percentage reduction."""
        if self.original_size > 0 and self.output_size > 0:
            return round((1 - (self.output_size / self.original_size)) * 100, 1)
        return 0.0


@dataclass
class RecentFileEntry:
    """Recently opened file."""

    id: int
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    last_opened: str


class HistoryManager:
    """Interface to query and write processing history and recent files."""

    def __init__(self, database: Database | None = None) -> None:
        self.db = database or Database.get_instance()

    def record_task(
        self,
        operation_type: str,
        source_file: Path | str,
        output_file: Path | str | None,
        original_size: int = 0,
        output_size: int = 0,
        duration_ms: int = 0,
        status: str = "completed",
        details: str | None = None,
    ) -> int:
        """Record a completed or failed task into the audit history."""
        src_str = str(source_file)
        out_str = str(output_file) if output_file else None

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_history (
                    operation_type, source_file, output_file,
                    original_size, output_size, duration_ms, status, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    operation_type,
                    src_str,
                    out_str,
                    original_size,
                    output_size,
                    duration_ms,
                    status,
                    details,
                ),
            )
            conn.commit()
            task_id = cursor.lastrowid or 0
            logger.info("Recorded history entry %d: %s (%s)", task_id, operation_type, status)
            return task_id

    def get_recent_history(self, limit: int = 50) -> list[HistoryEntry]:
        """Fetch latest processing history entries."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, operation_type, source_file, output_file,
                       original_size, output_size, duration_ms, status, details
                FROM processing_history
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                HistoryEntry(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    operation_type=row["operation_type"],
                    source_file=row["source_file"],
                    output_file=row["output_file"],
                    original_size=row["original_size"],
                    output_size=row["output_size"],
                    duration_ms=row["duration_ms"],
                    status=row["status"],
                    details=row["details"],
                )
                for row in rows
            ]

    def clear_history(self) -> None:
        """Clear all processing history records."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM processing_history;")
            conn.commit()
            logger.info("Processing history cleared.")

    def get_statistics(self) -> dict[str, Any]:
        """Calculate summary statistics for dashboard display."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as total_tasks,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_tasks,
                       SUM(CASE WHEN original_size > output_size AND output_size > 0 
                                THEN original_size - output_size ELSE 0 END) as total_bytes_saved
                FROM processing_history;
                """
            )
            row = cursor.fetchone()
            total = row["total_tasks"] or 0
            success = row["successful_tasks"] or 0
            saved = row["total_bytes_saved"] or 0

            return {
                "total_tasks": total,
                "successful_tasks": success,
                "total_bytes_saved": saved,
            }

    # --- Recent Files ---

    def add_recent_file(self, file_path: Path | str) -> None:
        """Record or update a file in the recent files list."""
        path = Path(file_path).resolve()
        if not path.exists():
            return

        ext = path.suffix.lower()
        if ext in SUPPORTED_PDF_EXTENSIONS:
            file_type = "pdf"
        elif ext in SUPPORTED_DOC_EXTENSIONS:
            file_type = "docx"
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            file_type = "image"
        else:
            file_type = "other"

        size = path.stat().st_size

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO recent_files (file_path, file_name, file_type, file_size, last_opened)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    last_opened = CURRENT_TIMESTAMP,
                    file_size = excluded.file_size;
                """,
                (str(path), path.name, file_type, size),
            )
            # Prune to MAX_RECENT_FILES
            cursor.execute(
                """
                DELETE FROM recent_files
                WHERE id NOT IN (
                    SELECT id FROM recent_files ORDER BY last_opened DESC LIMIT ?
                );
                """,
                (MAX_RECENT_FILES,),
            )
            conn.commit()

    def get_recent_files(self, limit: int = 10) -> list[RecentFileEntry]:
        """Retrieve recent files ordered by last_opened."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, file_path, file_name, file_type, file_size, last_opened
                FROM recent_files
                ORDER BY last_opened DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                RecentFileEntry(
                    id=row["id"],
                    file_path=row["file_path"],
                    file_name=row["file_name"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    last_opened=row["last_opened"],
                )
                for row in rows
            ]

    def clear_recent_files(self) -> None:
        """Clear recent files history."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM recent_files;")
            conn.commit()
            logger.info("Recent files cleared.")
