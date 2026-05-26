import time
from collections import deque
from threading import Lock


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        if self._limit <= 0:
            return True

        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self._limit:
                return False

            hits.append(now)
            return True
