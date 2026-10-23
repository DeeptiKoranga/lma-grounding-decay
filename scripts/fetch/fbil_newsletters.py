"""Audit cached FBIL newsletter yield candidates; never import unverified vintages.

The public /publications listing identifies media assets and upload timestamps.
Upload time does not establish when the newsletter was published. Candidates
therefore remain outside SeriesStore until publication and benchmark identity
are verified. This module performs no network requests.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

from corpus.official import pdf_file_day

LISTING_URL = "https://www.fbil.org.in/publications"


def parse_yield_table(text: str, *, month: int, year: int) -> dict:
    text = " ".join(text.split())
    heading = "10-year Sovereign Bond Yield of Major Economies"
    if text.count(heading) != 1:
        raise ValueError("expected one sovereign-yield table")
    table = text.split(heading, 1)[1]
    name, short = calendar.month_name[month], calendar.month_abbr[month]
    header = re.search(r"Yield \(%\) \*(\w+) (\d{4})", table)
    footnote = re.search(r"\*(\w+) (\d{4}) - Month [\u2013-] end closing level", table)
    for label, found in [("header", header), ("footnote", footnote)]:
        if not found or found[1] not in {name, short} or int(found[2]) != year:
            raise ValueError(f"sovereign-yield {label} conflicts with observation month")
    table = table[: footnote.start()]
    rows = re.findall(r"\bIndia (\d+\.\d+) (\d+\.\d+) (\d+\.\d+) (\w+ \d{2}, \d{4})", table)
    if len(rows) != 1:
        raise ValueError("expected one identified Indian security row")
    current, prior, coupon, maturity = rows[0]
    if not all(0 < float(v) < 25 for v in (current, prior, coupon)):
        raise ValueError("yield/coupon outside audit bounds")
    return {
        "observation_on": str(date(year, month, calendar.monthrange(year, month)[1])),
        "value": float(current),
        "prior_year_comparison": float(prior),
        "coupon_percent": float(coupon),
        "maturity": datetime.strptime(maturity, "%B %d, %Y").date().isoformat(),
        "unit": "percent",
        "measure": "month-end closing yield as printed; source credits LSEG",
    }


def audit(*, listing: Path, raw: Path, report: Path) -> dict:
    import pymupdf

    payload = json.loads(listing.read_text())
    descriptions = next(n for n in payload[0]["NewsLetter"] if n["Label"] == "2026")["Description"]
    candidates, excluded = [], []
    for entry in descriptions:
        issue = int(entry["IssueNumber"])
        if not 86 <= issue <= 90:
            continue
        asset = entry["Pdf"][0]
        path = raw / f"{issue}.pdf"
        identity = {"issue": issue, "url": "https://www.fbil.org.in" + asset["url"]}
        try:
            meta = json.loads(path.with_suffix(".meta.json").read_text())
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if meta["url"] != identity["url"] or meta["asset"] != asset:
                raise ValueError("cached asset identity differs from public listing")
            if meta["sha256"] != digest:
                raise ValueError("cached PDF checksum mismatch")
            created = datetime.fromisoformat(asset["created_at"].replace("Z", "+00:00"))
            if asset["updated_at"] != asset["created_at"]:
                raise ValueError("media asset has a later update timestamp")
            with pymupdf.open(stream=data, filetype="pdf") as document:
                if any(
                    (day := pdf_file_day(document.metadata.get(key)))
                    and day.date() > created.date()
                    for key in ("creationDate", "modDate")
                ):
                    raise ValueError("PDF file version postdates asset upload")
                pages = [
                    (i + 1, p.get_text())
                    for i, p in enumerate(document)
                    if "10-year Sovereign Bond Yield of Major Economies" in p.get_text()
                ]
                if len(pages) != 1:
                    raise ValueError("expected one sovereign-yield page")
                page, text = pages[0]
                values = parse_yield_table(text, month=issue - 83, year=2026)
            candidates.append(
                {
                    **identity,
                    **values,
                    "pdf_sha256": digest,
                    "page": page,
                    "asset_created_at": asset["created_at"],
                    "available_on": None,
                    "accepted_for_historical_use": False,
                }
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            excluded.append({**identity, "reason": str(exc)})
    result = {
        "series_id": "gsec_10y_pct",
        "accepted_for_historical_use": False,
        "canonical_observations_added": 0,
        "listing_url": LISTING_URL,
        "listing_sha256": hashlib.sha256(listing.read_bytes()).hexdigest(),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "excluded": excluded,
        "remaining_checks": [
            "Media upload timestamps are not verified newsletter publication dates.",
            "Verify the reported coupon/maturity against the historical benchmark roll calendar.",
            "Monthly closes cannot confirm daily threshold crossings or episode dates.",
            "July has conflicting header/footnote months; August/September originals are absent.",
            "Average YTM and par-yield tables are different measures and were not substituted.",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--listing", type=Path, default=Path("data/raw/series/fbil/publications.json")
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw/series/fbil/newsletters"))
    parser.add_argument("--report", type=Path, default=Path("reports/gsec_acquisition_review.json"))
    args = parser.parse_args()
    result = audit(listing=args.listing, raw=args.raw, report=args.report)
    print(
        json.dumps({"candidates": result["candidate_count"], "excluded": len(result["excluded"])})
    )


if __name__ == "__main__":
    main()
