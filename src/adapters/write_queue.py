"""Threading-based write queue for serializing Google Sheets writes."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class WriteOp:
    """Single write operation to queue."""

    sheet_name: str
    operation: Literal["append", "update"]
    data: list[list[str]]
    range_notation: str = ""
    callback: Callable[[], None] | None = field(default=None)


class WriteQueueWorker:
    """Thread-safe write queue worker for serialized Google Sheets writes."""

    _SENTINEL: None = None

    def __init__(self, executor: Callable[[WriteOp], None]) -> None:
        """Initialize worker with executor callback.

        Args:
            executor: Callback that executes a WriteOp (e.g., calls gspread).
        """
        self._executor = executor
        self._queue: queue.Queue[WriteOp | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start the worker thread."""
        self._thread.start()
        logger.debug("WriteQueueWorker started")

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully shutdown worker thread.

        Args:
            timeout: Max seconds to wait for thread termination.
        """
        self._queue.put(self._SENTINEL)
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning("WriteQueueWorker did not terminate within timeout")

    def submit(self, op: WriteOp) -> None:
        """Submit a write operation (non-blocking).

        Args:
            op: WriteOp to enqueue.
        """
        self._queue.put(op)

    @property
    def pending(self) -> int:
        """Return approximate number of pending operations."""
        return self._queue.qsize()

    @property
    def is_alive(self) -> bool:
        """Return True if worker thread is alive."""
        return self._thread.is_alive()

    def _run(self) -> None:
        """Worker loop: dequeue and execute writes."""
        while True:
            try:
                op = self._queue.get()
                if op is None:
                    break
                self._executor(op)
                if op.callback:
                    op.callback()
            except Exception:
                logger.error("WriteQueueWorker error", exc_info=True)
