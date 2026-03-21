from __future__ import annotations

import logging
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token bucket rate limiter using sliding window for Google Sheets API."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window (default 60).
            window_seconds: Time window in seconds (default 60.0).
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def _remove_expired(self) -> None:
        """Remove timestamps outside the current window (not thread-safe alone)."""
        cutoff = time.monotonic() - self._window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def acquire(self) -> None:
        """Block until a request slot is available, then acquire it."""
        while True:
            wait = self.wait_time()
            if wait <= 0:
                with self._lock:
                    self._timestamps.append(time.monotonic())
                return
            logger.warning(
                "Rate limit throttling",
                extra={"wait_seconds": wait, "window_seconds": self._window_seconds},
            )
            time.sleep(min(wait, 0.1))

    def try_acquire(self) -> bool:
        """Non-blocking acquire. Return True if slot available, False otherwise."""
        with self._lock:
            self._remove_expired()
            if len(self._timestamps) < self._max_requests:
                self._timestamps.append(time.monotonic())
                return True
            return False

    def wait_time(self) -> float:
        """Return seconds until next available slot (0.0 if available now)."""
        with self._lock:
            self._remove_expired()
            if len(self._timestamps) < self._max_requests:
                return 0.0
            oldest = self._timestamps[0]
            elapsed = time.monotonic() - oldest
            return max(0.0, self._window_seconds - elapsed)

    @property
    def available_tokens(self) -> int:
        """Return number of available request slots in current window."""
        with self._lock:
            self._remove_expired()
            return self._max_requests - len(self._timestamps)
