# Third-Party Licenses & Open-Source Compliance

DocuTools integrates and depends upon several open-source libraries and frameworks. This document inventories every third-party component, its version, license, upstream repository, role within DocuTools, and redistribution obligations.

---

## 1. Third-Party Component Inventory

| Dependency Name | Version | License | Upstream Repository | Usage within DocuTools | Redistribution & Compliance Obligations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PySide6** | 6.12.0 | LGPL-3.0 / GPL-3.0 / Commercial | https://code.qt.io/cgit/pyside/pyside-setup.git | Core desktop GUI framework, Qt Widgets, styling, QThreadPool, QPainter | - Dynamically link (standard in Python distribution via wheels / shared DLLs).<br>- Preserve Qt copyright notices.<br>- Allow end-users to replace Qt shared libraries or reverse-engineer the application for debugging modifications to LGPL parts. |
| **pikepdf** | 10.18.1 | MPL-2.0 | https://github.com/pikepdf/pikepdf | Low-level PDF stream deduplication, lossless compression, repair of damaged PDFs | - MPL-2.0 is a weak copyleft, file-level license.<br>- Consumed as an unmodified dependency.<br>- Distribute pikepdf source or provide clear link to upstream source if binary wheel is distributed. |
| **pypdf** | 7.1.0 | BSD 3-Clause | https://github.com/py-pdf/pypdf | Pure-Python PDF merger, splitter, page extractor, AES security operations | - Retain the 3-clause BSD copyright notice and disclaimer in binary distribution notices. |
| **Pillow (PIL)** | 11.2.1 | HPND (Historical Permission Notice and Disclaimer) | https://github.com/python-pillow/Pillow | Primary image engine: resizing, cropping, JPEG/PNG/WebP conversion, iterative target-size compression | - Permissive license.<br>- Retain Pillow copyright notice and disclaimer in documentation. |
| **PyMuPDF** | 1.26.3 | AGPL-3.0 / Commercial | https://github.com/pymupdf/PyMuPDF | Headless PDF rendering, in-place text extraction and redaction, high-fidelity rasterization | - Strong reciprocal copyleft (AGPL-3.0).<br>- Requires the distributing application (DocuTools) to be open-source under AGPL-3.0 or a compatible license, providing corresponding source code to recipients.<br>- Commercial license required if proprietary closed-source distribution is intended. |
| **Open-Source-PDF-Editor Core** | 0.12.0 | AGPL-3.0-or-later | https://github.com/RonnyM82/Open-Source-PDF-Editor | Architecture reference and adapted in-place text/image editing engine (`pdfcore`) | - AGPL-3.0-or-later.<br>- Full source code of modified and derived files must be provided under AGPL-3.0.<br>- Prominently display original authorship and copyright notices. |
| **python-docx** | 1.2.0 | MIT | https://github.com/python-openxml/python-docx | Reading, modifying, and generating Microsoft Word (.docx) documents | - Permissive MIT license.<br>- Include original MIT copyright and permission notice in DocuTools distributions. |
| **pyHanko** | 0.38.1 | MIT | https://github.com/MatthiasValvekens/pyHanko | Cryptographic digital signatures (PKCS#12, self-signed certificates) | - Permissive MIT license.<br>- Retain MIT copyright notice in binary and source releases. |
| **cryptography** | 50.0.2 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography | Cryptographic primitives for X.509 certificates and secure password hashing | - Dual Apache-2.0 / BSD.<br>- Retain notices and Apache/BSD license texts. |
| **qt-material** | 2.17 | BSD 2-Clause | https://github.com/UN-GCPDS/qt-material | Modern Material design stylesheets and theme customization | - Retain BSD 2-Clause notice and disclaimer. |
| **QtAwesome** | 1.4.2 | MIT | https://github.com/spyder-ide/qtawesome | FontAwesome and Material design vector icons for Qt widgets | - Retain MIT license notice. Embedded font licenses (SIL OFL) apply to icon fonts. |
| **pytesseract** | 0.3.13 | Apache-2.0 | https://github.com/madmaze/pytesseract | Python wrapper for local Tesseract OCR engine | - Apache-2.0 license.<br>- Retain Apache copyright notice and statement of modifications. |

---

## 2. Redistribution & Compliance Strategy

1. **Licensing of DocuTools**:
   Because DocuTools incorporates and links with PyMuPDF and the PDF editing core under the **GNU Affero General Public License version 3 (AGPL-3.0)**, DocuTools is licensed and distributed under the **AGPL-3.0**.
2. **Access to Source Code**:
   Any distribution of the DocuTools installer or executable will include or provide prominent links to download the complete source code of DocuTools and all modified components.
3. **No Network Bypass**:
   DocuTools operates completely offline. No user data, documents, or telemetry are transmitted to external servers.
4. **Preservation of Notices**:
   All original copyright headers and notice files are preserved across all adapted source files in `src/` and `app/`.
