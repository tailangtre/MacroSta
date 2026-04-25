"""Currents API adapter."""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "currents"
URL = "https://api.currentsapi.services/v1/latest-news"


def enabled() -> bool:
    return bool(settings.CURRENTS_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "language": "en",
                "category": "business",
                "apiKey": settings.CURRENTS_API_KEY,
            })
            resp.raise_for_status()
            for art in resp.json().get("news", []):
                url = art.get("url") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("author") or "",
                    title=art.get("title") or "",
                    description=art.get("description") or "",
                    published_at=parse_iso(art.get("published")),
                ))
    except Exception as exc:
        logger.warning("currents fetch failed: %s", exc)
    return out
