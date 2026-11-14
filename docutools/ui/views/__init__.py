"""
Views package for DocuTools.
"""

from docutools.ui.views.batch_processing_view import BatchProcessingView
from docutools.ui.views.conversion_view import ConversionView
from docutools.ui.views.document_studio_view import DocumentStudioView
from docutools.ui.views.history_view import HistoryView
from docutools.ui.views.home_view import HomeView
from docutools.ui.views.image_studio_view import ImageStudioView
from docutools.ui.views.pdf_manager_view import PDFManagerView
from docutools.ui.views.settings_view import SettingsView

# Aliases matching the roadmap specification
PDFToolsView = PDFManagerView
DocumentEditorView = DocumentStudioView
ImageToolsView = ImageStudioView
ConverterView = ConversionView

__all__ = [
    "BatchProcessingView",
    "ConversionView",
    "ConverterView",
    "DocumentEditorView",
    "DocumentStudioView",
    "HistoryView",
    "HomeView",
    "ImageStudioView",
    "ImageToolsView",
    "PDFManagerView",
    "PDFToolsView",
    "SettingsView",
]
