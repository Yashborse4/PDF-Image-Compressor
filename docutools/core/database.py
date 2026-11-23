"""
SQLite persistence for DocuTools: Recent files, operation history, and settings.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


from contextlib import contextmanager


class Database:
    """Manages local SQLite database storage for DocuTools."""

    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            # Prefer centralized application data location (%LOCALAPPDATA%\DocuTools\docutools.db)
            try:
                from config import DATABASE_PATH
                self.db_path = Path(DATABASE_PATH)
            except Exception:
                app_dir = Path.home() / ".docutools"
                app_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = app_dir / "docutools.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Settings table (key, value)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Recent files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recent_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    last_opened REAL NOT NULL
                )
            """)

            # Operations history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    action TEXT NOT NULL,
                    input_summary TEXT,
                    output_file TEXT,
                    initial_size INTEGER,
                    final_size INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # Default settings
            defaults = {
                "theme": "dark",
                "default_output_dir": str(Path.home() / "Documents" / "DocuTools"),
                "image_target_size_kb": "100",
                "pdf_compression_level": "medium",
            }
            for k, v in defaults.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, v)
                )
            conn.commit()

    # --- Settings Management ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default

    def set_setting(self, key: str, value: Any) -> None:
        if isinstance(value, (dict, list, bool)):
            val_str = json.dumps(value)
        else:
            val_str = str(value)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, val_str)
            )
            conn.commit()

    # --- Recent Files ---
    def add_recent_file(self, file_path: str | Path, file_type: str = "pdf") -> None:
        p = Path(file_path)
        if not p.exists():
            return
        size = p.stat().st_size
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recent_files (file_path, file_name, file_type, file_size, last_opened)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_size = excluded.file_size,
                    last_opened = excluded.last_opened
            """, (str(p.resolve()), p.name, file_type, size, now))
            # Keep max 50 recent files
            cursor.execute("""
                DELETE FROM recent_files WHERE id NOT IN (
                    SELECT id FROM recent_files ORDER BY last_opened DESC LIMIT 50
                )
            """)
            conn.commit()

    def get_recent_files(self, limit: int = 15, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if file_type:
                cursor.execute(
                    "SELECT * FROM recent_files WHERE file_type = ? ORDER BY last_opened DESC LIMIT ?",
                    (file_type, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM recent_files ORDER BY last_opened DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def remove_recent_file(self, file_path: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recent_files WHERE file_path = ?", (file_path,))
            conn.commit()

    def clear_recent_files(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recent_files")
            conn.commit()

    # --- History Logging ---
    def log_operation(
        self,
        module: str,
        action: str,
        input_summary: str = "",
        output_file: Optional[str] = None,
        initial_size: Optional[int] = None,
        final_size: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> int:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (
                    module, action, input_summary, output_file,
                    initial_size, final_size, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                module, action, input_summary, output_file,
                initial_size, final_size, status, error_message, now
            ))
            conn.commit()
            return cursor.lastrowid

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_history(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()
