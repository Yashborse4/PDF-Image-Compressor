"""
Reusable Embedded PDF Previewer & Instant Output Viewer Widget for DocuTools.
Provides fast, crisp PyMuPDF page rendering, paging, zoom/fit-width controls,
and one-click file/folder actions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import fitz
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from docutools.core.validator import format_file_size


class PDFPreviewWidget(QFrame):
    """Embedded live PDF previewer and instant output viewer."""

    close_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("pdfPreviewPane")
        self.setMinimumWidth(340)
        self.setStyleSheet("""
            #pdfPreviewPane {
                background-color: #161820;
                border: 1px solid #2b2f3c;
                border-radius: 10px;
            }
            #pdfPreviewPane QLabel {
                border: none;
                background: transparent;
            }
        """)

        self.file_path: Optional[Path] = None
        self._doc: Optional[fitz.Document] = None
        self.total_pages: int = 0
        self.current_page: int = 0
        self.zoom_factor: float = 1.0
        self._fit_width: bool = True
        self._is_output: bool = False
        self._updating_spin: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Header Bar (Mode Badge + File Info + Close)
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.lbl_badge = QLabel("👁 Live PDF Preview")
        self.lbl_badge.setStyleSheet(
            "background-color: rgba(96, 205, 255, 0.14); color: #60cdff; "
            "border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;"
        )
        header_row.addWidget(self.lbl_badge)

        self.lbl_file_info = QLabel("No file loaded")
        self.lbl_file_info.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600;")
        header_row.addWidget(self.lbl_file_info, stretch=1)

        btn_close = QPushButton("✕")
        btn_close.setToolTip("Hide Preview Pane")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton { background: transparent; color: #9ca3af; border: none; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: rgba(239, 68, 68, 0.2); color: #ef4444; }"
        )
        btn_close.clicked.connect(self.close_requested.emit)
        header_row.addWidget(btn_close)
        layout.addLayout(header_row)

        # 2. Navigation & Zoom Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("previewToolbar")
        toolbar.setStyleSheet(
            "#previewToolbar { background-color: #1d2029; border: 1px solid #2b2f3c; border-radius: 7px; }"
        )
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(6, 4, 6, 4)
        tb_lay.setSpacing(4)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(28)
        self.btn_prev.setToolTip("Previous page")
        self.btn_prev.clicked.connect(self.prev_page)
        tb_lay.addWidget(self.btn_prev)

        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, 1)
        self.spin_page.setFixedWidth(54)
        self.spin_page.valueChanged.connect(self._on_spin_changed)
        tb_lay.addWidget(self.spin_page)

        self.lbl_total = QLabel("/ 0")
        self.lbl_total.setStyleSheet("color: #94a3b8; font-size: 11px;")
        tb_lay.addWidget(self.lbl_total)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(28)
        self.btn_next.setToolTip("Next page")
        self.btn_next.clicked.connect(self.next_page)
        tb_lay.addWidget(self.btn_next)

        tb_lay.addStretch()

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedWidth(26)
        self.btn_zoom_out.setToolTip("Zoom out")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        tb_lay.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("Fit")
        self.lbl_zoom.setStyleSheet("color: #93c5fd; font-size: 11px; font-weight: 600; min-width: 36px;")
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_lay.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(26)
        self.btn_zoom_in.setToolTip("Zoom in")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        tb_lay.addWidget(self.btn_zoom_in)

        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setToolTip("Fit page to width")
        self.btn_fit.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        self.btn_fit.clicked.connect(self.fit_to_width)
        tb_lay.addWidget(self.btn_fit)

        layout.addWidget(toolbar)

        # 3. Scrollable PDF Page Canvas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("background-color: #0e1015; border: 1px solid #232631; border-radius: 8px;")

        self.lbl_canvas = QLabel(
            "👁 Live PDF Preview & Instant Output Viewer\n\n"
            "Select any PDF or run an operation\n"
            "to inspect the output here immediately."
        )
        self.lbl_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_canvas.setWordWrap(True)
        self.lbl_canvas.setStyleSheet("color: #64748b; font-size: 12px; padding: 24px;")
        self.scroll.setWidget(self.lbl_canvas)
        layout.addWidget(self.scroll, stretch=1)

        # 4. Quick Output Actions Footer
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.btn_open_external = QPushButton("📂 Open PDF")
        self.btn_open_external.setEnabled(False)
        self.btn_open_external.clicked.connect(self._open_external)
        footer.addWidget(self.btn_open_external)

        self.btn_open_folder = QPushButton("📁 Show in Folder")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self._open_folder)
        footer.addWidget(self.btn_open_folder)
        layout.addLayout(footer)

    def clear(self) -> None:
        """Close any loaded document and reset to empty state."""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None
        self.file_path = None
        self.total_pages = 0
        self.current_page = 0
        self.lbl_file_info.setText("No file loaded")
        self.lbl_total.setText("/ 0")
        self.btn_open_external.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.lbl_canvas.setPixmap(QPixmap())
        self.lbl_canvas.setText(
            "👁 Live PDF Preview & Instant Output Viewer\n\n"
            "Select any PDF or run an operation\n"
            "to inspect the output here immediately."
        )

    def load_pdf(
        self,
        file_path: str | Path,
        password: Optional[str] = None,
        is_output: bool = False,
    ) -> bool:
        """Load a PDF file into the previewer (or instant output viewer)."""
        p = Path(file_path)
        if not p.is_file():
            return False

        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

        try:
            doc = fitz.open(stream=p.read_bytes(), filetype="pdf")
            if doc.needs_pass:
                if password and doc.authenticate(password):
                    pass
                else:
                    doc.close()
                    self.file_path = p
                    self.total_pages = 0
                    self.lbl_file_info.setText(f"{p.name} (Encrypted)")
                    self.btn_open_external.setEnabled(True)
                    self.btn_open_folder.setEnabled(True)
                    self.lbl_canvas.setPixmap(QPixmap())
                    self.lbl_canvas.setText(f"🔒 '{p.name}' is password-protected.\nUnlock or enter password to preview.")
                    return False

            self._doc = doc
            self.file_path = p
            self.total_pages = len(doc)
            self.current_page = 0
            self._is_output = is_output

            if is_output:
                self.lbl_badge.setText("✨ Instant Output Viewer")
                self.lbl_badge.setStyleSheet(
                    "background-color: rgba(16, 185, 129, 0.16); color: #34d399; "
                    "border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;"
                )
            else:
                self.lbl_badge.setText("👁 Live PDF Preview")
                self.lbl_badge.setStyleSheet(
                    "background-color: rgba(96, 205, 255, 0.14); color: #60cdff; "
                    "border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;"
                )

            size_str = format_file_size(p.stat().st_size)
            self.lbl_file_info.setText(f"{p.name}  •  {self.total_pages} pg  •  {size_str}")

            self._updating_spin = True
            self.spin_page.setRange(1, max(1, self.total_pages))
            self.spin_page.setValue(1)
            self._updating_spin = False
            self.lbl_total.setText(f"/ {self.total_pages}")

            self.btn_open_external.setEnabled(True)
            self.btn_open_folder.setEnabled(True)
            self._render_page()
            return True
        except Exception as exc:
            self.lbl_canvas.setPixmap(QPixmap())
            self.lbl_canvas.setText(f"Could not preview '{p.name}':\n{exc}")
            return False

    def _render_page(self) -> None:
        if self._doc is None or self.total_pages == 0:
            return
        page = self._doc[self.current_page]
        if self._fit_width:
            avail_w = max(260, self.scroll.viewport().width() - 28)
            rect = page.rect
            zoom = avail_w / max(rect.width, 1.0)
            self.zoom_factor = max(0.25, min(3.5, zoom))
            self.lbl_zoom.setText("Fit")
        else:
            self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")

        # Render at 1.25x device scale for sharp text, then display cleanly
        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        qimg = pix.tobytes("png")
        px = QPixmap()
        px.loadFromData(qimg, "PNG")
        self.lbl_canvas.setText("")
        self.lbl_canvas.setPixmap(px)

        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < self.total_pages - 1)

    def _on_spin_changed(self, val: int) -> None:
        if self._updating_spin or self.total_pages == 0:
            return
        self.current_page = max(0, min(self.total_pages - 1, val - 1))
        self._render_page()

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._updating_spin = True
            self.spin_page.setValue(self.current_page + 1)
            self._updating_spin = False
            self._render_page()

    def next_page(self) -> None:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._updating_spin = True
            self.spin_page.setValue(self.current_page + 1)
            self._updating_spin = False
            self._render_page()

    def zoom_in(self) -> None:
        self._fit_width = False
        self.zoom_factor = min(3.5, self.zoom_factor + 0.2)
        self._render_page()

    def zoom_out(self) -> None:
        self._fit_width = False
        self.zoom_factor = max(0.3, self.zoom_factor - 0.2)
        self._render_page()

    def fit_to_width(self) -> None:
        self._fit_width = True
        self._render_page()

    def _open_external(self) -> None:
        if self.file_path and self.file_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.file_path)))

    def _open_folder(self) -> None:
        if self.file_path and self.file_path.exists():
            if os.name == "nt":
                os.system(f'explorer /select,"{self.file_path}"')
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.file_path.parent)))
