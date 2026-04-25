"""Polygon.io news adapter."""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "polygon"
URL = "https://api.polygon.io/v2/reference/news"


def enabled() -> bool:
    return bool(settings.POLYGON_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "order": "desc",
                "limit": 50,
                "sort": "published_utc",
                "apiKey": settings.POLYGON_API_KEY,
            })
            resp.raise_for_status()
            for art in resp.json().get("results", []):
                url = art.get("article_url") or ""
                if not url:
                    continue
                pub = (art.get("publisher") or {}).get("name", "")
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=pub,
                    title=art.get("title") or "",
                    description=art.get("description") or "",
                    published_at=parse_iso(art.get("published_utc")),
                ))
    except Exception as exc:
        logger.warning("polygon fetch failed: %s", exc)
    return out
