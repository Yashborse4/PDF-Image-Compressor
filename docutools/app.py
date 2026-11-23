"""
Application Bootstrap and entry point for DocuTools.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from docutools.core.assets import get_app_icon_path
from docutools.main_window import MainWindow

logger = logging.getLogger("docutools.app")


def _setup_logging() -> None:
    """Initialize file and stream logging for DocuTools."""
    try:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            log_dir = Path(local_appdata) / "DocuTools" / "logs"
        else:
            log_dir = Path.home() / ".docutools" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "docutools.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(str(log_file), encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        logger.info("DocuTools logging initialized at %s", log_file)
    except Exception as e:
        sys.stderr.write(f"Failed to initialize logging: {e}\n")


def main() -> int:
    """Run DocuTools Desktop Application."""
    _setup_logging()
    logger.info("Launching DocuTools Desktop Application...")

    app = QApplication(sys.argv)
    app.setApplicationName("DocuTools")
    app.setOrganizationName("DocuTools")
    app.setApplicationDisplayName("DocuTools Desktop Suite")

    # Set universal application icon
    icon_path = get_app_icon_path(ico=True)
    if Path(icon_path).is_file():
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    try:
        window = MainWindow()
        window.show()
        logger.info("DocuTools main window displayed successfully.")
        return app.exec()
    except Exception as exc:
        logger.exception("Fatal error launching DocuTools main window: %s", exc)
        QMessageBox.critical(
            None,
            "DocuTools Error",
            f"Failed to start DocuTools:\n\n{exc}\n\nSee log file for details.",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
