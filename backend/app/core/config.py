"""
MacroScope — Configuration
All secrets come from environment variables / .env file.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── News API keys ───────────────────────────────────────────────
    # All optional — sources with missing keys are silently skipped.
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")          # newsapi.org      100/day
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")    # finnhub.io        60/min
    ALPHAVANTAGE_API_KEY: str = os.getenv("ALPHAVANTAGE_API_KEY", "")  # alphavantage.co  25/day
    MARKETAUX_API_KEY: str = os.getenv("MARKETAUX_API_KEY", "")        # marketaux.com   100/day
    POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY", "")            # polygon.io       5/min
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")                    # financialmodelingprep.com 250/day
    NEWSDATA_API_KEY: str = os.getenv("NEWSDATA_API_KEY", "")          # newsdata.io    200/day
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")                # gnews.io       100/day
    CURRENTS_API_KEY: str = os.getenv("CURRENTS_API_KEY", "")          # currentsapi.services 600/day

    # ── Pipeline cadence ────────────────────────────────────────────
    # Top-level scheduler interval. Per-source cadence is enforced separately
    # in the orchestrator (see SOURCE_INTERVALS_MINUTES) so we don't burn
    # a daily-quota source 24 times a day.
    NEWS_FETCH_INTERVAL_MINUTES: int = 30

    # Minimum minutes between calls per source. The orchestrator skips a
    # source if the last successful fetch is more recent than this.
    # Tuned to fit free-tier quotas with headroom.
    SOURCE_INTERVALS_MINUTES: dict = {
        "newsapi":      240,   # 100/day, 15 queries per cycle, fits at 6 cycles/day
        "finnhub":      30,    # 60/min, can be aggressive
        "alphavantage": 180,   # 25/day, very tight — 8 calls/day
        "marketaux":    60,    # 100/day
        "polygon":      60,    # 5/min, but daily limit on free
        "fmp":          60,    # 250/day
        "newsdata":     60,    # 200/day
        "gnews":        60,    # 100/day
        "currents":     30,    # 600/day, generous
        "rss":          15,    # unlimited but be polite
    }

    # HTTP timeout per source request (seconds).
    SOURCE_HTTP_TIMEOUT: int = 20

    # ── Groq ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")  # https://groq.com/ (free tier: 100 req/month)
    # Fast, free-tier available models: llama-3.3-70b-versatile (best),
    # llama-3.1-8b-instant (faster/cheaper), mixtral-8x7b-32768
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Database ────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./macroscope.db"

    # ── CORS ────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    # ── Geopolitical keywords for relevance filtering ───────────────
    # NewsAPI queries — keep short (1–3 words max). Long phrases return 0 results.
    NEWS_QUERIES: List[str] = [
        "war sanctions",
        "military conflict",
        "interest rates inflation",
        "central bank",
        "OPEC oil",
        "recession GDP",
        "geopolitical crisis",
        "trade tariffs",
        "currency forex",
        "semiconductor chips",
        "energy commodity",
        "nuclear threat",
        "stock market crash",
        "debt default",
        "drone strike",
    ]

    # Hard keyword filter — article must contain at least one of these
    RELEVANCE_KEYWORDS: List[str] = [
        "war", "conflict", "military", "sanctions", "missile",
        "inflation", "interest rate", "central bank", "fed", "ecb", "boj", "pboc",
        "opec", "oil", "crude", "gas", "energy",
        "recession", "gdp", "economic", "trade",
        "crisis", "geopolit", "tension", "coup", "protest",
        "tariff", "export", "import", "embargo",
        "currency", "devaluation", "forex",
        "semiconductor", "supply chain",
        "default", "debt", "sovereign",
        "nuclear", "drone", "airstrike",
        "commodity", "gold", "wheat", "copper",
    ]

    # Countries / regions we track
    TRACKED_COUNTRIES: List[str] = [
        "United States", "China", "Russia", "Ukraine", "Germany", "France",
        "United Kingdom", "Japan", "South Korea", "Taiwan", "Israel", "Iran",
        "Saudi Arabia", "India", "Brazil", "Turkey", "North Korea", "Pakistan",
        "EU", "NATO", "OPEC", "G7", "G20",
    ]

    # Maximum articles to process per fetch cycle (cost control)
    MAX_ARTICLES_PER_CYCLE: int = 100

    # Minimum relevance score (0–1) to keep an article
    MIN_RELEVANCE_SCORE: float = 0.15


settings = Settings()