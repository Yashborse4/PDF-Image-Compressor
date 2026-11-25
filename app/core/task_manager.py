"""Central task manager coordinating asynchronous worker threads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.workers.background_worker import BackgroundWorker

logger = get_logger("task_manager")


class TaskManager(QObject):
    """Coordinates thread-pool execution and lifecycle of background workers."""

    _instance: TaskManager | None = None
    all_tasks_completed = Signal()

    def __init__(self, max_threads: int | None = None) -> None:
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()
        if max_threads:
            self.thread_pool.setMaxThreadCount(max_threads)
        self._active_workers: list[BackgroundWorker] = []
        logger.info("TaskManager initialized with %d max threads.", self.thread_pool.maxThreadCount())

    @classmethod
    def get_instance(cls) -> TaskManager:
        """Singleton accessor for TaskManager."""
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance

    def submit_task(
        self,
        task_fn: Callable[..., Any],
        *args: Any,
        on_progress: Callable[[int, str], None] | None = None,
        on_finished: Callable[[Any], None] | None = None,
        on_error: Callable[[str, str], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> BackgroundWorker:
        """Enqueue a callable onto the thread pool and attach signal listeners."""
        from app.workers.background_worker import BackgroundWorker

        worker = BackgroundWorker(task_fn, *args, **kwargs)

        if on_progress:
            worker.signals.progress.connect(on_progress)

        def _handle_finished(res: Any) -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if on_finished:
                on_finished(res)
            self._check_all_completed()

        def _handle_error(msg: str, tb: str) -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if on_error:
                on_error(msg, tb)
            self._check_all_completed()

        def _handle_cancelled() -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if on_cancelled:
                on_cancelled()
            self._check_all_completed()

        worker.signals.finished.connect(_handle_finished)
        worker.signals.error.connect(_handle_error)
        worker.signals.cancelled.connect(_handle_cancelled)

        self._active_workers.append(worker)
        self.thread_pool.start(worker)
        logger.debug("Submitted task. Active workers count: %d", len(self._active_workers))
        return worker

    def cancel_all(self) -> None:
        """Request immediate cancellation of all active background workers."""
        logger.info("Cancelling %d active workers.", len(self._active_workers))
        for worker in list(self._active_workers):
            worker.cancel()

    def _check_all_completed(self) -> None:
        """Emit all_tasks_completed signal when queue is empty."""
        if not self._active_workers:
            self.all_tasks_completed.emit()
