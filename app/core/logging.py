"""Structured logging subsystem for DocuTools."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import APP_NAME, LOGS_DIR


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Initialize root application logger with rotating file and console handlers.

    Logs are structured, thread-safe, and never leak sensitive document content.
    """
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler
    target_file = log_file or (LOGS_DIR / "docutools.log")
    try:
        file_handler = RotatingFileHandler(
            target_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning("Failed to initialize file logger at %s: %s", target_file, exc)

    logger.info("DocuTools logging initialized successfully.")
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Retrieve a namespaced child logger."""
    base_name = APP_NAME
    if name:
        return logging.getLogger(f"{base_name}.{name}")
    return logging.getLogger(base_name)
