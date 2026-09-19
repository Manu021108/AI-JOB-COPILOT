"""Simple sliding-window rate limiting service.

A lightweight in-memory limiter is enough for the current single-instance
architecture. It is abstracted behind a class so it can be swapped for a
distributed implementation (Redis etc.) in a later phase without changing
call sites.
"""
import threading
import time


class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        timestamp = now if now is not None else time.monotonic()
        with self._lock:
            window_start = timestamp - self.window_seconds
            current = [t for t in self._records.get(key, []) if t > window_start]
            if len(current) >= self.max_requests:
                self._records[key] = current
                return False
            current.append(timestamp)
            self._records[key] = current
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._records.clear()
            else:
                self._records.pop(key, None)


url_import_limiter = RateLimiter()