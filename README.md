# PDF Editor

A fast, offline PDF viewer, editor, and merger for Windows built with Python, PySide6, and PyMuPDF.

## Features

- **Viewer**: High-fidelity PDF rendering with zoom, rotation, thumbnails, and search
- **Page Management**: Merge, split, reorder, rotate, extract, and delete pages
- **Direct Editing**: Edit text and images directly on the page
- **Annotations**: Highlights, underlines, freehand drawings, sticky notes, and comments
- **OCR**: Optical character recognition for scanned PDFs via Tesseract
- **Signatures**: Digital signatures and visual stamp placement
- **Themes**: Material Design light and dark themes
- **Offline & Private**: Completely local execution with zero cloud dependencies

## Requirements

- Windows 10/11
- Python 3.12+ (Python 3.13 recommended)

## Quick Start

### 1. Clone & Set Up Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Run Application

```powershell
python -m pdfapp.app
```

### 3. Run Tests

```powershell
pytest
```

## Packaging & Building

Build scripts are provided under the `scripts/` directory:

- `.\scripts\build.ps1`: Builds the standalone PyInstaller executable
- `.\scripts\build_installer.ps1`: Creates the Inno Setup installer package
- `.\scripts\test.ps1`: Runs test suite
- `.\scripts\lint.ps1`: Runs Ruff linter and code formatting checks

## License

Licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).
