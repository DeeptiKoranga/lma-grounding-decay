"""Collect reproducible, bounded archive batches without alphabetical-topic bias.

URLs are discovered from publisher sitemaps. Archive dates schedule requests;
only publisher publication metadata can admit an article to the corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from .client import Client
from .collect import collect
from .discovery import archive_month, discover, parse_feed
from .sources import SOURCES

TOPICS = re.compile(
    r"brent|crude|rupee|inflation|monetary|repo[- ]rate|bond[- ]yield|g-sec|"
    r"cpi|fiscal[- ]deficit|trade[- ]deficit|current[- ]account|forex|foreign[- ]portfolio|"
    r"oil[- ]import|atf[- ]price|aviation[- ]turbine|fuel[- ]price|government[- ]borrowing",
    re.IGNORECASE,
)


def select_candidates(urls, *, limit: int, seed: str) -> list[str]:
    """Hash sampling is stable and avoids always collecting one alphabetic section."""
    candidates = {url for url in urls if TOPICS.search(url)}
    return sorted(candidates, key=lambda url: hashlib.sha256((seed + url).encode()).digest())[
        :limit
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", choices=["economic_times", "businessline", "mint"], required=True
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--per-month", type=int, default=145, help="Maximum candidate attempts per month"
    )
    parser.add_argument("--max-feeds", type=int, default=230)
    parser.add_argument("--max-requests", type=int, default=1500)
    parser.add_argument("--delay", type=float, default=2)
    parser.add_argument(
        "--workers",
        type=int,
        choices=[1, 2, 4],
        default=1,
        help="At most four overlapping response reads; request pacing is shared",
    )
    parser.add_argument("--seed", default="lma-corpus-v1")
    parser.add_argument("--months", nargs="+", type=int, default=list(range(3, 10)))
    args = parser.parse_args()
    if args.per_month < 1 or not set(args.months) <= set(range(3, 10)):
        parser.error("per-month must be positive and months must be in March-September")
    client = Client(SOURCES[args.source], delay=args.delay, max_requests=args.max_requests)
    output = args.raw / args.source
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    if args.source == "economic_times":
        index = "https://economictimes.indiatimes.com/etstatic/sitemaps/et/news/sitemap-index.xml"
        feeds, _ = parse_feed(client.get(index))
    else:
        feeds = client.sitemaps()
        if args.source == "businessline":
            feeds = [feed for feed in feeds if "/archive" in feed]
            nested, _ = parse_feed(client.get(feeds[0]))
            feeds = nested
    total = Counter()
    summaries = []
    for month in args.months:
        matching = [
            feed
            for feed in feeds
            if (stamp := archive_month(feed)) and stamp.year == 2026 and stamp.month == month
        ]
        if not matching and args.source == "mint":
            matching = feeds
        cache = output / f"archive-2026-{month:02d}-urls.jsonl"
        if cache.exists():
            urls = [
                json.loads(line)["url"] for line in cache.read_text().splitlines() if line.strip()
            ]
        else:
            urls = discover(
                client,
                matching,
                max_feeds=args.max_feeds,
                on_error=lambda url, error: failures.append({"url": url, "error": error}),
            )
            cache.write_text("".join(json.dumps({"url": url}) + "\n" for url in urls))
        candidates = select_candidates(urls, limit=len(urls), seed=args.seed + f"-{month}")
        # Apply the attempt limit after excluding complete caches, so restarting
        # a bounded batch advances through the archive. An orphaned sidecar is
        # not a completed download. The rebuild rechecks cached payload hashes.
        pending = [
            url
            for url in candidates
            if not (
                (output / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".meta.json")).is_file()
                and (output / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".html")).is_file()
            )
        ][: args.per_month]
        chosen = pending
        print(
            json.dumps(
                {
                    "phase": "discovered",
                    "month": month,
                    "urls": len(urls),
                    "candidates": len(candidates),
                    "pending": len(pending),
                    "selected": len(chosen),
                }
            ),
            flush=True,
        )
        counts = Counter()
        for offset in range(0, len(chosen), 25):
            batch = chosen[offset : offset + 25]
            if args.workers == 1:
                counts.update(collect(client, batch, output, max_articles=len(batch)))
            else:
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    results = pool.map(
                        lambda url: collect(client, [url], output, max_articles=1), batch
                    )
                    for result in results:
                        counts.update(result)
            print(
                json.dumps(
                    {
                        "phase": "collected",
                        "month": month,
                        "attempted": min(offset + 25, len(chosen)),
                        "counts": dict(counts),
                        "requests": client.requests,
                    }
                ),
                flush=True,
            )
            if client.requests >= client.max_requests:
                break
        total.update(counts)
        summaries.append(
            {
                "month": month,
                "discovered": len(urls),
                "selected": len(chosen),
                "counts": dict(counts),
            }
        )
        summary = {
            "source": args.source,
            "at": datetime.now(UTC).isoformat(),
            "months": summaries,
            "counts": dict(total),
            "requests": client.requests,
            "failures": failures,
        }
        (output / "batch_collection.json").write_text(json.dumps(summary, indent=2) + "\n")
        if client.requests >= client.max_requests:
            break


if __name__ == "__main__":
    main()
