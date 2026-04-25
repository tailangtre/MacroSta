"""
MacroScope — Storage service.
Persists enriched events to the database, deduplicating by source URL.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.event import Event

logger = logging.getLogger(__name__)


async def save_event(article: Dict[str, Any]) -> bool:
    """
    Save an enriched article as an Event.
    Returns True if inserted, False if already existed.
    """
    url = article.get("url", "")
    if not url:
        return False

    async with AsyncSessionLocal() as session:
        # Dedup check
        existing = await session.scalar(select(Event).where(Event.source_url == url))
        if existing:
            return False

        published_at = article.get("published_at")
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now(timezone.utc)
        if not isinstance(published_at, datetime):
            published_at = datetime.now(timezone.utc)

        event = Event(
            source_url=url,
            source_name=article.get("source_name"),
            provider=article.get("provider"),
            raw_title=article.get("raw_title", ""),
            raw_description=article.get("raw_description"),
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc),
            content_hash=article.get("content_hash"),
            # LLM-enriched
            title=article.get("title"),
            summary=article.get("summary"),
            category=article.get("category"),
            country=article.get("country"),
            region=article.get("region"),
            lat=article.get("lat"),
            lng=article.get("lng"),
            impact_summary=article.get("impact_summary"),
            risk_level=article.get("risk_level"),
            assets=article.get("assets"),
            tags=article.get("tags"),
            ai_analysis=article.get("ai_analysis"),
            relevance_score=article.get("relevance_score", 0.0),
        )
        session.add(event)
        await session.commit()
        logger.info("Saved event: %s", event.title or event.raw_title)
        return True


async def get_recent_events(
    session: AsyncSession,
    limit: int = 50,
    category: str | None = None,
    region: str | None = None,
    age_days: int | None = None,
) -> List[Event]:
    """Return the most recent processed events, with optional filters."""
    from sqlalchemy import and_, desc
    from datetime import timedelta

    conditions = [Event.relevance_score > 0]
    if category:
        conditions.append(Event.category == category)
    if region:
        conditions.append(Event.region == region)
    if age_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=age_days)
        conditions.append(Event.published_at >= cutoff)

    stmt = (
        select(Event)
        .where(and_(*conditions))
        .order_by(desc(Event.published_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_event_by_id(session: AsyncSession, event_id: int) -> Event | None:
    return await session.get(Event, event_id)