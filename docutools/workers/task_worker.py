"""
Background task worker system for DocuTools using QRunnable and QThreadPool.
Ensures zero UI freezing during heavy processing.
"""

from __future__ import annotations

import sys
import traceback
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Signals available from a running worker thread."""
    started = Signal()
    progress = Signal(int, str)  # percent (0-100), status message
    finished = Signal(object)    # result object/dict
    error = Signal(str, str)     # error message, traceback


class TaskWorker(QRunnable):
    """
    General-purpose worker thread runnable.
    Executes a callable function with optional args and kwargs in a QThreadPool.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        """Execute the worker function with signal reporting."""
        try:
            self.signals.started.emit()

            # If the target function accepts progress_callback, wire it up
            if "progress_callback" in self.fn.__code__.co_varnames:
                def on_progress(percent: int, msg: str = ""):
                    self.signals.progress.emit(percent, msg)
                self.kwargs["progress_callback"] = on_progress

            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(str(e), tb)
