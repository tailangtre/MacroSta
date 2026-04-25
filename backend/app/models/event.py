"""
MacroScope — Event ORM model.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Source metadata ─────────────────────────────────────────────
    source_url: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Which API/feed delivered this article: "newsapi", "finnhub", "rss:yahoo", etc.
    # Distinct from source_name (the outlet, e.g. "Reuters") and useful for
    # debugging coverage gaps and weighting source quality later.
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    raw_title: Mapped[str] = mapped_column(Text)
    raw_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # ── LLM-enriched fields ─────────────────────────────────────────
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # "war" | "economy" | "politics"

    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    impact_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

    # JSON arrays / objects
    assets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # [{ symbol, direction, pct, reason }]

    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # ["war", "sanctions", …]

    # Deep analysis — generated alongside classification in the same LLM call
    # { summary, market_impact, risk_level, key_takeaway, asset_outlook: [...] }
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ── Deduplication ───────────────────────────────────────────────
    # SHA-1 of normalised title — catches same story with different URLs
    # (syndication, tracking params, www vs non-www, etc.)
    content_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    # ── Relevance ───────────────────────────────────────────────────
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "country": self.country,
            "lat": self.lat,
            "lng": self.lng,
            "title": self.title or self.raw_title,
            "summary": self.summary or self.raw_description or "",
            "category": self.category or "politics",
            "region": self.region or "Global",
            "timestamp": self.published_at.isoformat() + "Z",
            "assets": self.assets or [],
            "tags": self.tags or [],
            "impact_summary": self.impact_summary or "",
            "risk_level": self.risk_level or "MEDIUM",
            "source_url": self.source_url,
            "source_name": self.source_name or "",
            "provider": self.provider or "",
            "ai_analysis": self.ai_analysis or None,
        }