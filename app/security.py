"""API key check + simple per-key rate limiting.

Protects your Anthropic bill: without the right X-API-Key header,
no photos ever reach the AI.
"""
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

WINDOW_SECONDS = 3600
_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def require_api_key(key: str | None = Security(api_key_header)) -> str:
    expected = os.getenv("SERVICE_API_KEY")
    if not expected:
        raise HTTPException(503, "Server is missing SERVICE_API_KEY")
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing API key")
    _check_rate_limit(key)
    return key


def _check_rate_limit(key: str) -> None:
    limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "20"))
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        while hits and now - hits[0] > WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            retry = int(WINDOW_SECONDS - (now - hits[0])) + 1
            raise HTTPException(429, "Rate limit reached, try again later",
                                headers={"Retry-After": str(retry)})
        hits.append(now)


def reset_rate_limits() -> None:
    """Used by tests."""
    with _lock:
        _hits.clear()
