"""About view displaying version information, offline pledge, and open source licenses."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config import APP_DESCRIPTION, APP_NAME, APP_VERSION, BASE_DIR


class AboutView(QWidget):
    """About view with version information and third-party license credits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Title Card
        title_card = QFrame()
        title_card.setProperty("card", "true")
        title_layout = QVBoxLayout(title_card)
        title_layout.setContentsMargins(24, 20, 24, 20)
        title_layout.setSpacing(6)

        title = QLabel(f"{APP_NAME} v{APP_VERSION}")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_layout.addWidget(title)

        desc = QLabel(APP_DESCRIPTION)
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        title_layout.addWidget(desc)

        pledge = QLabel("Privacy Guarantee: DocuTools is fully offline. Your files never leave your computer.")
        pledge.setStyleSheet("color: #10b981; font-weight: 600; font-size: 11px; margin-top: 4px;")
        title_layout.addWidget(pledge)

        layout.addWidget(title_card)

        # License Section
        sec_label = QLabel("Third-Party Open-Source Credits & Licenses")
        sec_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        layout.addWidget(sec_label)

        self.license_browser = QTextBrowser()
        self.license_browser.setOpenExternalLinks(True)

        license_file = BASE_DIR / "THIRD_PARTY_LICENSES.md"
        if license_file.exists():
            content = license_file.read_text(encoding="utf-8")
            self.license_browser.setMarkdown(content)
        else:
            self.license_browser.setText("Third-party license file not found.")

        layout.addWidget(self.license_browser)
