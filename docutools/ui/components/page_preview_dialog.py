"""
Interactive Large Page Preview & Inspection Dialog for PDF Manager.
Provides high-resolution vector page viewing, zoom scaling, rotation,
keyboard navigation, and multi-page selection management including
'Select All Pages' and extraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from docutools.core.assets import get_app_icon_path
from docutools.core.pdf_engine import PDFEngine


class PagePreviewDialog(QDialog):
    """Large inspection and page selection window for PDF pages."""

    selection_changed = Signal(int, bool)     # (page_index, is_selected)
    select_all_requested = Signal()          # All pages selected
    deselect_all_requested = Signal()        # All pages deselected
    rotate_page_requested = Signal(int)      # (page_index)
    delete_page_requested = Signal(int)      # (page_index)
    extract_requested = Signal(list)         # (selected_indices)

    def __init__(
        self,
        file_path: str,
        pages_data: List[Dict[str, Any]],
        initial_index: int = 0,
        selected_indices: Optional[Set[int]] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.file_path = file_path
        self.pages_data = pages_data  # [{orig_index: int, rotation: int, pixmap_bytes: bytes}]
        self.total_pages = len(pages_data)
        self.current_index = max(0, min(initial_index, self.total_pages - 1)) if self.total_pages > 0 else 0
        self.selected_indices: Set[int] = set(selected_indices) if selected_indices is not None else set()

        self.zoom_factor: float = 1.3
        self._cache: Dict[tuple[int, int, int], bytes] = {}  # (orig_index, zoom_int, rotation) -> png_bytes
        self._updating_controls = False

        self._setup_window()
        self._init_ui()
        self._setup_shortcuts()
        self._render_current_page()
        self._update_selection_summary()

    def _setup_window(self) -> None:
        file_name = Path(self.file_path).name if self.file_path else "Document"
        self.setWindowTitle(f"Page Inspector — {file_name}")
        icon_path = get_app_icon_path()
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1020, 820)
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # --- Top Navigation & Zoom Toolbar ---
        nav_card = QFrame()
        nav_card.setProperty("class", "cardFrame")
        nav_card.setStyleSheet("background-color: #17181c; border: 1px solid #282a30; border-radius: 6px; padding: 4px;")
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(8, 6, 8, 6)
        nav_layout.setSpacing(8)

        # Page navigation
        self.btn_prev = QPushButton("◀ Prev Page")
        self.btn_prev.setToolTip("Previous page (Left arrow or Page Up)")
        self.btn_prev.clicked.connect(self._go_previous_page)
        nav_layout.addWidget(self.btn_prev)

        lbl_page_text = QLabel("Page")
        lbl_page_text.setStyleSheet("font-weight: 500; color: #cbd5e1;")
        nav_layout.addWidget(lbl_page_text)

        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, max(1, self.total_pages))
        self.spin_page.setValue(self.current_index + 1)
        self.spin_page.setFixedWidth(65)
        self.spin_page.valueChanged.connect(self._on_spin_page_changed)
        nav_layout.addWidget(self.spin_page)

        self.lbl_page_total = QLabel(f"of {self.total_pages}")
        self.lbl_page_total.setStyleSheet("color: #94a3b8; font-weight: 500;")
        nav_layout.addWidget(self.lbl_page_total)

        self.btn_next = QPushButton("Next Page ▶")
        self.btn_next.setToolTip("Next page (Right arrow or Page Down)")
        self.btn_next.clicked.connect(self._go_next_page)
        nav_layout.addWidget(self.btn_next)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("color: #334155; margin: 0 4px;")
        nav_layout.addWidget(div1)

        # Zoom Controls
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedSize(28, 28)
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl + Minus)")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        nav_layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel(f"{int(self.zoom_factor * 100)}%")
        self.lbl_zoom.setFixedWidth(52)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_zoom.setStyleSheet("font-weight: 600; color: #60a5fa;")
        nav_layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(28, 28)
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl + Plus)")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        nav_layout.addWidget(self.btn_zoom_in)

        self.btn_fit_width = QPushButton("Fit Width")
        self.btn_fit_width.setToolTip("Fit page to window width")
        self.btn_fit_width.clicked.connect(self._fit_to_width)
        nav_layout.addWidget(self.btn_fit_width)

        self.btn_fit_page = QPushButton("Fit Page")
        self.btn_fit_page.setToolTip("Fit entire page within view")
        self.btn_fit_page.clicked.connect(self._fit_to_page)
        nav_layout.addWidget(self.btn_fit_page)

        self.btn_actual_size = QPushButton("100%")
        self.btn_actual_size.setToolTip("Reset to 100% normal scale")
        self.btn_actual_size.clicked.connect(self._set_100_percent)
        nav_layout.addWidget(self.btn_actual_size)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet("color: #334155; margin: 0 4px;")
        nav_layout.addWidget(div2)

        # Rotate
        self.btn_rotate = QPushButton("⟳ Rotate 90°")
        self.btn_rotate.setToolTip("Rotate current page 90 degrees clockwise")
        self.btn_rotate.clicked.connect(self._rotate_current_page)
        nav_layout.addWidget(self.btn_rotate)

        nav_layout.addStretch()

        self.btn_close = QPushButton("✕ Close")
        self.btn_close.setToolTip("Close preview window (Escape)")
        self.btn_close.clicked.connect(self.accept)
        nav_layout.addWidget(self.btn_close)

        main_layout.addWidget(nav_card)

        # --- Secondary Toolbar: Multi-Page Selection & Action Bar ---
        sel_card = QFrame()
        sel_card.setStyleSheet("background-color: #121316; border: 1px solid #23252a; border-radius: 6px; padding: 4px;")
        sel_layout = QHBoxLayout(sel_card)
        sel_layout.setContentsMargins(10, 6, 10, 6)
        sel_layout.setSpacing(10)

        # Checkbox for current page
        self.chk_current_page = QCheckBox("Select This Page")
        self.chk_current_page.setStyleSheet("font-weight: 600; font-size: 13px; color: #f1f5f9;")
        self.chk_current_page.setToolTip("Toggle selection of currently viewed page (Space key)")
        self.chk_current_page.toggled.connect(self._on_current_page_toggled)
        sel_layout.addWidget(self.chk_current_page)

        div3 = QFrame()
        div3.setFrameShape(QFrame.Shape.VLine)
        div3.setStyleSheet("color: #334155; margin: 0 4px;")
        sel_layout.addWidget(div3)

        # Prominent Select All Pages Button
        self.btn_select_all = QPushButton("☑ Select All Pages")
        self.btn_select_all.setStyleSheet(
            "background-color: #1e3a8a; color: #ffffff; font-weight: 600; border: 1px solid #3b82f6; border-radius: 5px; padding: 5px 12px;"
        )
        self.btn_select_all.setToolTip("Select every page in the document")
        self.btn_select_all.clicked.connect(self.select_all_pages)
        sel_layout.addWidget(self.btn_select_all)

        # Prominent Deselect All Button
        self.btn_deselect_all = QPushButton("☐ Deselect All")
        self.btn_deselect_all.setStyleSheet("border-radius: 5px; padding: 5px 12px; color: #cbd5e1;")
        self.btn_deselect_all.setToolTip("Deselect all pages")
        self.btn_deselect_all.clicked.connect(self.deselect_all_pages)
        sel_layout.addWidget(self.btn_deselect_all)

        # Selection Badge / Counter
        self.lbl_selection_summary = QLabel("0 of 0 pages selected")
        self.lbl_selection_summary.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; font-weight: 600; padding: 4px 10px; border-radius: 12px; font-size: 12px;"
        )
        sel_layout.addWidget(self.lbl_selection_summary)

        # Remove current page button
        self.btn_delete_current = QPushButton("🗑️ Remove Page")
        self.btn_delete_current.setToolTip("Remove this unneeded page from the assembled document (Delete key)")
        self.btn_delete_current.setStyleSheet(
            "background-color: #450a0a; color: #f87171; border: 1px solid #7f1d1d; border-radius: 5px; padding: 5px 10px;"
        )
        self.btn_delete_current.clicked.connect(self._delete_current_page)
        sel_layout.addWidget(self.btn_delete_current)

        sel_layout.addStretch()

        # Action: Extract selected pages directly
        self.btn_extract_selected = QPushButton("✂ Extract Selected Pages...")
        self.btn_extract_selected.setProperty("class", "primaryButton")
        self.btn_extract_selected.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 600; border-radius: 5px; padding: 5px 14px;"
        )
        self.btn_extract_selected.clicked.connect(self._on_extract_clicked)
        sel_layout.addWidget(self.btn_extract_selected)

        main_layout.addWidget(sel_card)

        # --- Main High-Res Preview Canvas (Scroll Area) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #0b0c0e; border: 1px solid #1f2127; border-radius: 6px;")

        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("background-color: #0b0c0e;")
        c_layout = QVBoxLayout(self.canvas_container)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setContentsMargins(18, 18, 18, 18)

        self.lbl_page_image = QLabel()
        self.lbl_page_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page_image.setStyleSheet(
            "background-color: #141518; border: 1px solid #2d3039; border-radius: 4px; box-shadow: 0 4px 14px rgba(0,0,0,0.4);"
        )
        c_layout.addWidget(self.lbl_page_image)

        self.scroll_area.setWidget(self.canvas_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._go_previous_page)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._go_next_page)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, self._go_previous_page)
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, self._go_next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_current_selection)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self._delete_current_page)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self._set_100_percent)
        QShortcut(QKeySequence("Ctrl+A"), self, self.select_all_pages)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self._go_previous_page()
            event.accept()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._go_next_page()
            event.accept()
        elif key == Qt.Key.Key_Space:
            self._toggle_current_selection()
            event.accept()
        elif key == Qt.Key.Key_Delete:
            self._delete_current_page()
            event.accept()
        elif key == Qt.Key.Key_Escape:
            self.accept()
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Ctrl + Wheel zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in()
            elif delta < 0:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def _render_current_page(self) -> None:
        if self.total_pages == 0:
            self.lbl_page_image.setText("No pages to display.")
            return

        page_meta = self.pages_data[self.current_index]
        orig_index = page_meta["orig_index"]
        rotation = page_meta.get("rotation", 0)
        source_file = page_meta.get("source_file", self.file_path)
        doc_name = page_meta.get("doc_name", "")

        # Check in memory cache
        cache_key = (str(source_file), orig_index, int(self.zoom_factor * 100), rotation % 360)
        png_bytes = self._cache.get(cache_key)

        if not png_bytes:
            try:
                png_bytes = PDFEngine.render_page_hires(
                    file_path=source_file,
                    page_index=orig_index,
                    zoom=self.zoom_factor,
                    rotation=rotation
                )
                self._cache[cache_key] = png_bytes
            except Exception as e:
                self.lbl_page_image.setText(f"Error rendering page {self.current_index + 1}: {e}")
                return

        px = QPixmap()
        px.loadFromData(png_bytes)
        self.lbl_page_image.setPixmap(px)

        # Update controls
        self._updating_controls = True
        self.spin_page.setValue(self.current_index + 1)
        self.chk_current_page.setChecked(self.current_index in self.selected_indices)
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < self.total_pages - 1)
        self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")
        doc_suffix = f" ({doc_name})" if doc_name else ""
        self.lbl_page_total.setText(f"of {self.total_pages}{doc_suffix}")
        self._updating_controls = False

    def _delete_current_page(self) -> None:
        """Remove currently viewed page from the assembled document."""
        if self.total_pages <= 1:
            return
        idx = self.current_index
        self.delete_page_requested.emit(idx)
        del self.pages_data[idx]
        self.total_pages = len(self.pages_data)
        # Re-index selection set
        new_sel = set()
        for s in self.selected_indices:
            if s < idx:
                new_sel.add(s)
            elif s > idx:
                new_sel.add(s - 1)
        self.selected_indices = new_sel
        self.current_index = min(idx, self.total_pages - 1)
        self.spin_page.setMaximum(self.total_pages)
        self._update_selection_summary()
        self._render_current_page()

    def _update_selection_summary(self) -> None:
        sel_count = len(self.selected_indices)
        self.lbl_selection_summary.setText(f"{sel_count} of {self.total_pages} pages selected")
        if sel_count > 0:
            self.lbl_selection_summary.setStyleSheet(
                "background-color: #064e3b; color: #34d399; font-weight: 600; padding: 4px 10px; border-radius: 12px; font-size: 12px;"
            )
        else:
            self.lbl_selection_summary.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; font-weight: 600; padding: 4px 10px; border-radius: 12px; font-size: 12px;"
            )

    def _go_previous_page(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._render_current_page()

    def _go_next_page(self) -> None:
        if self.current_index < self.total_pages - 1:
            self.current_index += 1
            self._render_current_page()

    def _on_spin_page_changed(self, val: int) -> None:
        if self._updating_controls:
            return
        target = val - 1
        if 0 <= target < self.total_pages and target != self.current_index:
            self.current_index = target
            self._render_current_page()

    def _on_current_page_toggled(self, checked: bool) -> None:
        if self._updating_controls:
            return
        if checked:
            self.selected_indices.add(self.current_index)
        else:
            self.selected_indices.discard(self.current_index)

        self._update_selection_summary()
        self.selection_changed.emit(self.current_index, checked)

    def _toggle_current_selection(self) -> None:
        self.chk_current_page.setChecked(not self.chk_current_page.isChecked())

    def select_all_pages(self) -> None:
        """Select every page in the document."""
        self.selected_indices = set(range(self.total_pages))
        self._updating_controls = True
        self.chk_current_page.setChecked(True)
        self._updating_controls = False
        self._update_selection_summary()
        self.select_all_requested.emit()

    def deselect_all_pages(self) -> None:
        """Deselect all pages."""
        self.selected_indices.clear()
        self._updating_controls = True
        self.chk_current_page.setChecked(False)
        self._updating_controls = False
        self._update_selection_summary()
        self.deselect_all_requested.emit()

    def _rotate_current_page(self) -> None:
        if self.total_pages == 0:
            return
        meta = self.pages_data[self.current_index]
        meta["rotation"] = (meta.get("rotation", 0) + 90) % 360
        self.rotate_page_requested.emit(self.current_index)
        self._render_current_page()

    def _zoom_in(self) -> None:
        self.zoom_factor = min(3.5, round(self.zoom_factor + 0.2, 1))
        self._render_current_page()

    def _zoom_out(self) -> None:
        self.zoom_factor = max(0.4, round(self.zoom_factor - 0.2, 1))
        self._render_current_page()

    def _set_100_percent(self) -> None:
        self.zoom_factor = 1.0
        self._render_current_page()

    def _fit_to_width(self) -> None:
        if self.total_pages == 0:
            return
        # Calculate viewport width available
        avail_w = max(self.scroll_area.viewport().width() - 40, 200)
        # Approximate unscaled width of current page (assumed 612 pt for standard letter/A4)
        approx_w = 612.0
        self.zoom_factor = max(0.4, min(3.5, round(avail_w / approx_w, 2)))
        self._render_current_page()

    def _fit_to_page(self) -> None:
        if self.total_pages == 0:
            return
        avail_w = max(self.scroll_area.viewport().width() - 40, 200)
        avail_h = max(self.scroll_area.viewport().height() - 40, 200)
        scale_w = avail_w / 612.0
        scale_h = avail_h / 792.0
        self.zoom_factor = max(0.4, min(3.5, round(min(scale_w, scale_h), 2)))
        self._render_current_page()

    def _on_extract_clicked(self) -> None:
        if not self.selected_indices:
            # If none selected, offer to select current
            self.chk_current_page.setChecked(True)

        selected_order = sorted(list(self.selected_indices))
        self.extract_requested.emit(selected_order)
