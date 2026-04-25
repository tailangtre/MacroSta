"""Finnhub general financial news adapter.

Endpoint: /news?category=general — broad market/economy news.
We use this rather than per-symbol /company-news because we don't have
a ticker watchlist yet. Add /company-news later when we do.
"""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_unix

logger = logging.getLogger(__name__)

NAME = "finnhub"
URL = "https://finnhub.io/api/v1/news"


def enabled() -> bool:
    return bool(settings.FINNHUB_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "category": "general",
                "token": settings.FINNHUB_API_KEY,
            })
            resp.raise_for_status()
            for art in resp.json() or []:
                url = art.get("url") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("source") or "",
                    title=art.get("headline") or "",
                    description=art.get("summary") or "",
                    published_at=parse_unix(art.get("datetime")),
                ))
    except Exception as exc:
        logger.warning("finnhub fetch failed: %s", exc)
    return out
