"""Financial Modeling Prep — general news adapter."""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "fmp"
# Legacy /api/v3/stock_news is paid-only; /stable/news/general-latest is the
# free-tier replacement (capped history window).
URL = "https://financialmodelingprep.com/stable/news/general-latest"


def enabled() -> bool:
    return bool(settings.FMP_API_KEY)


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "page": 0,
                "limit": 50,
                "apikey": settings.FMP_API_KEY,
            })
            resp.raise_for_status()
            for art in resp.json() or []:
                url = art.get("url") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("publisher") or art.get("site") or "",
                    title=art.get("title") or "",
                    description=art.get("text") or "",
                    published_at=parse_iso(art.get("publishedDate")),
                ))
    except Exception as exc:
        logger.warning("fmp fetch failed: %s", exc)
    return out
