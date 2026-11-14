"""
Unit tests for DocuTools SQLite database layer.
"""

import tempfile
from pathlib import Path
from docutools.core.database import Database


def test_database_settings():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "test.db"
        db = Database(db_file)

        # Test default
        assert db.get_setting("theme") == "dark"

        # Update setting
        db.set_setting("theme", "light")
        assert db.get_setting("theme") == "light"

        # Complex setting (dict)
        db.set_setting("custom_config", {"a": 1, "b": "hello"})
        assert db.get_setting("custom_config") == {"a": 1, "b": "hello"}


def test_database_recent_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "test.db"
        db = Database(db_file)

        # Create dummy file
        test_file = Path(tmp_dir) / "sample.pdf"
        test_file.write_text("dummy content")

        db.add_recent_file(test_file, file_type="pdf")
        recents = db.get_recent_files()
        assert len(recents) == 1
        assert recents[0]["file_name"] == "sample.pdf"
        assert recents[0]["file_type"] == "pdf"


def test_database_history():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "test.db"
        db = Database(db_file)

        op_id = db.log_operation(
            module="PDF Manager",
            action="Merge",
            output_file="out.pdf",
            initial_size=5000,
            final_size=4000,
            status="success"
        )
        assert op_id > 0

        history = db.get_history()
        assert len(history) == 1
        assert history[0]["module"] == "PDF Manager"
        assert history[0]["action"] == "Merge"
        assert history[0]["status"] == "success"
