"""
Probe every news source adapter and print a one-line health summary plus
a sample article. Use this after adding API keys to confirm each source
actually returns data — a "0 articles" line almost always means a
field-name mismatch in the adapter, not a network problem.

Run from the backend/ directory:

    python -m tools.probe_sources              # probe all
    python -m tools.probe_sources finnhub      # probe one
    python -m tools.probe_sources -v           # also dump raw HTTP response
"""
import asyncio
import json
import sys
from datetime import datetime

from app.services.sources import ALL


def _fmt_date(d) -> str:
    if isinstance(d, datetime):
        return d.isoformat()
    return str(d)


async def probe(mod, verbose: bool) -> None:
    name = mod.NAME
    if not mod.enabled():
        print(f"  {name:14s} SKIP   (no key configured)")
        return
    try:
        articles = await mod.fetch()
    except Exception as exc:
        print(f"  {name:14s} ERROR  {type(exc).__name__}: {exc}")
        return

    count = len(articles)
    status = "OK   " if count > 0 else "EMPTY"
    print(f"  {name:14s} {status}  {count} articles")

    if verbose and articles:
        sample = dict(articles[0])
        sample["published_at"] = _fmt_date(sample.get("published_at"))
        # Trim long text for readability
        if sample.get("raw_description"):
            sample["raw_description"] = sample["raw_description"][:160] + "…"
        print(json.dumps(sample, indent=2, default=str))
        print()


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    targets = ALL
    if args:
        wanted = set(args)
        targets = [m for m in ALL if m.NAME in wanted]
        missing = wanted - {m.NAME for m in targets}
        if missing:
            print(f"Unknown source(s): {', '.join(missing)}")
            print(f"Available: {', '.join(m.NAME for m in ALL)}")
            sys.exit(1)

    print(f"Probing {len(targets)} source(s) — {datetime.now().isoformat(timespec='seconds')}")
    print("─" * 60)

    # Run sequentially so output is readable. Parallelism doesn't help when
    # the bottleneck is human eyeballs reading the report.
    for mod in targets:
        await probe(mod, verbose)

    print("─" * 60)
    print("Done. Hint: re-run with -v to see a sample article per source.")


if __name__ == "__main__":
    asyncio.run(main())
