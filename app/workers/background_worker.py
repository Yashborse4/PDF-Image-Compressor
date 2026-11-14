"""Background worker infrastructure using PySide6 QRunnable and Qt signals."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.core.exceptions import TaskCancelledError
from app.core.logging import get_logger

logger = get_logger("worker")


class WorkerSignals(QObject):
    """Qt signals emitted by background workers to update the UI thread."""

    started = Signal()
    progress = Signal(int, str)  # (percentage: 0-100, message: str)
    finished = Signal(object)  # (result: Any)
    error = Signal(str, str)  # (error_title: str, detailed_traceback: str)
    cancelled = Signal()


class BackgroundWorker(QRunnable):
    """A generic, cancellable worker runnable executing tasks in QThreadPool."""

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False

        # If fn takes progress_callback or cancel_checker, inject them
        self.kwargs["progress_callback"] = self.report_progress
        self.kwargs["cancel_checker"] = self.is_cancelled

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self._is_cancelled = True
        logger.info("Worker cancel flag set.")

    def is_cancelled(self) -> bool:
        """Check whether task has been cancelled."""
        return self._is_cancelled

    def report_progress(self, percent: int, message: str = "") -> None:
        """Emit progress update safely."""
        if not self._is_cancelled:
            self.signals.progress.emit(max(0, min(100, percent)), message)

    @Slot()
    def run(self) -> None:
        """Execute the target function and emit appropriate signals."""
        self.signals.started.emit()
        try:
            if self._is_cancelled:
                self.signals.cancelled.emit()
                return

            result = self.fn(*self.args, **self.kwargs)

            if self._is_cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(result)

        except TaskCancelledError:
            logger.info("Worker caught TaskCancelledError.")
            self.signals.cancelled.emit()
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Worker error: %s\n%s", exc, tb)
            self.signals.error.emit(str(exc), tb)
