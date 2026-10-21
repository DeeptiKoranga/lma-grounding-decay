"""Acquire original MoSPI CPI vintages with dates and values read from each PDF.

Seven original releases published during March-September cover February-August
observations. September CPI was released in October and is omitted.
URLs were discovered in MoSPI's public latest-release index; source content is
validated rather than trusting filenames, a calendar, or publication schedules.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

from corpus.series import Observation, write_csv

from .client import Client
from .sources import Source

BASE = "https://mospi.gov.in/"
RELEASES = (
    (
        2,
        "uploads/latestReleases/latest_release_1773310539387_714ce3b5-4644-4aef-b2e3-64433640a9c3_Press_Release_of_CPI_February_2026.pdf",
    ),
    (
        3,
        "uploads/latestReleases/latest_release_1776075408775_60ad93d0-aedc-405b-864a-d1e965e7ba40_Press_Release_of_CPI_March_2026.pdf",
    ),
    (4, "uploads/PressRelease/CPI%20Press%20Release%20of%20April%202026.pdf"),
    (
        5,
        "uploads/latestReleases/latest_release_1781259853555_04875571-19f2-4830-9cad-3a1bfd5992e1_Press_Release_of_CPI_for_May_2026.pdf",
    ),
    (
        6,
        "uploads/latestReleases/latest_release_1783937698596_1013f1a1-3400-41aa-b4f4-5bbff10db7b7_Press_Release_of_CPI_for_June_2026.pdf",
    ),
    (
        7,
        "uploads/latestReleases/latest_release_1786529680747_3113661d-1a2b-4b9a-af06-b340193ef9a0_Press_Release_CPI_July_2026.pdf",
    ),
    (
        8,
        "uploads/latestReleases/latest_release_1789381904344_6c792dcf-8a9f-4fca-93d3-99d833bdb358_Press_Release_of_CPI_for_August_2026.pdf",
    ),
)


def parse_cpi_text(text: str, *, source_url: str, month: int) -> Observation:
    """Read combined YoY headline inflation and the release's own dated header."""
    text = " ".join(text.split())
    dated = re.findall(r"\bDated\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})", text, re.I)
    if len(set(dated)) != 1:
        raise ValueError("CPI release must state one unambiguous Dated header")
    day, release_month, year = dated[0]
    try:
        released = datetime.strptime(f"{day} {release_month} {year}", "%d %B %Y").date()
    except ValueError as exc:
        raise ValueError("invalid CPI release date") from exc
    name = calendar.month_name[month]
    title = f"CONSUMER PRICE INDEX ON BASE 2024=100 FOR {name}, 2026"
    if title.casefold() not in text.casefold():
        raise ValueError("CPI release title does not match the requested observation/base")
    pattern = (
        r"Year-on-year inflation rate based on All India Consumer Price Index\s*\(CPI\)\s*"
        r"with base year 2024 for the month of "
        + name
        + r",?\s+2026 over "
        + name
        + r",?\s+2025 is\s+(-?\d+(?:\.\d+)?)\s*%\s*\(Provisional\)"
    )
    values = re.findall(pattern, text, re.I)
    if len(values) != 1:
        raise ValueError("expected exactly one combined headline YoY provisional CPI value")
    return Observation(
        on=date(2026, month, calendar.monthrange(2026, month)[1]),
        value=values[0],
        available_on=released,
        source_url=source_url,
        unit="percent year on year",
    )


def extract_pdf_text(raw: bytes) -> str:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("CPI source is not a PDF")
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("CPI PDF extraction requires the optional pymupdf package") from exc
    with pymupdf.open(stream=raw, filetype="pdf") as document:
        if not 1 <= len(document) <= 30:
            raise ValueError("unexpected CPI release page count")
        # Header and national headline appear on page one, avoiding conflicting
        # dates/values from annexures and historical tables.
        return document[0].get_text(sort=True)


def acquire(client: Client, *, raw_root: Path, output: Path, report: Path) -> dict:
    raw_root.mkdir(parents=True, exist_ok=True)
    observations, sources, failures = [], [], []
    for month, path in RELEASES:
        url = BASE + path
        target = raw_root / f"cpi_2026_{month:02d}.pdf"
        sidecar = target.with_suffix(".meta.json")
        try:
            if target.is_file() and sidecar.is_file():
                raw = target.read_bytes()
                metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                if (
                    metadata.get("url") != url
                    or metadata.get("sha256") != hashlib.sha256(raw).hexdigest()
                ):
                    raise ValueError("cached CPI source metadata/checksum mismatch")
            else:
                response = client.get(url)
                if response.content_type != "application/pdf":
                    raise ValueError(f"CPI release is not application/pdf: {response.content_type}")
                raw = response.body
                metadata = {
                    "url": url,
                    "fetched_at": datetime.now(UTC).isoformat(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
                target.write_bytes(raw)
                sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            observation = parse_cpi_text(extract_pdf_text(raw), source_url=url, month=month)
            if observation.available_on > date(2026, 9, 30):
                raise ValueError("CPI original was unavailable by the frozen corpus end")
            observations.append(observation)
            sources.append(
                {
                    **metadata,
                    "raw_path": str(target),
                    **observation.model_dump(mode="json"),
                    "status": "original_provisional",
                    "base": "2024=100",
                    "definition": "All India combined general CPI, year-on-year inflation",
                }
            )
        except (ValueError, OSError, RuntimeError) as exc:
            failures.append({"url": url, "month": month, "error": str(exc)})
    summary = {
        "series_id": "cpi_headline_yoy",
        "observations": len(observations),
        "expected_observations": len(RELEASES),
        "complete": len(observations) == len(RELEASES),
        "sources": sources,
        "failures": failures,
        "use": "move_confirmation_only",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if not summary["complete"]:
        raise ValueError(f"CPI acquisition incomplete; inspect {report}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, series_id="cpi_headline_yoy", records=observations)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw/series/cpi"))
    parser.add_argument("--output", type=Path, default=Path("data/series/cpi_headline_yoy.csv"))
    parser.add_argument("--report", type=Path, default=Path("data/series/cpi_provenance.json"))
    args = parser.parse_args()
    source = Source("mospi", BASE.rstrip("/"), ("mospi.gov.in", "www.mospi.gov.in"))
    try:
        result = acquire(
            Client(source, delay=2, max_requests=16),
            raw_root=args.raw,
            output=args.output,
            report=args.report,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in result.items() if key != "sources"}, indent=2))


if __name__ == "__main__":
    main()
