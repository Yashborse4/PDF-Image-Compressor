"""
Tests verifying application icon generation, paths, and UI version cleanliness.
"""

from pathlib import Path
from PIL import Image
from docutools.core.assets import get_app_icon_path, get_asset_path


def test_icon_assets_exist():
    png_path = Path(get_app_icon_path(ico=False))
    ico_path = Path(get_app_icon_path(ico=True))

    assert png_path.exists(), f"Missing PNG icon at {png_path}"
    assert ico_path.exists(), f"Missing ICO icon at {ico_path}"

    with Image.open(png_path) as img:
        assert img.size == (512, 512)
        assert img.format == "PNG"

    with Image.open(ico_path) as img:
        assert img.format == "ICO"
        assert img.size[0] >= 16


def test_no_version_strings_in_ui():
    ui_dir = Path(__file__).resolve().parent.parent / "docutools" / "ui"
    for py_file in ui_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "v1.0" not in content, f"Found version string 'v1.0' in {py_file}"
        assert "v1.0.0" not in content, f"Found version string 'v1.0.0' in {py_file}"
        assert "⚡" not in content, f"Found lightning symbol in {py_file}"


def test_sidebar_toggle_icon_exists():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from docutools.core.assets import get_sidebar_toggle_icon_path
    from docutools.ui.components.sidebar import Sidebar

    expanded_path = Path(get_sidebar_toggle_icon_path(collapsed=False))
    collapsed_path = Path(get_sidebar_toggle_icon_path(collapsed=True))

    assert expanded_path.exists(), f"Missing toggle icon at {expanded_path}"
    assert collapsed_path.exists(), f"Missing collapsed toggle icon at {collapsed_path}"

    sidebar = Sidebar()
    assert sidebar.btn_collapse.text() == "", "Collapse button should have no text (icon only)"
    assert not sidebar.btn_collapse.icon().isNull(), "Collapse button should have an icon set"
