"""
Main Application Shell for DocuTools.
Hosts the collapsible navigation sidebar and stacked views for all 8 modules.
Includes global keyboard shortcuts, cross-module navigation, and theme coordination.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from docutools.core.assets import get_app_icon_path
from docutools.core.database import Database
from docutools.ui.components.sidebar import Sidebar
from docutools.ui.styles import get_stylesheet
from docutools.ui.views.batch_processing_view import BatchProcessingView
from docutools.ui.views.conversion_view import ConversionView
from docutools.ui.views.document_studio_view import DocumentStudioView
from docutools.ui.views.history_view import HistoryView
from docutools.ui.views.home_view import HomeView
from docutools.ui.views.image_studio_view import ImageStudioView
from docutools.ui.views.pdf_manager_view import PDFManagerView
from docutools.ui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    """Primary window shell containing sidebar navigation and 8 active module views."""

    PAGE_NAMES = [
        "Home Dashboard",
        "PDF Tools",
        "Document Editor",
        "Image Tools",
        "Converter",
        "Batch Processing",
        "Activity History",
        "Settings",
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("DocuTools — Windows Desktop Suite")
        self.setWindowIcon(QIcon(get_app_icon_path(ico=True)))
        self.resize(1300, 860)
        self.setMinimumSize(980, 660)

        # Shared Infrastructure
        self.db = Database()
        self.thread_pool = QThreadPool.globalInstance()

        self._init_ui()
        self._setup_shortcuts()
        self._apply_theme(self.db.get_setting("theme", "dark"))

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)

        # 2. Stacked Content Views (8 primary modules)
        self.stack = QStackedWidget()

        self.view_home = HomeView(self.db)
        self.view_pdf = PDFManagerView(self.db, self.thread_pool)
        self.view_docx = DocumentStudioView(self.db, self.thread_pool)
        self.view_image = ImageStudioView(self.db, self.thread_pool)
        self.view_conv = ConversionView(self.db, self.thread_pool)
        self.view_batch = BatchProcessingView(self.db, self.thread_pool)
        self.view_history = HistoryView(self.db)
        self.view_settings = SettingsView(self.db, theme_change_callback=self._apply_theme)

        # Connect Home View interactions
        self.view_home.navigate_requested.connect(self.sidebar.select_page)
        self.view_home.file_open_requested.connect(self._handle_file_open_from_home)

        # Register views in order
        self.stack.addWidget(self.view_home)      # Index 0
        self.stack.addWidget(self.view_pdf)       # Index 1
        self.stack.addWidget(self.view_docx)      # Index 2
        self.stack.addWidget(self.view_image)     # Index 3
        self.stack.addWidget(self.view_conv)      # Index 4
        self.stack.addWidget(self.view_batch)     # Index 5
        self.stack.addWidget(self.view_history)   # Index 6
        self.stack.addWidget(self.view_settings)  # Index 7

        main_layout.addWidget(self.stack, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("DocuTools ready.")

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts for fast keyboard-driven navigation."""
        # Ctrl+1 to Ctrl+8 for page navigation
        for i in range(8):
            sc = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            sc.activated.connect(lambda idx=i: self.sidebar.select_page(idx))

        # Ctrl+O: Open file for current active module
        sc_open = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self._trigger_open_active_view)

        # Ctrl+S: Save for current view
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self._trigger_save_active_view)

        # Ctrl+N: New document
        sc_new = QShortcut(QKeySequence("Ctrl+N"), self)
        sc_new.activated.connect(lambda: (self.sidebar.select_page(2), self.view_docx._new_document()))

        # Ctrl+T: Toggle theme
        sc_theme = QShortcut(QKeySequence("Ctrl+T"), self)
        sc_theme.activated.connect(self._toggle_theme)

        # Ctrl+W: Collapse / expand sidebar
        sc_sidebar = QShortcut(QKeySequence("Ctrl+W"), self)
        sc_sidebar.activated.connect(self.sidebar.toggle_collapse)

    def _on_page_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.PAGE_NAMES):
            self.status_bar.showMessage(f"Active Module: {self.PAGE_NAMES[index]}")

        # Refresh dashboard or history on activation
        if index == 0:
            self.view_home.refresh_dashboard()
        elif index == 6:
            self.view_history.refresh_history()

    def _handle_file_open_from_home(self, file_path: str, file_type: str) -> None:
        """Route open requests from home dashboard to the corresponding tool."""
        if file_type == "pdf":
            self.sidebar.select_page(1)
            self.view_pdf.load_pdf(file_path)
        elif file_type == "docx":
            self.sidebar.select_page(2)
            self.view_docx.load_docx(file_path)
        elif file_type == "image":
            self.sidebar.select_page(3)
            self.view_image.load_image(file_path)
        else:
            self.sidebar.select_page(4)

    def _trigger_open_active_view(self) -> None:
        idx = self.stack.currentIndex()
        if idx == 1:
            self.view_pdf._select_pdf_dialog()
        elif idx == 2:
            self.view_docx._open_docx_dialog()
        elif idx == 3:
            self.view_image._select_image_dialog()

    def _trigger_save_active_view(self) -> None:
        idx = self.stack.currentIndex()
        if idx == 2:
            self.view_docx._save_docx_dialog()
        elif idx == 3:
            self.view_image._execute_single_process()

    def _toggle_theme(self) -> None:
        curr = self.db.get_setting("theme", "dark")
        new_theme = "light" if curr == "dark" else "dark"
        self.db.set_setting("theme", new_theme)
        self._apply_theme(new_theme)
        self.view_settings.combo_theme.blockSignals(True)
        self.view_settings.combo_theme.setCurrentIndex(0 if new_theme == "dark" else 1)
        self.view_settings.combo_theme.blockSignals(False)

    def _apply_theme(self, theme_name: str) -> None:
        qss = get_stylesheet(theme_name)
        self.setStyleSheet(qss)
