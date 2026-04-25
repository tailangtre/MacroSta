"""NewsAPI.org adapter."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "newsapi"
URL = "https://newsapi.org/v2/everything"


def enabled() -> bool:
    return bool(settings.NEWS_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    # Free tier accepts only YYYY-MM-DD for `from` (full ISO is paid-only;
    # using it on free silently returns 0 results).
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")

    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    async with http_client() as client:
        for query in settings.NEWS_QUERIES:
            try:
                resp = await client.get(
                    URL,
                    params={
                        "q": query,
                        "from": from_date,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20,
                        "apiKey": settings.NEWS_API_KEY,
                    },
                )
                resp.raise_for_status()
                for art in resp.json().get("articles", []):
                    url = art.get("url") or ""
                    title = art.get("title")
                    if not url or url in seen or title in (None, "[Removed]"):
                        continue
                    seen.add(url)
                    out.append(make_article(
                        url=url,
                        provider=NAME,
                        source_name=(art.get("source") or {}).get("name", ""),
                        title=title or "",
                        description=art.get("description") or art.get("content") or "",
                        published_at=parse_iso(art.get("publishedAt")),
                    ))
            except Exception as exc:
                logger.warning("newsapi query '%s' failed: %s", query, exc)
    return out
