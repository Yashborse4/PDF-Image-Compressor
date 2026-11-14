"""Global configuration and application constants for DocuTools."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Application identity
APP_NAME = "DocuTools"
APP_VERSION = "1.0.0"
APP_AUTHOR = "DocuTools Team"
APP_DESCRIPTION = "Professional All-in-One Windows PDF, Document and Image Utility Suite"

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent

# User data directory (%LOCALAPPDATA%\DocuTools or portable fallback)
PORTABLE_FLAG = BASE_DIR / "portable.flag"


def get_app_data_dir() -> Path:
    """Return the application data directory for configuration, logs, and database.

    If portable.flag exists in the application root, uses a local 'data' folder.
    Otherwise, standard Windows %LOCALAPPDATA%\\DocuTools.
    """
    if PORTABLE_FLAG.exists():
        data_dir = BASE_DIR / "data"
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            data_dir = Path(local_app_data) / APP_NAME
        else:
            data_dir = Path.home() / f".{APP_NAME.lower()}"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DATA_DIR = get_app_data_dir()
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "docutools.db"

# Supported file extensions
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_DOC_EXTENSIONS = {".docx", ".doc", ".txt", ".rtf", ".odt", ".html", ".htm"}
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".ico",
    ".gif",
}
ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_PDF_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS
)

# Defaults
DEFAULT_THEME = "dark"
MAX_RECENT_FILES = 20
DEFAULT_COMPRESSION_QUALITY = 75
DEFAULT_DPI = 150
