"""SQLite database connection and schema management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DATABASE_PATH
from app.core.logging import get_logger

logger = get_logger("database")


class Database:
    """Manages SQLite connection lifecycle and schema setup."""

    _instance: Database | None = None

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def get_instance(cls) -> Database:
        """Singleton accessor for the local application database."""
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a new SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema tables and indices if not already present."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Processing history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    operation_type TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    output_file TEXT,
                    original_size INTEGER DEFAULT 0,
                    output_size INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    status TEXT NOT NULL,  -- 'completed', 'failed', 'cancelled'
                    details TEXT
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON processing_history(timestamp DESC);"
            )

            # Recent files table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recent_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,  -- 'pdf', 'docx', 'image', 'other'
                    file_size INTEGER DEFAULT 0,
                    last_opened DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recent_last_opened ON recent_files(last_opened DESC);"
            )

            # Saved presets table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    preset_name TEXT NOT NULL,
                    preset_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(module_name, preset_name)
                );
                """
            )

            conn.commit()
            logger.debug("Database schema initialized at %s", self.db_path)
