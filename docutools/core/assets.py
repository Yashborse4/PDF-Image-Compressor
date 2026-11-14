"""
Asset path resolution utilities for DocuTools (source and frozen executable modes).
"""

import sys
from pathlib import Path


def get_asset_path(filename: str) -> Path:
    """Return absolute path to an asset file in docutools/assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS) / "docutools" / "assets"
        p = base_dir / filename
        if p.exists():
            return p

    # Standard source directory fallback
    curr = Path(__file__).resolve().parent.parent / "assets" / filename
    if curr.exists():
        return curr

    # Root assets fallback
    root_fallback = Path(__file__).resolve().parent.parent.parent / "assets" / filename
    return root_fallback if root_fallback.exists() else curr


def get_app_icon_path(ico: bool = False) -> str:
    """Return path to icon.ico or icon.png."""
    filename = "icon.ico" if ico else "icon.png"
    return str(get_asset_path(filename))


def get_sidebar_toggle_icon_path(collapsed: bool = False) -> str:
    """Return path to sidebar toggle icon."""
    filename = "sidebar_toggle_collapsed.png" if collapsed else "sidebar_toggle.png"
    return str(get_asset_path(filename))
