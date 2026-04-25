"""Marketaux adapter — multi-source aggregator with entity tagging."""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "marketaux"
URL = "https://api.marketaux.com/v1/news/all"


def enabled() -> bool:
    return bool(settings.MARKETAUX_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "language": "en",
                "filter_entities": "true",
                "limit": 50,
                "api_token": settings.MARKETAUX_API_KEY,
            })
            resp.raise_for_status()
            for art in resp.json().get("data", []):
                url = art.get("url") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("source") or "",
                    title=art.get("title") or "",
                    description=art.get("description") or art.get("snippet") or "",
                    published_at=parse_iso(art.get("published_at")),
                ))
    except Exception as exc:
        logger.warning("marketaux fetch failed: %s", exc)
    return out
