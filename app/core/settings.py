"""Application settings and user preferences management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR, DEFAULT_THEME
from app.core.logging import get_logger

logger = get_logger("settings")


class Settings:
    """Persistent user preferences manager."""

    _instance: Settings | None = None
    _file_path: Path = DATA_DIR / "settings.json"

    DEFAULT_SETTINGS: dict[str, Any] = {
        "theme": DEFAULT_THEME,
        "default_output_dir": str(Path.home() / "Documents"),
        "open_output_folder_after_process": True,
        "recent_files_limit": 20,
        "pdf_compression_preset": "recommended",
        "image_compression_quality": 80,
        "preserve_image_metadata": True,
        "window_width": 1280,
        "window_height": 820,
        "sidebar_collapsed": False,
    }

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or self._file_path
        self._data: dict[str, Any] = dict(self.DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> Settings:
        """Singleton accessor for application settings."""
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def load(self) -> None:
        """Load settings from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data.update(loaded)
                logger.debug("Settings loaded from %s", self.file_path)
            except Exception as exc:
                logger.error("Failed to load settings from %s: %s", self.file_path, exc)
        else:
            self.save()

    def save(self) -> None:
        """Persist current settings to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            logger.debug("Settings saved to %s", self.file_path)
        except Exception as exc:
            logger.error("Failed to save settings to %s: %s", self.file_path, exc)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._data.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any) -> None:
        """Update a setting value and persist."""
        self._data[key] = value
        self.save()

    def reset_to_defaults(self) -> None:
        """Restore all settings to initial defaults."""
        self._data = dict(self.DEFAULT_SETTINGS)
        self.save()
