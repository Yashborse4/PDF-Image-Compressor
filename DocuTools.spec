# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# 1. Collect dynamic libraries for PyMuPDF (native C extensions)
binaries = collect_dynamic_libs("pymupdf")

# 2. Collect static data assets and modules
datas = [
    ("docutools/assets", "docutools/assets"),
    ("docutools/ui/styles.py", "docutools/ui"),
    ("src/pdfcore", "pdfcore"),
    ("src/pdfapp", "pdfapp"),
    ("app", "app"),
    ("config.py", "."),
    ("main.py", "."),
    ("assets", "assets"),
    ("pyproject.toml", "."),
    ("LICENSE", "."),
]

# Package data for font/icon/theming libraries
datas += collect_data_files("qt_material")
datas += collect_data_files("qtawesome")
try:
    datas += collect_data_files("pyhanko")
except Exception:
    pass

hidden_imports = [
    "main",
    "config",
    "run",
    "pdfcore",
    "pdfcore.signing",
    "pdfcore.document",
    "pdfapp",
    "app",
    "app.core",
    "app.database",
    "app.ui",
    "docutools",
    "docutools.core",
    "docutools.core.pdf_engine",
    "docutools.core.image_engine",
    "docutools.core.database",
    "docutools.core.assets",
    "docutools.ui",
    "docutools.ui.styles",
    "docutools.ui.views",
    "docutools.ui.views.pdf_manager_view",
    "docutools.ui.views.image_processor_view",
    "docutools.ui.views.history_view",
    "docutools.ui.views.settings_view",
    "docutools.app",
    "pyhanko",
    "pyhanko.sign",
    "pyhanko.pdf_utils",
    "pyhanko.sign.fields",
    "pyhanko.sign.signers",
    "pyhanko_certvalidator",
    "cryptography",
    "cryptography.hazmat",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.serialization",
    "cryptography.hazmat.primitives.serialization.pkcs12",
    "asn1crypto",
    "pymupdf",
    "fitz",
    "pikepdf",
    "pypdf",
    "PIL",
    "PIL.Image",
    "qtawesome",
    "qt_material",
    "docx",
    "jinja2",
    "sqlite3",
]

hidden_imports += collect_submodules("docutools")
hidden_imports += collect_submodules("app")
hidden_imports += collect_submodules("pdfcore")
hidden_imports += collect_submodules("pdfapp")

a = Analysis(
    ["run.py"],
    pathex=[".", "src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "scipy",
        "pandas",
        "sklearn",
        "nltk",
        "flask",
        "matplotlib",
        "openpyxl",
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 1. Onedir target: optimized for MSI & Inno Setup installers (instant launch, no temp unpacking)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocuTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["docutools/assets/icon.ico"],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DocuTools",
)

# 2. Standalone Onefile target: completely self-contained portable executable
# Runs from ANY folder (Desktop, Downloads, USB) with zero missing DLL errors.
exe_portable = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DocuTools-Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["docutools/assets/icon.ico"],
)
