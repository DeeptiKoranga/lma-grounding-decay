"""Extract monthly Indian basket prices from audited, cached PPAC snapshots.

Reuse the official collector's checksummed PDFs and the saved release archive.
Later file versions are excluded, rather than backdating their observations.
Partial coverage is explicit; this does not manufacture daily prices.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

from corpus.official import pdf_file_day
from corpus.series import Observation, validate_observations, write_csv
from schema import CORPUS_END, CORPUS_START

from .official import Release

ARCHIVE_URL = "https://ppac.gov.in/archives/reports"
SERIES_ID = "indian_basket_usd_bbl"


class ArchiveRows(HTMLParser):
    """Keep each download link beside its publisher-declared release date."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[list[str], list[str]]] = []
        self.links: list[str] = []
        self.dates: list[str] = []
        self.in_row = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.links, self.dates = [], []
        elif self.in_row and tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif self.in_row and tag == "td" and attrs.get("data-sort"):
            self.dates.append(attrs["data-sort"])

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.rows.append((self.links, self.dates))
            self.in_row = False


def check_archive(html: str, release: Release) -> None:
    page = ArchiveRows()
    page.feed(html)
    dates = [days for links, days in page.rows if release.url in links]
    if dates != [[release.published_at]]:
        raise ValueError("PPAC archive must link this PDF with one matching publication date")
    if release.publication_date_source != ARCHIVE_URL:
        raise ValueError("PPAC publication date must come from the audited archive")


def parse_prices(
    highlights: str, prices_table: str, *, month: int, year: int, released: date, url: str
) -> list[Observation]:
    """Match the basket sentence and cross-check its current month against table 25."""
    text = " ".join(highlights.split())
    value = r"(\d+(?:\.\d+)?)"
    period = r"([A-Za-z]+)['\u2019](\d{4})"
    pattern = (
        r"The Indian basket crude price averaged\s*\$"
        + value
        + r"/bbl during\s+"
        + period
        + r"\s+as against\s*\$"
        + value
        + r"/bbl during\s+"
        + period
        + r"\s+and\s*\$"
        + value
        + r"/bbl during\s+"
        + period
    )
    matches = re.findall(pattern, text, re.I)
    if len(matches) != 1:
        raise ValueError("expected one unambiguous Indian basket monthly-average sentence")
    current, name, y, previous, prev_name, prev_y, _, old_name, old_y = matches[0]
    prior_end = date(year, month, 1) - timedelta(days=1)
    if (name.casefold(), int(y)) != (calendar.month_name[month].casefold(), year):
        raise ValueError("basket sentence does not match the snapshot month")
    if (prev_name.casefold(), int(prev_y)) != (
        calendar.month_name[prior_end.month].casefold(),
        prior_end.year,
    ) or (old_name.casefold(), int(old_y)) != (name.casefold(), year - 1):
        raise ValueError("basket comparison periods do not match previous month/prior year")
    table = " ".join(prices_table.split())
    if not re.search(rf"\b{calendar.month_abbr[month]}-{str(year)[-2:]}\b", table):
        raise ValueError("price table does not identify the snapshot month")
    table_values = re.findall(
        r"Crude oil\s*\(Indian Basket\)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+" + value,
        table,
        re.I,
    )
    if len(table_values) != 1 or float(table_values[0]) != float(current):
        raise ValueError("basket highlight and monthly price table disagree")
    observations = []
    for on, amount in (
        (date(year, month, calendar.monthrange(year, month)[1]), current),
        (prior_end, previous),
    ):
        if CORPUS_START <= on <= CORPUS_END:
            row = Observation(
                on=on,
                value=amount,
                available_on=released,
                source_url=url,
                unit="USD per barrel",
            )
            if row.value <= 0:
                raise ValueError("Indian basket price must be positive")
            observations.append(row)
    return observations


def extract_snapshot(raw: bytes, release: Release) -> tuple[list[Observation], dict]:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("PPAC source is not a PDF")
    match = re.fullmatch(
        r"Snapshot of India's Oil and Gas Data, ([A-Za-z]+) (\d{4})", release.title
    )
    if not match or match[1] not in calendar.month_name:
        raise ValueError("snapshot title must identify a month and year")
    month, year = list(calendar.month_name).index(match[1]), int(match[2])
    released = date.fromisoformat(release.published_at)
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("PPAC PDF extraction requires the optional pymupdf package") from exc

    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if pdf.needs_pass or not 1 <= len(pdf) <= 100:
            raise ValueError("unexpected or encrypted PPAC PDF")
        metadata = pdf.metadata or {}
        versions = [
            stamp.date()
            for field in ("creationDate", "modDate")
            if (stamp := pdf_file_day(metadata.get(field, "")))
        ]
        if versions and max(versions) > released:
            raise ValueError("PDF file version is later than its listed release; original required")
        pages = [page.get_text(sort=True) for page in pdf]
    highlights = [
        (i + 1, text) for i, text in enumerate(pages) if "The Indian basket crude price" in text
    ]
    tables = [
        (i + 1, text)
        for i, text in enumerate(pages)
        if "Information on Prices, Taxes" in text and "Crude oil (Indian Basket)" in text
    ]
    if len(highlights) != 1 or len(tables) != 1:
        raise ValueError("expected one highlights page and one monthly price table")
    rows = parse_prices(
        highlights[0][1], tables[0][1], month=month, year=year, released=released, url=release.url
    )
    return rows, {
        "highlights_pdf_page": highlights[0][0],
        "prices_table_pdf_page": tables[0][0],
        "pdf_file_version_day": str(max(versions)) if versions else None,
        "observations": [row.model_dump(mode="json") for row in rows],
    }


def acquire_from_cache(
    *, manifest: Path, raw_root: Path, archive: Path, output: Path, report: Path
) -> dict:
    archive_raw = archive.read_bytes()
    archive_html = archive_raw.decode("utf-8")
    sources, excluded, observations = [], [], []
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("source") != "ppac" or not entry.get("title", "").startswith("Snapshot"):
            continue
        release = Release.model_validate(entry)
        try:
            check_archive(archive_html, release)
            key = hashlib.sha256(release.url.encode()).hexdigest()[:20]
            path = raw_root / f"{key}.pdf"
            metadata = json.loads((raw_root / f"{key}.meta.json").read_text())
            raw = path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            if metadata.get("sha256") != checksum or any(
                metadata.get(field) != value for field, value in release.model_dump().items()
            ):
                raise ValueError("cached PPAC identity/checksum does not match audited release")
            rows, details = extract_snapshot(raw, release)
            observations.extend(rows)
            sources.append(
                {**release.model_dump(), "raw_path": str(path), "sha256": checksum, **details}
            )
        except (ValueError, OSError, KeyError, RuntimeError) as exc:
            excluded.append({"url": release.url, "reason": str(exc)})
    observations = validate_observations(SERIES_ID, observations)
    missing_months = [
        f"2026-{month:02d}"
        for month in range(3, 10)
        if not any(row.on.year == 2026 and row.on.month == month for row in observations)
    ]
    summary = {
        "series_id": SERIES_ID,
        "definition": "PPAC Indian crude basket, monthly average, USD per barrel",
        "frequency": "monthly; cannot confirm an intramonth or daily threshold crossing",
        "availability": "archive publication date of the specific accepted PDF, including comparison months",
        "observations": len({row.on for row in observations}),
        "vintages": len(observations),
        "coverage_complete": not missing_months,
        "missing_observation_months": missing_months,
        "archive": {
            "url": ARCHIVE_URL,
            "raw_path": str(archive),
            "sha256": hashlib.sha256(archive_raw).hexdigest(),
        },
        "sources": sources,
        "excluded_sources": excluded,
        "limitation": "File metadata detects known later copies; it cannot prove an unchanged historical body.",
        "use": "move_confirmation_only",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n")
    if not observations:
        raise ValueError(f"no eligible Indian basket observations; inspect {report}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, series_id=SERIES_ID, records=observations)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("scripts/fetch/official_seeds.jsonl"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw/ppac"))
    parser.add_argument(
        "--archive", type=Path, default=Path("data/raw/ppac/acquisition_archive.html")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/series/indian_basket_usd_bbl.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("data/series/indian_basket_provenance.json")
    )
    args = parser.parse_args()
    try:
        result = acquire_from_cache(
            manifest=args.manifest,
            raw_root=args.raw,
            archive=args.archive,
            output=args.output,
            report=args.report,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in {"sources", "archive"}},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
