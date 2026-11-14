"""Main application window for DocuTools combining navigation, header, and tool views with smooth transitions."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.logging import get_logger
from app.core.settings import Settings
from app.database.history import HistoryManager
from app.ui.about_view import AboutView
from app.ui.dashboard import DashboardView
from app.ui.history_view import HistoryView
from app.ui.pdf_editor_view import AdvancedPdfEditorView
from app.ui.placeholder_views import BatchView
from app.ui.settings_view import SettingsView
from app.ui.sidebar import SidebarWidget
from app.ui.theme import apply_theme
from app.ui.transitions import SmoothStackedWidget

# Import processing views from docutools
from docutools.core.database import Database as DocuToolsDB
from docutools.ui.views.conversion_view import ConversionView
from docutools.ui.views.document_studio_view import DocumentStudioView
from docutools.ui.views.image_studio_view import ImageStudioView
from docutools.ui.views.pdf_manager_view import PDFManagerView

logger = get_logger("main_window")


class DocuToolsMainWindow(QMainWindow):
    """The unified primary desktop window for DocuTools with Windows 11 Fluent UI and smooth transitions."""

    PAGE_TITLES = {
        "home": ("Home Dashboard", "Overview, stats, and quick tools"),
        "pdf_tools": ("PDF Management Tools", "Merge, split, compress, and organize pages"),
        "pdf_editor": ("Advanced PDF Editor", "In-place text editing, annotations, and signing"),
        "doc_editor": ("Document Editor", "Word-style DOCX rich-text workspace"),
        "image_tools": ("Image Studio", "Resize, crop, and compress images to target sizes"),
        "converter": ("File Converter", "Universal local document and image conversions"),
        "batch": ("Batch Processing Queue", "Concurrent batch processing with live progress"),
        "history": ("Processing History", "Local SQLite audit trail of all operations"),
        "settings": ("Settings", "Preferences, theme, and default export directories"),
        "about": ("About DocuTools", "Version details, offline pledge, and licenses"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.get_instance()
        self.history_mgr = HistoryManager()
        self.legacy_db = DocuToolsDB()
        self.thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("DocuTools — Professional Document & Image Suite")
        self.resize(
            self.settings.get("window_width", 1280),
            self.settings.get("window_height", 820),
        )
        self.setMinimumSize(960, 600)

        self._build_ui()
        self._setup_status_bar()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = SidebarWidget(self)
        self.sidebar.page_selected.connect(self._navigate_to_page)
        root_layout.addWidget(self.sidebar)

        # 2. Main Work Area (Header + Smooth Stacked Pages)
        work_area = QWidget()
        work_layout = QVBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)

        # Header
        self._build_header(work_layout)

        # Smooth Stacked Pages
        self.stack = SmoothStackedWidget(self)
        self.pages: dict[str, QWidget] = {}

        # 0. Dashboard View
        self.dashboard_view = DashboardView(self)
        self.dashboard_view.navigate_to.connect(self._navigate_to_page)
        self.dashboard_view.open_file_requested.connect(self._handle_open_file)
        self._add_page("home", self.dashboard_view)

        # 1. PDF Tools (Manager)
        self.pdf_tools_view = PDFManagerView(self.legacy_db, self.thread_pool, self)
        self._add_page("pdf_tools", self.pdf_tools_view)

        # 2. PDF Editor (In-place editor & annotations)
        self.pdf_editor_view = AdvancedPdfEditorView(self)
        self._add_page("pdf_editor", self.pdf_editor_view)

        # 3. Document Editor (Word-style DOCX & rich text)
        self.doc_editor_view = DocumentStudioView(self.legacy_db, self.thread_pool, self)
        self._add_page("doc_editor", self.doc_editor_view)

        # 4. Image Tools (Image Studio)
        self.image_tools_view = ImageStudioView(self.legacy_db, self.thread_pool, self)
        self._add_page("image_tools", self.image_tools_view)

        # 5. File Converter
        self.converter_view = ConversionView(self.legacy_db, self.thread_pool, self)
        self._add_page("converter", self.converter_view)

        # 6. Batch Processing Queue
        self.batch_view = BatchView(self)
        self._add_page("batch", self.batch_view)

        # 7. Processing History
        self.history_view = HistoryView(self)
        self._add_page("history", self.history_view)

        # 8. Settings
        self.settings_view = SettingsView(self)
        self.settings_view.theme_changed.connect(self._on_theme_changed)
        self._add_page("settings", self.settings_view)

        # 9. About
        self.about_view = AboutView(self)
        self._add_page("about", self.about_view)

        work_layout.addWidget(self.stack)
        root_layout.addWidget(work_area)

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        self.header = QFrame()
        self.header.setObjectName("headerContainer")
        self.header.setFixedHeight(58)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(28, 0, 24, 0)
        header_layout.setSpacing(16)

        # Breadcrumbs
        crumb_layout = QHBoxLayout()
        crumb_layout.setSpacing(8)

        app_label = QLabel("DocuTools")
        app_label.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: 500;")
        crumb_layout.addWidget(app_label)

        chevron = QLabel("›")
        chevron.setStyleSheet("color: #6b7280; font-size: 13px;")
        crumb_layout.addWidget(chevron)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.header_title = QLabel("Home Dashboard")
        self.header_title.setFont(QFont("Segoe UI Variable Display", 13, QFont.Weight.Bold))
        self.header_title.setStyleSheet("color: #ffffff;")
        title_box.addWidget(self.header_title)

        self.header_sub = QLabel("Overview, stats, and quick tools")
        self.header_sub.setStyleSheet("color: #9ca3af; font-size: 10px;")
        title_box.addWidget(self.header_sub)
        crumb_layout.addLayout(title_box)

        header_layout.addLayout(crumb_layout)
        header_layout.addStretch()

        # Windows 11 Pill Search Bar
        import qtawesome as qta
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("Search tools & actions (e.g. merge, compress, docx)...")
        self.search_bar.setFixedWidth(300)
        self.search_bar.returnPressed.connect(self._on_search_submitted)
        header_layout.addWidget(self.search_bar)

        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setProperty("variant", "flat")
        self.theme_btn.setToolTip("Toggle Theme (Dark / Light)")
        is_dark = self.settings.get("theme", "dark") == "dark"
        self.theme_btn.setIcon(qta.icon("fa5s.sun" if is_dark else "fa5s.moon", color="#60cdff"))
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)

        parent_layout.addWidget(self.header)

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("DocuTools Suite Ready")
        self.status_label.setStyleSheet("color: #9ca3af; font-size: 11px; padding-left: 8px;")
        self.status_bar.addWidget(self.status_label, 1)

        privacy_label = QLabel("● 100% Offline & Private")
        privacy_label.setStyleSheet("color: #10b981; font-weight: 600; font-size: 11px; padding-right: 14px;")
        self.status_bar.addPermanentWidget(privacy_label)

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self.pages[page_id] = widget
        self.stack.addWidget(widget)

    def _navigate_to_page(self, page_id: str) -> None:
        """Switch active page with smooth transition and update header breadcrumb."""
        if page_id in self.pages:
            target = self.pages[page_id]
            self.stack.fade_to_widget(target)

            title, sub = self.PAGE_TITLES.get(page_id, ("DocuTools", ""))
            self.header_title.setText(title)
            self.header_sub.setText(sub)

            # Keep sidebar in sync if navigation was triggered from dashboard
            self.sidebar.select_page(page_id, emit_signal=False)

            # Refresh history if navigating to history
            if page_id == "history" and hasattr(self.history_view, "refresh_history"):
                self.history_view.refresh_history()

    def _on_search_submitted(self) -> None:
        """Handle quick search query and navigate to relevant tool."""
        query = self.search_bar.text().lower().strip()
        if not query:
            return

        if any(w in query for w in ["merge", "split", "reorder", "organize", "page", "protect", "lock"]):
            self._navigate_to_page("pdf_tools")
        elif any(w in query for w in ["edit", "annotation", "annotate", "text", "sign", "highlight"]):
            self._navigate_to_page("pdf_editor")
        elif any(w in query for w in ["doc", "docx", "word", "rich", "write"]):
            self._navigate_to_page("doc_editor")
        elif any(w in query for w in ["image", "resize", "crop", "compress", "photo", "pic", "kb", "target"]):
            self._navigate_to_page("image_tools")
        elif any(w in query for w in ["convert", "conversion", "transcode", "export"]):
            self._navigate_to_page("converter")
        elif any(w in query for w in ["batch", "queue", "bulk"]):
            self._navigate_to_page("batch")
        elif any(w in query for w in ["history", "log", "audit", "recent"]):
            self._navigate_to_page("history")
        elif any(w in query for w in ["setting", "pref", "theme", "dark", "light"]):
            self._navigate_to_page("settings")
        elif any(w in query for w in ["about", "license", "version"]):
            self._navigate_to_page("about")
        else:
            self.status_label.setText(f"No direct match for '{query}'. Try 'merge', 'edit', 'resize'...")

        self.search_bar.clear()

    def _handle_open_file(self, file_path_str: str) -> None:
        """Route file to the corresponding editor module with smooth transition."""
        path = Path(file_path_str)
        ext = path.suffix.lower()

        if ext == ".pdf":
            self._navigate_to_page("pdf_editor")
            self.pdf_editor_view.load_pdf(str(path))
            self.status_label.setText(f"Loaded PDF: {path.name}")
        elif ext in {".docx", ".doc"}:
            self._navigate_to_page("doc_editor")
            if hasattr(self.doc_editor_view, "_open_file_path"):
                self.doc_editor_view._open_file_path(path)
            self.status_label.setText(f"Loaded Document: {path.name}")
        elif ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            self._navigate_to_page("image_tools")
            if hasattr(self.image_tools_view, "_load_single_image"):
                self.image_tools_view._load_single_image(str(path))
            self.status_label.setText(f"Loaded Image: {path.name}")

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        import qtawesome as qta
        current = self.settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.settings.set("theme", new_theme)
        self._on_theme_changed(new_theme)

    def _on_theme_changed(self, new_theme: str) -> None:
        """Apply theme update across entire app."""
        import qtawesome as qta
        app = QApplication.instance()
        if app:
            apply_theme(app, new_theme)
        is_dark = new_theme == "dark"
        self.theme_btn.setIcon(qta.icon("fa5s.sun" if is_dark else "fa5s.moon", color="#60cdff"))
        logger.info("Theme switched to %s", new_theme)

    def closeEvent(self, event) -> None:
        """Persist window geometry on exit."""
        self.settings.set("window_width", self.width())
        self.settings.set("window_height", self.height())
        super().closeEvent(event)
