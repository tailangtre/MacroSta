"""Alpha Vantage NEWS_SENTIMENT adapter.

Endpoint includes pre-scored sentiment per article and per ticker.
We capture the article-level sentiment; ticker-level sentiment is left
on the floor for now (would need its own column).

Free tier is brutally tight (25 calls/day) — orchestrator runs this
sparingly. Topics filter narrows to what we care about.
"""
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "alphavantage"
URL = "https://www.alphavantage.co/query"

# Topics: economy_macro, financial_markets, energy_transportation,
# economy_monetary, economy_fiscal, finance, technology, earnings, ipo, mergers_and_acquisitions
TOPICS = "economy_macro,financial_markets,economy_monetary"


def enabled() -> bool:
    return bool(settings.ALPHAVANTAGE_API_KEY)


def _parse_av_time(ts: str) -> str:
    """Alpha Vantage uses YYYYMMDDTHHMMSS, convert to ISO."""
    if not ts or len(ts) < 15:
        return ""
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T{ts[9:11]}:{ts[11:13]}:{ts[13:15]}Z"


async def fetch() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(URL, params={
                "function": "NEWS_SENTIMENT",
                "topics": TOPICS,
                "limit": 50,
                "sort": "LATEST",
                "apikey": settings.ALPHAVANTAGE_API_KEY,
            })
            resp.raise_for_status()
            data = resp.json()
            # Free-tier rate-limit responses come back as 200s with a "Note" field
            if "Note" in data or "Information" in data:
                logger.info("alphavantage rate-limited: %s",
                            data.get("Note") or data.get("Information"))
                return out
            for art in data.get("feed", []):
                url = art.get("url") or ""
                if not url:
                    continue
                out.append(make_article(
                    url=url,
                    provider=NAME,
                    source_name=art.get("source") or "",
                    title=art.get("title") or "",
                    description=art.get("summary") or "",
                    published_at=parse_iso(_parse_av_time(art.get("time_published", ""))),
                ))
    except Exception as exc:
        logger.warning("alphavantage fetch failed: %s", exc)
    return out
