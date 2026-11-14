"""Automated tests for Phase 1 Core, Database, Settings, and Validators."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.core.exceptions import (
    CorruptedFileError,
    DiskSpaceError,
    DocuToolsError,
    UnsupportedFormatError,
    ValidationError,
)
from app.core.file_manager import FileManager
from app.core.settings import Settings
from app.core.validators import FileValidator
from app.database.database import Database
from app.database.history import HistoryManager


class TestFileManager:
    def test_format_file_size(self):
        assert FileManager.format_file_size(500) == "500 B"
        assert FileManager.format_file_size(2048) == "2.0 KB"
        assert FileManager.format_file_size(5 * 1024 * 1024) == "5.00 MB"
        assert FileManager.format_file_size(2 * 1024 * 1024 * 1024) == "2.00 GB"

    def test_safe_temp_file_lifecycle(self):
        temp_path = None
        with FileManager.safe_temp_file(suffix=".pdf") as t:
            temp_path = t
            assert temp_path.exists()
            assert temp_path.suffix == ".pdf"
            temp_path.write_text("sample content")

        # Must be deleted upon exiting context
        assert not temp_path.exists()

    def test_atomic_replace(self, tmp_path):
        src = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("hello world")

        res = FileManager.atomic_replace(src, dest)
        assert res == dest
        assert dest.exists()
        assert dest.read_text() == "hello world"
        assert not src.exists()

    def test_unique_filename(self, tmp_path):
        p1 = tmp_path / "report.pdf"
        p1.write_text("test")

        candidate = FileManager.get_unique_filename(tmp_path, "report", ".pdf")
        assert candidate.name == "report_1.pdf"

        p2 = tmp_path / "report_1.pdf"
        p2.write_text("test")

        candidate2 = FileManager.get_unique_filename(tmp_path, "report", ".pdf")
        assert candidate2.name == "report_2.pdf"


class TestValidators:
    def test_parse_page_range(self):
        pages = FileValidator.parse_page_range("1, 3-5, 8", total_pages=10)
        assert pages == [0, 2, 3, 4, 7]  # 0-indexed

    def test_parse_page_range_errors(self):
        with pytest.raises(ValidationError):
            FileValidator.parse_page_range("0, 2", total_pages=5)  # 0 is invalid 1-based

        with pytest.raises(ValidationError):
            FileValidator.parse_page_range("1-10", total_pages=5)  # 10 exceeds 5

        with pytest.raises(ValidationError):
            FileValidator.parse_page_range("5-2", total_pages=5)  # start > end

        with pytest.raises(ValidationError):
            FileValidator.parse_page_range("invalid", total_pages=5)

    def test_validate_file_exists(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("data")
        assert FileValidator.validate_file_exists(f) == f.resolve()

        non_existent = tmp_path / "missing.txt"
        with pytest.raises(ValidationError):
            FileValidator.validate_file_exists(non_existent)

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        with pytest.raises(CorruptedFileError):
            FileValidator.validate_file_exists(empty_file)

    def test_validate_pdf_magic(self, tmp_path):
        pdf_file = tmp_path / "valid.pdf"
        pdf_file.write_bytes(b"%PDF-1.7\n...")
        assert FileValidator.validate_pdf(pdf_file) == pdf_file.resolve()

        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_bytes(b"This is not a pdf file")
        with pytest.raises(UnsupportedFormatError):
            FileValidator.validate_pdf(fake_pdf)


class TestDatabaseAndHistory:
    def test_database_and_history_crud(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = Database(db_path=db_path)
        mgr = HistoryManager(database=db)

        # 1. Record task
        src = tmp_path / "in.pdf"
        out = tmp_path / "out.pdf"
        src.write_text("in")
        out.write_text("out")

        tid = mgr.record_task(
            operation_type="compress",
            source_file=src,
            output_file=out,
            original_size=1000,
            output_size=400,
            duration_ms=120,
            status="completed",
        )
        assert tid > 0

        # 2. Query history
        history = mgr.get_recent_history()
        assert len(history) == 1
        entry = history[0]
        assert entry.operation_type == "compress"
        assert entry.space_saved_bytes == 600
        assert entry.compression_ratio_percent == 60.0

        # 3. Stats
        stats = mgr.get_statistics()
        assert stats["total_tasks"] == 1
        assert stats["successful_tasks"] == 1
        assert stats["total_bytes_saved"] == 600

        # 4. Clear history
        mgr.clear_history()
        assert len(mgr.get_recent_history()) == 0

    def test_recent_files_crud(self, tmp_path):
        db_path = tmp_path / "test_recents.db"
        db = Database(db_path=db_path)
        mgr = HistoryManager(database=db)

        f1 = tmp_path / "doc.pdf"
        f1.write_text("pdf")
        mgr.add_recent_file(f1)

        recents = mgr.get_recent_files()
        assert len(recents) == 1
        assert recents[0].file_name == "doc.pdf"
        assert recents[0].file_type == "pdf"

        mgr.clear_recent_files()
        assert len(mgr.get_recent_files()) == 0


class TestSettings:
    def test_settings_load_save(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings = Settings(file_path=settings_file)

        assert settings.get("theme") == "dark"
        settings.set("theme", "light")
        assert settings.get("theme") == "light"

        # Reload from disk
        settings_reloaded = Settings(file_path=settings_file)
        assert settings_reloaded.get("theme") == "light"

        # Reset to defaults
        settings_reloaded.reset_to_defaults()
        assert settings_reloaded.get("theme") == "dark"
