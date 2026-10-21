"""Collect curated RBI/MOSPI/PPAC/PIB releases, retaining publication provenance.

Usage: python -m scripts.fetch.official --manifest releases.jsonl
Each row: source, url, title, published_at, publication_date_source (release page URL).
Review the date on that page before adding a row; do not use PDF metadata dates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from corpus.official import parse_official
from corpus.parser import publication_time
from schema import CORPUS_END, CORPUS_START

from .client import Client
from .sources import Source

OFFICIAL_SOURCES = {
    "rbi": Source(
        "rbi",
        "https://www.rbi.org.in",
        ("www.rbi.org.in", "rbi.org.in", "rbidocs.rbi.org.in", "bulletin.rbi.org.in"),
    ),
    "mospi": Source("mospi", "https://www.mospi.gov.in", ("www.mospi.gov.in", "mospi.gov.in")),
    "ppac": Source("ppac", "https://ppac.gov.in", ("ppac.gov.in", "www.ppac.gov.in")),
    "pib": Source(
        "pib", "https://www.pib.gov.in", ("www.pib.gov.in", "pib.gov.in", "static.pib.gov.in")
    ),
}


class Release(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    url: str
    title: str = Field(min_length=1)
    published_at: str
    publication_date_source: str

    @field_validator("title")
    @classmethod
    def _title_is_nonblank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("release title must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_release(self) -> Self:
        source = OFFICIAL_SOURCES.get(self.source)
        if source is None:
            raise ValueError("unknown official publisher")
        if not source.accepts(self.url) or not source.accepts(self.publication_date_source):
            raise ValueError("document and date-source URLs must belong to the official publisher")
        if not CORPUS_START <= publication_time(self.published_at).date() <= CORPUS_END:
            raise ValueError("release date is outside the frozen corpus window")
        return self


def collect_releases(
    releases: list[Release],
    output: Path,
    *,
    max_documents: int = 25,
    client_factory=Client,
    delay: float = 2,
    max_requests: int = 80,
) -> dict:
    if max_documents < 1:
        raise ValueError("max_documents must be positive")
    if max_requests < 1 or delay < 0 or not math.isfinite(delay):
        raise ValueError("max_requests must be positive and delay finite and nonnegative")
    unique = {}
    for release in releases:
        key = (release.source, release.url)
        if key in unique and unique[key] != release:
            raise ValueError(f"conflicting release metadata for {release.url}")
        unique[key] = release
    clients = {}
    counts: Counter = Counter()
    attempted = 0
    for release in sorted(unique.values(), key=lambda r: (r.source, r.url)):
        directory = output / release.source
        directory.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(release.url.encode()).hexdigest()[:20]
        sidecar = directory / f"{key}.meta.json"
        event = {"url": release.url, "at": datetime.now(UTC).isoformat()}
        meta = None
        try:
            if sidecar.exists():
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                extension = ".pdf" if meta["content_type"] == "application/pdf" else ".html"
                raw = (directory / f"{key}{extension}").read_bytes()
                if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                    raise ValueError("cached raw payload checksum mismatch")
                if any(meta.get(field) != value for field, value in release.model_dump().items()):
                    raise ValueError("release metadata changed; review and remove stale cache")
                counts["cached"] += 1
            else:
                if attempted >= max_documents:
                    break
                attempted += 1
                if release.source not in clients:
                    clients[release.source] = client_factory(
                        OFFICIAL_SOURCES[release.source], delay=delay, max_requests=max_requests
                    )
                response = clients[release.source].get(release.url)
                if response.content_type not in {
                    "application/pdf",
                    "text/html",
                    "application/xhtml+xml",
                }:
                    raise ValueError(f"unsupported release content type: {response.content_type}")
                raw = response.body
                meta = {
                    **release.model_dump(),
                    "fetched_url": response.url,
                    "fetched_at": event["at"],
                    "content_type": response.content_type,
                    "charset": response.charset,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "source_kind": "official",
                }
                extension = ".pdf" if response.content_type == "application/pdf" else ".html"
                (directory / f"{key}{extension}").write_bytes(raw)
                sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
                counts["downloaded"] += 1
            doc = parse_official(
                raw,
                source=release.source,
                url=release.url,
                title=release.title,
                published_at=release.published_at,
                content_type=meta["content_type"],
                charset=meta.get("charset", "utf-8"),
            )
            event.update(status="accepted", doc_id=doc.doc_id)
        except (ValueError, OSError, KeyError, LookupError, TypeError) as exc:
            event.update(status="rejected", reason=str(exc))
        if isinstance(meta, dict):
            meta.update(
                accepted=event["status"] == "accepted", rejection_reason=event.get("reason")
            )
            sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        counts[event["status"]] += 1
        with (directory / "collection_log.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(event) + "\n")
    return {"counts": dict(counts), "requests": sum(c.requests for c in clients.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-documents", type=int, default=25)
    parser.add_argument("--max-requests", type=int, default=80, help="Per publisher")
    parser.add_argument("--delay", type=float, default=2)
    args = parser.parse_args()
    try:
        releases = []
        for number, line in enumerate(args.manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                releases.append(Release.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"{args.manifest}:{number}: invalid release: {exc}") from exc
        summary = collect_releases(
            releases,
            args.raw,
            max_documents=args.max_documents,
            delay=args.delay,
            max_requests=args.max_requests,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.raw.mkdir(parents=True, exist_ok=True)
    (args.raw / "official_collection.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
