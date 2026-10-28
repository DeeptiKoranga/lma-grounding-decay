"""Bounded, resumable news collection. Raw payloads and audit logs stay out of git."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from corpus import parse_html

from .client import Client
from .discovery import canonical_url, discover
from .sources import SOURCES

MACRO = re.compile(
    r"\b(brent|crude|rupee|inflation|RBI|monetary|repo rate|bond yield|g-sec|"
    r"GDP|CPI|MOSPI|PPAC|fiscal|trade deficit|current account|forex|foreign portfolio|"
    r"oil import|ATF|aviation turbine fuel|fuel price|government borrowing)\b",
    re.IGNORECASE,
)


def collect(client, urls: list[str], output: Path, *, max_articles: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    # Article URLs are deduplicated independently of discovery order.
    attempted = 0
    for url in sorted({canonical_url(u) for u in urls}):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        payload = output / f"{key}.html"
        sidecar = output / f"{key}.meta.json"
        event = {"url": url, "at": datetime.now(UTC).isoformat()}
        meta = None
        try:
            if not client.source.accepts(url):
                raise ValueError("URL is outside this publisher")
            if payload.exists() and sidecar.exists():
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    raise ValueError("cached metadata must be a JSON object")
                raw = payload.read_bytes()
                if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                    raise ValueError("cached raw payload checksum mismatch")
                counts["cached"] += 1
            else:
                if attempted >= max_articles:
                    break
                attempted += 1
                response = client.get(url)
                if response.content_type not in {"text/html", "application/xhtml+xml"}:
                    raise ValueError(f"not HTML: {response.content_type}")
                raw = response.body
                meta = {
                    "source": client.source.name,
                    "url": canonical_url(response.url),
                    "requested_url": url,
                    "fetched_at": event["at"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "charset": response.charset,
                    "content_type": response.content_type,
                }
                payload.write_bytes(raw)
                sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
                counts["downloaded"] += 1
            doc = parse_html(
                raw.decode(meta["charset"], errors="replace"),
                source=client.source.name,
                url=meta["url"],
            )
            if not MACRO.search(doc.title + " " + doc.text):
                raise ValueError("no macroeconomic topic match")
            event.update(status="accepted", doc_id=doc.doc_id, published_at=str(doc.published_at))
        except (ValueError, OSError, LookupError, KeyError, TypeError) as exc:
            event.update(status="rejected", reason=str(exc))
        if isinstance(meta, dict):
            meta["accepted"] = event["status"] == "accepted"
            meta["rejection_reason"] = event.get("reason")
            sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        counts[event["status"]] += 1
        with (output / "collection_log.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(event) + "\n")
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=SOURCES, required=True)
    parser.add_argument(
        "--url", action="append", default=[], help="Explicit article URL (repeatable)"
    )
    parser.add_argument("--feed", action="append", default=[], help="Archive sitemap/RSS/Atom URL")
    parser.add_argument("--url-file", type=Path, help="Previously discovered URL JSONL")
    parser.add_argument(
        "--macro-urls-only",
        action="store_true",
        help="Prioritise URLs mentioning a macro topic; final acceptance still uses page text/date",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Save discovered URLs without fetching articles",
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-feeds", type=int, default=8)
    parser.add_argument("--max-articles", type=int, default=25)
    parser.add_argument("--max-requests", type=int, default=80)
    parser.add_argument("--delay", type=float, default=2)
    args = parser.parse_args()
    if args.max_feeds < 0 or args.max_articles < 1:
        parser.error("max-feeds must be nonnegative and max-articles positive")
    source = SOURCES[args.source]
    client = Client(source, delay=args.delay, max_requests=args.max_requests)
    failures = []
    urls = args.url
    if args.url_file:
        urls += [
            json.loads(line)["url"]
            for line in args.url_file.read_text().splitlines()
            if line.strip()
        ]
    try:
        if args.feed or not urls:
            urls += discover(
                client,
                args.feed or client.sitemaps(),
                max_feeds=args.max_feeds,
                on_error=lambda url, error: failures.append({"url": url, "error": error}),
            )
    except (OSError, ValueError) as exc:
        failures.append({"url": source.root, "error": str(exc)})
    source_output = args.raw / source.name
    source_output.mkdir(parents=True, exist_ok=True)
    (source_output / "discovered_urls.jsonl").write_text(
        "".join(json.dumps({"url": url}) + "\n" for url in sorted(set(urls))), encoding="utf-8"
    )
    candidates = [url for url in urls if MACRO.search(url)] if args.macro_urls_only else urls
    counts = (
        {}
        if args.discover_only
        else collect(client, candidates, source_output, max_articles=args.max_articles)
    )
    summary = {
        "source": source.name,
        "at": datetime.now(UTC).isoformat(),
        "discovered_urls": len(set(urls)),
        "candidate_urls": len(set(candidates)),
        "requests": client.requests,
        "counts": counts,
        "discovery_failures": failures,
    }
    (args.raw / source.name / "last_collection.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
