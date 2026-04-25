"""
Run the news pipeline once and print a summary.

Mirrors tools/probe_sources.py but exercises the full chain end-to-end:
  fetch → parse → relevance filter → DB dedup → LLM enrich → save.

Run from backend/:

    python -m tools.run_pipeline              # full run
    python -m tools.run_pipeline --dry-run    # stop before LLM + DB writes
    python -m tools.run_pipeline --limit 5    # cap to 5 articles (cost control)
"""
import argparse
import asyncio
import json
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import init_db
from app.services.llm_enricher import enrich_article
from app.services.news_fetcher import fetch_articles, parse_article
from app.services.pipeline import _get_existing_urls_and_hashes
from app.services.relevance_filter import score_article
from app.services.storage import save_event

# Quiet httpx/httpcore/aiosqlite chatter; keep our own INFO logs.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
for noisy in ("httpx", "httpcore", "aiosqlite"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# Match the production semaphore so we exercise the same concurrency.
_LLM_SEMAPHORE = asyncio.Semaphore(3)


async def _enrich(article):
    async with _LLM_SEMAPHORE:
        return await enrich_article(article)


def _line(label: str, count: int, total: int | None = None) -> str:
    if total is not None and total > 0:
        pct = (count / total) * 100
        return f"  {label:14s} {count:6d}   ({pct:5.1f}% of {total})"
    return f"  {label:14s} {count:6d}"


async def run(dry_run: bool, limit: int | None) -> None:
    mode = "dry-run" if dry_run else "run"
    print(f"Pipeline {mode} — {datetime.now().isoformat(timespec='seconds')}")
    print("─" * 60)

    # FastAPI lifespan does this on server startup; the CLI bypasses that.
    await init_db()

    raw = await fetch_articles()
    print(_line("fetched", len(raw)))

    parsed = [parse_article(a) for a in raw]

    # Mirror filter_articles() but expose both pre-cap and post-cap counts so
    # we can tell whether the threshold or the cap is the real bottleneck.
    threshold = settings.MIN_RELEVANCE_SCORE
    cap = settings.MAX_ARTICLES_PER_CYCLE
    passed: list = []
    for art in parsed:
        s = score_article(art)
        if s >= threshold:
            art["relevance_score"] = s
            passed.append(art)
    passed.sort(key=lambda a: a["relevance_score"], reverse=True)
    relevant = passed[:cap]
    print(_line(f"passed (≥{threshold})", len(passed), len(parsed)))
    print(_line(f"kept (cap={cap})", len(relevant), len(passed)))

    urls, hashes = await _get_existing_urls_and_hashes()
    new_articles = [
        a for a in relevant
        if a["url"] not in urls and a.get("content_hash") not in hashes
    ]
    print(_line("new", len(new_articles), len(relevant)))

    if limit and len(new_articles) > limit:
        new_articles = new_articles[:limit]
        print(f"  (capped to first {limit})")

    if dry_run:
        print("─" * 60)
        print(f"Would enrich + save {len(new_articles)} articles.")
        if new_articles:
            sample = dict(new_articles[0])
            sample["published_at"] = str(sample.get("published_at"))
            print("Sample article:")
            print(json.dumps(sample, indent=2, default=str))
        return

    # Full run
    tasks = [_enrich(a) for a in new_articles]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    enriched = [r for r in results if r is not None]
    print(_line("enriched", len(enriched), len(new_articles)))

    saved = 0
    for art in enriched:
        if await save_event(art):
            saved += 1
    print(_line("saved", saved))
    print("─" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the news pipeline once.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip LLM enrichment and DB writes.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap the number of new articles processed (cost control).")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
