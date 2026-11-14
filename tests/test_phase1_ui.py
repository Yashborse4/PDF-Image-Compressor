"""Automated UI tests for Phase 1 Main Window, Sidebar, Theme, Transitions, and Dashboard."""

from __future__ import annotations

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.dashboard import DashboardView
from app.ui.main_window import DocuToolsMainWindow
from app.ui.sidebar import SidebarWidget
from app.ui.theme import DARK_PALETTE, LIGHT_PALETTE, apply_theme, generate_qss
from app.ui.transitions import SmoothStackedWidget
from app.ui.widgets import FileDropArea, FluentCard, StatCard, StatusPill


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


class TestPhase1UI:
    def test_theme_generation(self, qapp):
        dark_qss = generate_qss("dark")
        assert "QMainWindow" in dark_qss
        assert DARK_PALETTE["bg_main"] in dark_qss

        light_qss = generate_qss("light")
        assert "QMainWindow" in light_qss
        assert LIGHT_PALETTE["bg_main"] in light_qss

        # Apply to app
        apply_theme(qapp, "dark")
        apply_theme(qapp, "light")

    def test_widgets(self, qapp):
        card = FluentCard(title="Test Card", description="Card Description", icon_name="fa5s.star")
        assert card.title_label.text() == "Test Card"
        assert card.desc_label.text() == "Card Description"

        stat = StatCard(label="Files", value="42", subtext="processed", icon_name="fa5s.file")
        assert stat.value_widget.text() == "42"
        stat.update_value("100")
        assert stat.value_widget.text() == "100"

        pill = StatusPill("Active", variant="success")
        assert "Active" in pill.text()

        drop_area = FileDropArea(prompt_text="Drop Files")
        assert drop_area.label.text() == "Drop Files"

    def test_smooth_transition_stack(self, qapp):
        stack = SmoothStackedWidget()
        w1 = QLabel("Page 1")
        w2 = QLabel("Page 2")
        stack.addWidget(w1)
        stack.addWidget(w2)
        assert stack.count() == 2

        # Trigger smooth fade
        stack.fade_to_widget(w2, duration_ms=50)
        assert stack.currentWidget() == w2

    def test_sidebar_navigation_and_collapse(self, qapp):
        sidebar = SidebarWidget()
        selected_pages = []
        sidebar.page_selected.connect(selected_pages.append)

        sidebar.select_page("pdf_tools")
        assert "pdf_tools" in selected_pages

        sidebar.select_page("image_tools")
        assert "image_tools" in selected_pages

        # Test collapse animation toggle
        assert sidebar._is_collapsed is False
        sidebar.toggle_collapse()
        assert sidebar._is_collapsed is True

    def test_main_window_lifecycle(self, qapp):
        win = DocuToolsMainWindow()
        assert win.windowTitle().startswith("DocuTools")
        assert len(win.pages) >= 10

        # Test navigation to each page with smooth transitions
        for page_id in ["home", "pdf_tools", "pdf_editor", "doc_editor", "image_tools", "converter", "batch", "history", "settings", "about"]:
            win._navigate_to_page(page_id)
            assert win.stack.currentWidget() == win.pages[page_id]

        # Test search navigation
        win.search_bar.setText("merge")
        win._on_search_submitted()
        assert win.stack.currentWidget() == win.pages["pdf_tools"]

        # Test theme toggle
        initial_theme = win.settings.get("theme")
        win._toggle_theme()
        toggled_theme = win.settings.get("theme")
        assert initial_theme != toggled_theme

        win.close()
