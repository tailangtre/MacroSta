"""NewsData.io adapter — broad business news."""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "newsdata"
URL = "https://newsdata.io/api/1/news"


def enabled() -> bool:
    return bool(settings.NEWSDATA_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "apikey": settings.NEWSDATA_API_KEY,
                "language": "en",
                "category": "business,politics,world",
            })
            resp.raise_for_status()
            for art in resp.json().get("results", []):
                url = art.get("link") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("source_id") or "",
                    title=art.get("title") or "",
                    description=art.get("description") or art.get("content") or "",
                    published_at=parse_iso(art.get("pubDate")),
                ))
    except Exception as exc:
        logger.warning("newsdata fetch failed: %s", exc)
    return out
