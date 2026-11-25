"""UI presentation components."""

from app.ui.about_view import AboutView
from app.ui.dashboard import DashboardView
from app.ui.history_view import HistoryView
from app.ui.main_window import DocuToolsMainWindow
from app.ui.pdf_editor_view import AdvancedPdfEditorView
from app.ui.settings_view import SettingsView
from app.ui.sidebar import SidebarWidget
from app.ui.theme import apply_theme
from app.ui.transitions import SmoothStackedWidget
from app.ui.widgets import FileDropArea, FluentCard, StatCard, StatusPill

__all__ = [
    "AboutView",
    "DashboardView",
    "HistoryView",
    "DocuToolsMainWindow",
    "AdvancedPdfEditorView",
    "SettingsView",
    "SidebarWidget",
    "apply_theme",
    "SmoothStackedWidget",
    "FileDropArea",
    "FluentCard",
    "StatCard",
    "StatusPill",
]
