"""RSS / Atom feed adapter — covers all no-API-key sources.

Includes Reddit (post StockTwits/Reddit-API-policy changes, RSS is the path
of least resistance), Yahoo Finance, MarketWatch, Seeking Alpha, the Federal
Reserve press feed, and SEC EDGAR's recent 8-K filings.

Each entry's `provider` is namespaced (e.g. "rss:reddit_wsb") so you can
slice by feed in the DB.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser

from app.services.sources.base import http_client, make_article, parse_iso

logger = logging.getLogger(__name__)

NAME = "rss"

# (provider_suffix, source_name, feed_url)
FEEDS: list[tuple[str, str, str]] = [
    ("reddit_wsb",      "r/wallstreetbets", "https://www.reddit.com/r/wallstreetbets/.rss"),
    ("reddit_stocks",   "r/stocks",         "https://www.reddit.com/r/stocks/.rss"),
    ("reddit_investing","r/investing",      "https://www.reddit.com/r/investing/.rss"),
    ("yahoo_finance",   "Yahoo Finance",    "https://finance.yahoo.com/news/rssindex"),
    ("marketwatch",     "MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("seekingalpha",    "Seeking Alpha",    "https://seekingalpha.com/market_currents.xml"),
    ("fed_press",       "Federal Reserve",  "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("sec_8k",          "SEC EDGAR 8-K",    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=include&count=40&output=atom"),
]

# Reddit + SEC reject default httpx UA — set something benign.
HEADERS = {"User-Agent": "MacroScope/1.0 (news aggregator)"}


def enabled() -> bool:
    return True  # always on, no key required


def _entry_published(entry) -> datetime:
    """Best-effort extraction of an entry's publish time."""
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            return parse_iso(val)
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


async def _fetch_one(suffix: str, source_name: str, feed_url: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    try:
        async with http_client() as client:
            resp = await client.get(feed_url, headers=HEADERS)
            resp.raise_for_status()
            text = resp.text
        # feedparser is sync but very fast; offload to a thread to avoid
        # blocking the event loop on big feeds.
        feed = await asyncio.to_thread(feedparser.parse, text)
        for entry in feed.entries[:50]:
            url = entry.get("link") or ""
            title = entry.get("title") or ""
            if not url or not title:
                continue
            description = entry.get("summary") or entry.get("description") or ""
            items.append(make_article(
                url=url,
                provider=f"{NAME}:{suffix}",
                source_name=source_name,
                title=title,
                description=description,
                published_at=_entry_published(entry),
            ))
    except Exception as exc:
        logger.warning("rss feed %s failed: %s", suffix, exc)
    return items


async def fetch() -> List[Dict[str, Any]]:
    results = await asyncio.gather(*[_fetch_one(*f) for f in FEEDS], return_exceptions=False)
    flat: List[Dict[str, Any]] = []
    for chunk in results:
        flat.extend(chunk)
    return flat
