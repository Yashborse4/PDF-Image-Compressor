"""
Batch queue worker for multi-file processing pipelines.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class BatchWorkerSignals(QObject):
    """Signals for batch job execution."""
    started = Signal(int)                    # total items
    item_started = Signal(int, str)          # item index, item name
    item_progress = Signal(int, int, str)    # item index, item percent, message
    item_finished = Signal(int, object)      # item index, result
    item_error = Signal(int, str, str)       # item index, error, traceback
    all_finished = Signal(list)              # list of all results


class BatchWorker(QRunnable):
    """Executes a list of tasks sequentially in background thread."""

    def __init__(self, task_items: List[Any], process_fn: Callable[[Any, Callable[[int, str], None]], Any]):
        super().__init__()
        self.task_items = task_items
        self.process_fn = process_fn
        self.signals = BatchWorkerSignals()
        self.is_cancelled = False

    def cancel(self) -> None:
        self.is_cancelled = True

    @Slot()
    def run(self) -> None:
        total = len(self.task_items)
        self.signals.started.emit(total)
        all_results = []

        for idx, item in enumerate(self.task_items):
            if self.is_cancelled:
                break

            name = str(item)
            self.signals.item_started.emit(idx, name)

            def progress_cb(pct: int, msg: str = ""):
                self.signals.item_progress.emit(idx, pct, msg)

            try:
                res = self.process_fn(item, progress_cb)
                all_results.append(res)
                self.signals.item_finished.emit(idx, res)
            except Exception as e:
                tb = traceback.format_exc()
                err_dict = {"item": item, "error": str(e), "status": "failed"}
                all_results.append(err_dict)
                self.signals.item_error.emit(idx, str(e), tb)

        self.signals.all_finished.emit(all_results)
