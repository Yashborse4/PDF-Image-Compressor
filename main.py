"""DocuTools application entry point.

Usage:
    python main.py [optional_file_path]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config import APP_NAME, APP_VERSION
from app.core.logging import setup_logging
from app.core.settings import Settings
from app.database.database import Database
from app.ui.main_window import DocuToolsMainWindow
from app.ui.theme import apply_theme


def main() -> int:
    """Initialize application runtime, services, and launch GUI."""
    # 1. Setup structured logging
    logger = setup_logging()
    logger.info("Starting %s v%s...", APP_NAME, APP_VERSION)

    # 2. Setup SQLite persistence
    Database.get_instance()

    # 3. Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DocuTools")

    # 4. Load preferences & apply theme
    settings = Settings.get_instance()
    theme_mode = settings.get("theme", "dark")
    apply_theme(app, theme_mode)

    # 5. Instantiate Main Window
    window = DocuToolsMainWindow()

    # Handle command-line file argument if provided
    if len(sys.argv) > 1:
        target_file = Path(sys.argv[1]).resolve()
        if target_file.is_file():
            logger.info("Opening initial command-line file: %s", target_file)
            window._handle_open_file(str(target_file))

    window.show()
    logger.info("%s GUI displayed successfully.", APP_NAME)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
