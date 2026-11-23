# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

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
]

# Package data for font/icon/theming libraries
datas += collect_data_files("qt_material")
datas += collect_data_files("qtawesome")
try:
    datas += collect_data_files("pyhanko")
except Exception:
    pass

a = Analysis(
    ["run.py"],
    pathex=[".", "src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "main",
        "pdfcore",
        "pdfcore.signing",
        "pdfcore.document",
        "pdfapp",
        "app",
        "app.core",
        "app.database",
        "app.ui",
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
    ],
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
