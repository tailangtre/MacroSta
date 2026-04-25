"""
MacroScope — Multi-source news orchestrator.

Calls every enabled source adapter in parallel, deduplicates the merged
result by URL and content hash, and returns a list of parsed articles ready
for the relevance filter.

Per-source cadence is enforced here (not in the scheduler) so that a single
30-minute pipeline tick can poll Tiingo (every cycle) while skipping
Mediastack (only twice a day, has a 100/month free quota).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.core.config import settings
from app.services.sources import ALL as ALL_SOURCES
from app.utils.hashing import content_hash

logger = logging.getLogger(__name__)

# In-memory record of when each source was last polled successfully.
# Resets on process restart, which is fine — worst case we hit one source
# slightly more often than we'd like once after a deploy.
_last_fetch: Dict[str, datetime] = {}


def _ready(name: str) -> bool:
    interval_min = settings.SOURCE_INTERVALS_MINUTES.get(name, 60)
    last = _last_fetch.get(name)
    if last is None:
        return True
    return datetime.now(timezone.utc) - last >= timedelta(minutes=interval_min)


async def _run_source(mod) -> List[Dict[str, Any]]:
    name = mod.NAME
    if not mod.enabled():
        logger.debug("source %s skipped: not configured", name)
        return []
    if not _ready(name):
        logger.debug("source %s skipped: within rate window", name)
        return []
    try:
        articles = await mod.fetch()
        _last_fetch[name] = datetime.now(timezone.utc)
        logger.info("source %s: %d articles", name, len(articles))
        return articles
    except Exception:
        logger.exception("source %s: unhandled error", name)
        return []


async def fetch_articles() -> List[Dict[str, Any]]:
    """Fetch from every enabled, ready source in parallel; dedup the merged list."""
    chunks = await asyncio.gather(*[_run_source(s) for s in ALL_SOURCES])

    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    out: List[Dict[str, Any]] = []
    for chunk in chunks:
        for art in chunk:
            url = art.get("url", "")
            if not url or url in seen_urls:
                continue
            h = content_hash(art.get("raw_title", ""), art.get("raw_description", ""))
            if h in seen_hashes:
                # Same story under a different URL (syndication, aggregator rewrite).
                continue
            art["content_hash"] = h
            seen_urls.add(url)
            seen_hashes.add(h)
            out.append(art)

    logger.info("orchestrator: %d unique articles after cross-source dedup", len(out))
    return out


def parse_article(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Pass-through: adapters already return the canonical schema.

    Kept as a function so the rest of the pipeline doesn't need to know that
    parsing now happens inside each adapter. If we ever need a post-hoc
    normalization step (e.g. strip HTML), it goes here.
    """
    raw.setdefault("content_hash",
                   content_hash(raw.get("raw_title", ""), raw.get("raw_description", "")))
    return raw
