# PDF-Image-Compressor & DocuTools Suite

[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6?logo=windows)](https://microsoft.com/windows)
[![Python: 3.12 | 3.13](https://img.shields.io/badge/python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52?logo=qt)](https://www.qt.io/)
[![Engine: PyMuPDF + pikepdf + Pillow](https://img.shields.io/badge/engines-PyMuPDF%20%7C%20pikepdf%20%7C%20Pillow-FF6F00)](https://github.com/Yashborse4/PDF-Image-Compressor)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Security: 100% Offline](https://img.shields.io/badge/privacy-100%25%20Offline-success)](https://github.com/Yashborse4/PDF-Image-Compressor)

A modular desktop application built with **Python 3.13 + PySide6 (Qt 6)**, delivering an all-in-one local workspace for **PDF stream compression**, **precision image target-size compression**, page organizing, document authoring, and universal cross-format conversions.

---

## Key Features

### 🗜️ PDF Optimizer & Stream Compressor
- **Deep Stream Optimization**: Utilizes `pikepdf` and `PyMuPDF` to compress PDF streams, remove redundant objects, and deduplicate fonts and resources.
- **Image Downsampling**: Optional recompression and downsampling of embedded bitmap images.
- **Before/After Metrics**: Live metrics displaying original file size, compressed file size, bytes saved, and compression percentage.

### 🖼️ Image Studio & Target-Size Compressor
- **Target File Size Compression**: Binary search compression algorithm that hits exact target file sizes (e.g., 50 KB, 100 KB, 200 KB, 500 KB, or user-specified KB limits) without manual trial-and-error.
- **Quality & Quantization Calibration**: Automatic JPEG/WebP quality optimization and PNG palette color quantization.
- **Dimension Controls**: Exact pixel width and height scaling with aspect-ratio locking and percentage presets (25%, 50%, 75%, 200%).
- **Crop Tool**: Interactive cropping with standard presets (1:1, 4:3, 16:9) or custom bounding boxes.

### 📄 PDF Manager & Page Organizer
- **Interactive Thumbnail Grid**: Visual page previews with zoom and selection controls.
- **Page Reordering**: Drag-and-drop or directional reordering to arrange pages into any desired sequence.
- **Selective Page Extraction**: Pick individual pages or page ranges to extract into standalone PDFs.
- **Merge Engine**: Combine multiple PDF documents into a unified file with drag-and-drop file ordering.
- **Split Engine**: Split by custom page ranges (e.g., `1-3, 5, 8-10`) or by fixed page chunks (every $N$ pages).
- **AES-256 Encryption & Permissions**: Password protect sensitive documents and restrict copying/printing permissions.
- **Cryptographic Digital Signatures (PAdES / PKCS#7)**: Apply standards-compliant detached digital signatures with X.509 PKCS#12 bundles (.p12/.pfx), inspect and verify existing signatures, detect post-signing modifications/tampering, and generate self-signed RSA certificates.

### 🔄 Universal Conversion Center
- **PDF to Images**: Convert PDF pages to high-resolution PNG, JPEG, or WebP with configurable DPI (72 to 600 DPI).
- **Images to PDF**: Compile image collections into a clean, multi-page vector PDF or individual documents.
- **DOCX to PDF**: Direct vector PDF generation from Microsoft Word documents without requiring MS Word or LibreOffice.
- **PDF to Text**: Fast and clean plain-text extraction from documents.
- **Image Transcoding**: Lossless and lossy conversion between PNG, JPEG, WebP, BMP, and TIFF.

### 📝 Document Studio
- **Rich Text Editor**: Built on Qt's `QTextDocument` for word processing.
- **DOCX Interoperability**: Open `.docx` files, edit content, and save back to `.docx` using `python-docx`.
- **Styling & Structure**: Headings, fonts, font sizes, colors, highlights, text alignment, lists, and tables.
- **Vector PDF Export**: One-click direct export to high-resolution vector PDFs.

### ⚡ Batch Processing & Background Architecture
- **Non-blocking UI**: Asynchronous processing powered by `QThreadPool` and worker signals keeps the user interface responsive during heavy jobs.
- **Batch Processing Queue**: Queue multiple images or documents for bulk compression, resizing, and conversion with individual status and progress bars.
- **SQLite Local Storage**: Embedded SQLite database saves application preferences, default export folders, recent files, and complete operation logs.
- **Windows 11 Fluent Design**: Custom dark and light QSS themes with responsive layout design.

---

## Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **GUI Framework** | PySide6 (Qt 6.11+) | Modern desktop UI with Fluent Dark/Light themes |
| **PDF Processing** | PyMuPDF (fitz), pikepdf, pypdf | Rendering, stream compression, page assembly, metadata |
| **Image Engine** | Pillow (PIL) | Target-size binary search, resizing, cropping, quantization |
| **Document Engine** | python-docx, Jinja2 | Word document parsing, HTML generation, and rich-text bridges |
| **Persistence** | SQLite3 | Local storage for recent files, history, and user settings |
| **Icons & Styling** | QtAwesome, qt-material | Vector icons and Material/Fluent design stylesheets |
| **Testing** | pytest, pytest-mock | Automated test suite covering engines and UI components |

---

## Project Structure

```text
PDF-Image-Compressor/
├── app/                        # Application architecture
│   ├── core/                   # Logging, settings, and base contracts
│   ├── database/               # SQLite history and persistence layer
│   └── ui/                     # Windows, dashboard, history & settings views
├── docutools/                  # DocuTools processing modules
│   ├── app.py                  # DocuTools bootstrap
│   ├── main_window.py          # Main window shell & view controller
│   ├── core/                   # Headless processing engines
│   │   ├── conversion_engine.py# Cross-format conversion pipelines
│   │   ├── database.py         # SQLite persistence & recent files
│   │   ├── docx_engine.py      # python-docx parser & HTML bridge
│   │   ├── image_engine.py     # Pillow resize, crop & target compression
│   │   ├── pdf_engine.py       # PDF merge, split, compress & encryption
│   │   └── validator.py        # File validation and MIME verification
│   ├── ui/                     # Views, components, and Fluent styles
│   └── workers/                # QThreadPool background task runners
├── src/                        # Supplementary PDF viewer/editor core
│   ├── pdfapp/                 # Standalone PDF editing application
│   └── pdfcore/                # Rendering, annotations, signing & OCR
├── tests/                      # Automated test suite
├── scripts/                    # Build, test, and packaging scripts
├── installer/                  # Inno Setup Windows installer configurations
├── config.py                   # Central application configuration
├── main.py                     # Primary GUI application entry point
├── run.py                      # DocuTools launch script
├── pyproject.toml              # Build system specification
└── requirements.txt            # Python dependencies
```

---

## Getting Started

### Prerequisites

- **OS**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.12 or Python 3.13

### 1. Clone the Repository

```powershell
git clone https://github.com/Yashborse4/PDF-Image-Compressor.git
cd PDF-Image-Compressor
```

### 2. Set Up Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## Running the Application

Launch via the main application launcher:

```powershell
python main.py
```

Or launch via the DocuTools suite runner:

```powershell
python run.py
```

---

## Running Tests

Execute the automated test suite with `pytest`:

```powershell
# Run core engine tests
python -m pytest tests/test_database.py tests/test_pdf_engine.py tests/test_image_engine.py tests/test_docx_engine.py tests/test_conversion_engine.py -v

# Run phase verification tests
python -m pytest tests/test_phase1_core.py -v
```

---

## Building Executable & Installer

Scripts for creating standalone Windows binaries and setup installers:

```powershell
# Build standalone PyInstaller executable
.\scripts\build.ps1

# Build Inno Setup installer package (requires Inno Setup 6.3+)
.\scripts\build_installer.ps1
```

---

## Privacy & Security

- **100% Local Execution**: All compression, editing, rendering, and conversion occurs entirely on your local machine.
- **Zero Cloud Calls**: No network connectivity required and no data telemetry transmitted.
- **AES-256 Encryption**: Standard-compliant encryption for securing sensitive PDFs with granular permission controls.

---

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).
