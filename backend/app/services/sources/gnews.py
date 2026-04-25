"""GNews adapter."""
import asyncio
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "gnews"
URL = "https://gnews.io/api/v4/top-headlines"


def enabled() -> bool:
    return bool(settings.GNEWS_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # GNews splits topics; pull business + world to cover macro/geopolitical.
    # Free tier is 1 req/sec, so space the calls and isolate failures so a
    # second-call rate-limit doesn't discard the first call's articles.
    async with http_client() as client:
        for i, topic in enumerate(("business", "world")):
            if i:
                await asyncio.sleep(1.1)
            try:
                resp = await client.get(URL, params={
                    "topic": topic,
                    "lang": "en",
                    "max": 25,
                    "apikey": settings.GNEWS_API_KEY,
                })
                resp.raise_for_status()
                for art in resp.json().get("articles", []):
                    url = art.get("url") or ""
                    if not url:
                        continue
                    out.append(make_article(
                        url=url,
                        provider=NAME,
                        source_name=(art.get("source") or {}).get("name", ""),
                        title=art.get("title") or "",
                        description=art.get("description") or art.get("content") or "",
                        published_at=parse_iso(art.get("publishedAt")),
                    ))
            except Exception as exc:
                logger.warning("gnews %s fetch failed: %s", topic, exc)
    return out
