"""
Shared helpers for source adapters.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


def http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.SOURCE_HTTP_TIMEOUT, follow_redirects=True)


def parse_iso(value: Optional[str]) -> datetime:
    """Parse an ISO-8601 string with best-effort fallback to now()."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        s = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def parse_unix(value: Any) -> datetime:
    """Convert a unix timestamp (seconds) to a UTC datetime."""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def make_article(
    *,
    url: str,
    provider: str,
    source_name: str,
    title: str,
    description: str,
    published_at: datetime,
) -> Dict[str, Any]:
    return {
        "url": url,
        "provider": provider,
        "source_name": source_name or "",
        "raw_title": (title or "").strip(),
        "raw_description": (description or "").strip()[:2000],
        "published_at": published_at,
    }
