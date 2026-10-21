"""Acquire public FBIL USD/INR reference rates with their actual display dates.

The unauthenticated public data endpoint returns both observation and display
timestamps. Website HTML availability is independent of this read-only API.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import ssl
import time
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from corpus.series import Observation, validate_observations, write_csv

BASE = "https://www.fbil.org.in/wasdm/refrates/fetchfiltered"


def parse_reference_rates(
    payload: list[dict], *, url: str, start: date, end: date
) -> list[Observation]:
    if not isinstance(payload, list):
        raise ValueError("FBIL reference-rate response must be a list")
    observations = []
    for record in payload:
        if not isinstance(record, dict):
            raise ValueError("FBIL rate entry must be an object")
        if record.get("subProdName") != "INR / 1 USD":
            continue
        on = datetime.fromisoformat(record["processRunDate"]).date()
        available = datetime.fromisoformat(record["displayTime"]).date()
        if not start <= on <= end:
            raise ValueError("FBIL returned a reference rate outside the requested range")
        row = Observation(
            on=on, available_on=available, value=record["rate"], source_url=url, unit="INR per USD"
        )
        if row.value <= 0:
            raise ValueError("FBIL USD/INR reference rate must be positive")
        observations.append(row)
    if not observations:
        raise ValueError("FBIL response contains no USD/INR reference rates")
    return list(validate_observations("inr_usd", observations))


def acquire(*, raw: Path, output: Path, report: Path, months=tuple(range(3, 10))) -> dict:
    if not months or not set(months) <= set(range(3, 10)):
        raise ValueError("months must be within March-September 2026")
    raw.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        pass
    else:
        context.load_verify_locations(certifi.where())
    observations, sources, failures = [], [], []
    for month in months:
        start = date(2026, month, 1)
        end = date(2026, month, calendar.monthrange(2026, month)[1])
        url = (
            BASE
            + "?"
            + urlencode(
                {
                    "fromDate": f"2026-{month}-1",
                    "toDate": f"2026-{month}-{end.day}",
                    "authenticated": "false",
                }
            )
        )
        path = raw / f"reference_rates_2026_{month:02d}.json"
        metadata_path = path.with_suffix(".meta.json")
        try:
            if path.exists() and metadata_path.exists():
                payload = path.read_bytes()
                metadata = json.loads(metadata_path.read_text())
                if (
                    metadata["url"] != url
                    or metadata["sha256"] != hashlib.sha256(payload).hexdigest()
                ):
                    raise ValueError("FBIL cached response identity/checksum mismatch")
            else:
                request = Request(
                    url,
                    headers={
                        "User-Agent": "LmaGroundingResearch/0.1",
                        "Accept": "application/json",
                    },
                )
                with urlopen(request, context=context, timeout=30) as response:
                    payload = response.read(4_000_001)
                if len(payload) > 4_000_000:
                    raise ValueError("FBIL response exceeds 4 MB")
                metadata = {
                    "url": url,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "fetched_at": datetime.now(UTC).isoformat(),
                    "bytes": len(payload),
                }
                path.write_bytes(payload)
                metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
                time.sleep(2)
            rows = parse_reference_rates(json.loads(payload), url=url, start=start, end=end)
            observations.extend(rows)
            sources.append(
                {
                    **metadata,
                    "observations": len(rows),
                    "start": str(rows[0].on),
                    "end": str(rows[-1].on),
                }
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failures.append({"url": url, "error": str(exc)})
    result = {
        "series_id": "inr_usd",
        "observations": len(observations),
        "complete": not failures,
        "sources": sources,
        "failures": failures,
        "definition": "FBIL daily INR per 1 USD reference rate, not market close",
        "availability": "displayTime date provided by FBIL API; observation uses processRunDate",
        "missing_days": "omitted; no holiday filling or interpolation",
        "use": "move_confirmation_only",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    if failures:
        raise ValueError(f"FBIL acquisition incomplete; inspect {report}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, series_id="inr_usd", records=observations)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw/series/fbil"))
    parser.add_argument("--output", type=Path, default=Path("data/series/inr_usd.csv"))
    parser.add_argument("--report", type=Path, default=Path("data/series/inr_provenance.json"))
    args = parser.parse_args()
    try:
        result = acquire(raw=args.raw, output=args.output, report=args.report)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in result.items() if key != "sources"}, indent=2))


if __name__ == "__main__":
    main()
