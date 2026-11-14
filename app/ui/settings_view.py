"""Settings and preferences view for DocuTools."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import Settings


class SettingsView(QWidget):
    """View to view and modify user preferences."""

    theme_changed = Signal(str)  # 'dark' or 'light'

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = Settings.get_instance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Title
        title = QLabel("Settings & Preferences")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        # Settings Form Card
        form_card = QFrame()
        form_card.setProperty("card", "true")
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(16)

        row = 0

        # Theme
        theme_lbl = QLabel("Application Theme:")
        theme_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Theme", "Light Theme"])
        current_theme = self.settings.get("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form_layout.addWidget(theme_lbl, row, 0)
        form_layout.addWidget(self.theme_combo, row, 1)
        row += 1

        # Default Output Directory
        out_lbl = QLabel("Default Output Directory:")
        out_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        out_row = QHBoxLayout()
        self.out_input = QLineEdit(self.settings.get("default_output_dir", str(Path.home() / "Documents")))
        self.out_input.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.out_input)
        out_row.addWidget(browse_btn)
        form_layout.addWidget(out_lbl, row, 0)
        form_layout.addLayout(out_row, row, 1)
        row += 1

        # Open Output Folder
        self.open_folder_chk = QCheckBox("Automatically open destination folder upon task completion")
        self.open_folder_chk.setChecked(self.settings.get("open_output_folder_after_process", True))
        self.open_folder_chk.stateChanged.connect(
            lambda s: self.settings.set("open_output_folder_after_process", bool(s))
        )
        form_layout.addWidget(self.open_folder_chk, row, 0, 1, 2)
        row += 1

        # PDF Compression Preset
        pdf_preset_lbl = QLabel("Default PDF Compression Mode:")
        pdf_preset_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.pdf_preset_combo = QComboBox()
        self.pdf_preset_combo.addItems([
            "Recommended (Lossless stream + 150 DPI downsample)",
            "Lossless Only (No image quality reduction)",
            "Maximum Compression (High downsampling, 96 DPI)",
        ])
        preset_map = {"recommended": 0, "lossless": 1, "high": 2}
        self.pdf_preset_combo.setCurrentIndex(preset_map.get(self.settings.get("pdf_compression_preset", "recommended"), 0))
        self.pdf_preset_combo.currentIndexChanged.connect(self._on_pdf_preset_changed)
        form_layout.addWidget(pdf_preset_lbl, row, 0)
        form_layout.addWidget(self.pdf_preset_combo, row, 1)
        row += 1

        # Image Quality
        img_q_lbl = QLabel("Default Image Quality (1-100):")
        img_q_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.img_q_spin = QSpinBox()
        self.img_q_spin.setRange(10, 100)
        self.img_q_spin.setValue(self.settings.get("image_compression_quality", 80))
        self.img_q_spin.valueChanged.connect(
            lambda v: self.settings.set("image_compression_quality", v)
        )
        form_layout.addWidget(img_q_lbl, row, 0)
        form_layout.addWidget(self.img_q_spin, row, 1)
        row += 1

        layout.addWidget(form_card)

        # Danger zone / Maintenance
        actions_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset All to Defaults")
        reset_btn.setProperty("variant", "flat")
        reset_btn.clicked.connect(self._reset_defaults)
        actions_layout.addWidget(reset_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)
        layout.addStretch()

    def _browse_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Select Default Output Folder", self.out_input.text())
        if chosen:
            self.out_input.setText(chosen)
            self.settings.set("default_output_dir", chosen)

    def _on_theme_changed(self, index: int) -> None:
        theme = "dark" if index == 0 else "light"
        self.settings.set("theme", theme)
        self.theme_changed.emit(theme)

    def _on_pdf_preset_changed(self, index: int) -> None:
        presets = ["recommended", "lossless", "high"]
        self.settings.set("pdf_compression_preset", presets[index])

    def _reset_defaults(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all preferences back to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.settings.reset_to_defaults()
            self.theme_combo.setCurrentIndex(0)
            self.out_input.setText(self.settings.get("default_output_dir"))
            self.open_folder_chk.setChecked(True)
            self.pdf_preset_combo.setCurrentIndex(0)
            self.img_q_spin.setValue(80)
            self.theme_changed.emit("dark")
