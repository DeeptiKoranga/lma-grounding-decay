"""Collect original WPI and core-industry PDFs linked by the government archive.

Publication dates come from each PDF's embargo advisory, never from filenames
or the observation month named in an archive link.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from corpus.official import parse_official
from schema import CORPUS_END, CORPUS_START

from .client import Client
from .official import OFFICIAL_SOURCES, Release

ARCHIVES = (
    "https://eaindustry.nic.in/wpi_press_release_archive.asp",
    "https://eaindustry.nic.in/ici_press_release_archive.asp",
)
DATE = re.compile(
    r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s*,?\s*(20\d{2})\b",
    re.IGNORECASE,
)


def embargo_date(text: str) -> str:
    header = " ".join(text.split())[:1100]
    if "embargo" not in header.casefold():
        raise ValueError("PDF has no readable embargo advisory; date needs manual review")
    matches = DATE.findall(header)
    if not matches:
        raise ValueError("PDF embargo date could not be read")
    day, month, year = matches[0]
    stamp = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
    if not CORPUS_START <= stamp <= CORPUS_END:
        raise ValueError("PDF embargo date is outside the corpus window")
    return str(stamp)


class ArchiveLinks(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url, self.links = url, set()

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")
        # Metadata/methodology documents have different date semantics.
        if (
            tag == "a"
            and "2026" in href
            and href.lower().endswith(".pdf")
            and "meta" not in href.lower()
            and (
                "wpi_press_release" in href.lower()
                or "ici" in href.lower()
                or "/ipr_2026" in href.lower()
            )
        ):
            self.links.add(urljoin(self.url, href))


def main():
    import pymupdf

    output = Path("data/raw/eaindustry")
    output.mkdir(parents=True, exist_ok=True)
    client = Client(OFFICIAL_SOURCES["eaindustry"], max_requests=25)
    urls, failures, seeds = {}, [], []
    for index, archive in enumerate(ARCHIVES):
        response = client.get(archive)
        (output / f"archive_{index}.html").write_bytes(response.body)
        parser = ArchiveLinks(archive)
        parser.feed(response.body.decode(response.charset))
        urls.update(dict.fromkeys(parser.links, archive))
    for url, archive in sorted(urls.items()):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        payload = output / f"{key}.pdf"
        sidecar = output / f"{key}.meta.json"
        try:
            if payload.exists() and sidecar.exists():
                raw = payload.read_bytes()
                prior = json.loads(sidecar.read_text())
                if prior["sha256"] != hashlib.sha256(raw).hexdigest():
                    raise ValueError("cached PDF checksum mismatch")
            else:
                response = client.get(url)
                raw = response.body
            if not raw.startswith(b"%PDF-"):
                raise ValueError("archive link did not return a PDF")
            with pymupdf.open(stream=raw, filetype="pdf") as pdf:
                first_page = pdf[0].get_text(sort=True)
            published = embargo_date(first_page)
            kind = "WPI/PPI" if "wpi_press" in url else "Index of Core Industries"
            release = Release(
                source="eaindustry",
                url=url,
                title=f"{kind} official release published {published}",
                published_at=published,
                publication_date_source=url,
            )
            document = parse_official(
                raw,
                source=release.source,
                url=url,
                title=release.title,
                published_at=published,
                content_type="application/pdf",
            )
            metadata = {
                **release.model_dump(),
                "fetched_url": url,
                "fetched_at": datetime.now(UTC).isoformat(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_type": "application/pdf",
                "charset": "utf-8",
                "source_kind": "official",
                "archive_url": archive,
                "date_evidence": "PDF first-page embargo advisory",
                "accepted": True,
                "rejection_reason": None,
                "doc_id": document.doc_id,
            }
            payload.write_bytes(raw)
            sidecar.write_text(json.dumps(metadata, indent=2) + "\n")
            seeds.append(release.model_dump())
            print(json.dumps({"accepted": url, "published_at": published}), flush=True)
        except (ValueError, OSError, KeyError) as exc:
            failures.append({"url": url, "error": str(exc)})
    manifest = Path("scripts/fetch/official_seeds.jsonl")
    existing = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    known = {row["url"] for row in existing}
    manifest.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in existing + [row for row in seeds if row["url"] not in known]
        )
    )
    (output / "acquisition_summary.json").write_text(
        json.dumps({"accepted": len(seeds), "failures": failures}, indent=2) + "\n"
    )
    print(json.dumps({"accepted": len(seeds), "failures": failures}, indent=2))


if __name__ == "__main__":
    main()
