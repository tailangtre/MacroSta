"""
News source adapters. Each module exposes:

    NAME: str                    # provider key (e.g. "finnhub")
    enabled() -> bool            # True if configured (key present)
    async fetch() -> list[dict]  # parsed articles in common schema

Common schema:
    {
        "url": str,
        "source_name": str,      # outlet (e.g. "Reuters")
        "provider": str,         # this source (e.g. "finnhub")
        "raw_title": str,
        "raw_description": str,
        "published_at": datetime (UTC),
    }
"""
from app.services.sources import (
    newsapi, finnhub, alphavantage, marketaux, polygon,
    fmp, newsdata, gnews, currents, rss,
)

ALL = [
    newsapi, finnhub, alphavantage, marketaux, polygon,
    fmp, newsdata, gnews, currents, rss,
]
