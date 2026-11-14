"""
Dedicated History View for DocuTools.
Tracks operations, calculates cumulative storage savings, provides filtering and CSV export.
"""

from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from docutools.core.database import Database
from docutools.core.validator import format_file_size


class HistoryView(QWidget):
    """Activity history, storage analytics, and audit ledger."""

    def __init__(self, db: Database, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.all_records: List[Dict[str, Any]] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_heading = QLabel("Operation History & Analytics")
        lbl_heading.setProperty("class", "heading")
        lbl_sub = QLabel("Comprehensive record of all file conversions, compressions, and document tasks.")
        lbl_sub.setProperty("class", "subheading")
        title_box.addWidget(lbl_heading)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.refresh_history)
        header_row.addWidget(btn_refresh)

        btn_export = QPushButton("📤 Export CSV...")
        btn_export.clicked.connect(self._export_csv)
        header_row.addWidget(btn_export)

        btn_clear = QPushButton("Clear History")
        btn_clear.setProperty("class", "dangerButton")
        btn_clear.clicked.connect(self._clear_history)
        header_row.addWidget(btn_clear)

        main_layout.addLayout(header_row)

        # Summary Metrics Frame
        summary_frame = QFrame()
        summary_frame.setProperty("class", "cardFrame")
        sum_lay = QHBoxLayout(summary_frame)
        sum_lay.setContentsMargins(12, 10, 12, 10)

        self.lbl_stat_total = QLabel("Total Ops: 0")
        self.lbl_stat_saved = QLabel("Cumulative Storage Saved: 0 MB")
        self.lbl_stat_saved.setStyleSheet("font-weight: bold; color: #22c55e;")
        self.lbl_stat_success = QLabel("Success Rate: 100%")

        sum_lay.addWidget(self.lbl_stat_total)
        sum_lay.addStretch()
        sum_lay.addWidget(self.lbl_stat_saved)
        sum_lay.addStretch()
        sum_lay.addWidget(self.lbl_stat_success)

        main_layout.addWidget(summary_frame)

        # Filters Row
        filter_frame = QFrame()
        filter_frame.setProperty("class", "cardFrame")
        f_lay = QHBoxLayout(filter_frame)
        f_lay.setContentsMargins(8, 6, 8, 6)

        f_lay.addWidget(QLabel("Filter Module:"))
        self.combo_filter_mod = QComboBox()
        self.combo_filter_mod.addItems(["All Modules", "PDF Manager", "Document Studio", "Image Studio", "Conversion Center", "Batch Center"])
        self.combo_filter_mod.currentIndexChanged.connect(self._apply_filters)
        f_lay.addWidget(self.combo_filter_mod)

        f_lay.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter by action or file name...")
        self.txt_search.textChanged.connect(self._apply_filters)
        f_lay.addWidget(self.txt_search, stretch=1)

        main_layout.addWidget(filter_frame)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Module", "Action", "Output File", "Storage Saved", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table, stretch=1)

        self.refresh_history()

    def refresh_history(self) -> None:
        self.all_records = self.db.get_history(limit=500)
        self._apply_filters()

    def _apply_filters(self) -> None:
        selected_mod = self.combo_filter_mod.currentText()
        query = self.txt_search.text().strip().lower()

        filtered = []
        total_saved_bytes = 0
        success_count = 0

        for r in self.all_records:
            # Module check
            if selected_mod != "All Modules" and r["module"] != selected_mod:
                continue

            # Query check
            out_name = Path(r["output_file"]).name.lower() if r.get("output_file") else ""
            act_name = r["action"].lower()
            if query and (query not in out_name and query not in act_name):
                continue

            filtered.append(r)

            if r.get("initial_size") and r.get("final_size"):
                diff = r["initial_size"] - r["final_size"]
                if diff > 0:
                    total_saved_bytes += diff
            if r["status"] == "success":
                success_count += 1

        self.lbl_stat_total.setText(f"Total Ops: {len(filtered)}")
        self.lbl_stat_saved.setText(f"Cumulative Storage Saved: {format_file_size(total_saved_bytes)}")
        rate = (success_count / max(len(filtered), 1)) * 100
        self.lbl_stat_success.setText(f"Success Rate: {rate:.1f}%")

        self.table.setRowCount(len(filtered))
        for row_idx, row in enumerate(filtered):
            dt_str = datetime.datetime.fromtimestamp(row["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            item_time = QTableWidgetItem(dt_str)
            item_mod = QTableWidgetItem(row["module"])
            item_act = QTableWidgetItem(row["action"])
            item_out = QTableWidgetItem(Path(row["output_file"]).name if row["output_file"] else "-")
            if row["output_file"]:
                item_out.setToolTip(row["output_file"])

            savings_str = "-"
            if row.get("initial_size") and row.get("final_size"):
                diff = row["initial_size"] - row["final_size"]
                pct = (diff / row["initial_size"] * 100) if row["initial_size"] > 0 else 0
                savings_str = f"{format_file_size(diff)} ({pct:.1f}%)"
            item_sav = QTableWidgetItem(savings_str)

            item_status = QTableWidgetItem(row["status"].capitalize())
            if row["status"] == "success":
                item_status.setForeground(Qt.GlobalColor.green)
            else:
                item_status.setForeground(Qt.GlobalColor.red)

            self.table.setItem(row_idx, 0, item_time)
            self.table.setItem(row_idx, 1, item_mod)
            self.table.setItem(row_idx, 2, item_act)
            self.table.setItem(row_idx, 3, item_out)
            self.table.setItem(row_idx, 4, item_sav)
            self.table.setItem(row_idx, 5, item_status)

    def _export_csv(self) -> None:
        if not self.all_records:
            QMessageBox.information(self, "Export", "History is currently empty.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Export History CSV", "docutools_history.csv", "CSV Files (*.csv)")
        if not out_path:
            return

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Module", "Action", "Output File", "Initial Bytes", "Final Bytes", "Status"])
            for r in self.all_records:
                dt_str = datetime.datetime.fromtimestamp(r["created_at"]).isoformat()
                writer.writerow([
                    dt_str, r["module"], r["action"], r.get("output_file", ""),
                    r.get("initial_size", ""), r.get("final_size", ""), r["status"]
                ])

        QMessageBox.information(self, "Export Complete", f"History exported successfully to:\n{out_path}")

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History", "Are you sure you want to permanently clear all operation logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_history()
            self.refresh_history()
