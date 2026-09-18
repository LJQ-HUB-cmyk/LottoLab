"""In-process per-IP rate limiting for POST endpoints (defense in depth).

Cloudflare /reverse-proxy limits stay primary; this guard also protects
self-hosted deployments. State is per process: on serverless platforms each
instance keeps its own budget, so treat this as a backstop, not a quota.
"""

import time
from collections import deque
from threading import Lock

from fastapi import Request


class PostRateLimiter:
    """Sliding-window counter per client key using a monotonic clock."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allowed(self, key: str, now: float | None = None) -> bool:
        if self.per_minute <= 0:
            return True
        moment = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= moment - 60.0:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(moment)
            if len(self._hits) > 10000:
                self._hits = {k: v for k, v in self._hits.items() if v}
            return True


def client_ip(request: Request) -> str:
    """Best-effort client key: leftmost X-Forwarded-For, else the peer address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"
