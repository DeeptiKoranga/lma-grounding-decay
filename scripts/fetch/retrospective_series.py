"""Import separately captured historical snapshots without inventing old vintages.

These files are retrospective data for move checks, outside the default agent
store. A capture date is a known availability upper bound, not a historical
publication date. Preserve the original point-in-time series byte for byte.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from corpus.series import Observation, validate_observations, write_csv

from .cdsl_series import ARCHIVE_URL, FORM_URL, parse_month

START, END = date(2026, 3, 1), date(2026, 9, 30)
INDIA = ZoneInfo("Asia/Kolkata")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_day(metadata: dict) -> date:
    value = metadata.get("checked_at") or metadata.get("fetched_at")
    when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("capture timestamp must have an explicit timezone")
    return when.astimezone(INDIA).date()


def checked_source(raw: Path, meta: Path) -> tuple[bytes, dict]:
    metadata = json.loads(meta.read_text())
    payload = raw.read_bytes()
    if metadata.get("sha256") != hashlib.sha256(payload).hexdigest():
        raise ValueError("retrospective raw source checksum mismatch")
    if capture_day(metadata) < END:
        raise ValueError(
            "this backfill expects a post-window capture, not an invented historical vintage"
        )
    return payload, metadata


def brent_rows(payload: bytes, metadata: dict) -> list[Observation]:
    chart = json.loads(payload)["chart"]
    if chart.get("error") or len(chart["result"]) != 1:
        raise ValueError("invalid Yahoo chart response")
    result = chart["result"][0]
    identity = result["meta"]
    if any(
        identity.get(k) != v
        for k, v in {
            "symbol": "BZ=F",
            "currency": "USD",
            "instrumentType": "FUTURE",
            "exchangeName": "NYM",
        }.items()
    ):
        raise ValueError("Brent history must be the identified NYMEX financial futures series")
    if identity.get("priceHint") != 2:
        raise ValueError("unexpected Brent price precision")
    times = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    adjusted = result["indicators"].get("adjclose", [{"adjclose": closes}])[0]["adjclose"]
    if not len(times) == len(closes) == len(adjusted):
        raise ValueError("Brent date/value arrays are misaligned")
    zone = ZoneInfo(identity["exchangeTimezoneName"])
    rows = []
    for timestamp, value, comparison in zip(times, closes, adjusted, strict=True):
        on = datetime.fromtimestamp(timestamp, UTC).astimezone(zone).date()
        if not START <= on <= END:
            raise ValueError("Brent history contains an out-of-window trading day")
        if value is None:
            continue
        if (
            not math.isfinite(value)
            or value <= 0
            or comparison is None
            or abs(value - comparison) > 1e-6
        ):
            raise ValueError("invalid or adjusted Brent close")
        price = round(value, 2)
        if abs(value - price) > 0.0001:
            raise ValueError("Brent close differs from quoted cents beyond float encoding")
        rows.append(
            Observation(
                on=on,
                value=price,
                available_on=capture_day(metadata),
                source_url=metadata["url"],
                unit="USD per barrel",
            )
        )
    if {r.on.month for r in rows} != set(range(3, 10)):
        raise ValueError("Brent history must cover all seven requested months")
    return list(validate_observations("brent_usd_bbl", rows))


def fred_rows(payload: bytes, metadata: dict) -> list[Observation]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if reader.fieldnames != ["observation_date", "INDIRLTLT01STM"]:
        raise ValueError("unexpected FRED/OECD benchmark or CSV definition")
    rows = []
    for row in reader:
        period = date.fromisoformat(row["observation_date"])
        if period.day != 1 or not START <= period <= END or row["INDIRLTLT01STM"] in {"", "."}:
            raise ValueError("FRED period or value is missing/outside the requested range")
        value = float(row["INDIRLTLT01STM"])
        if not math.isfinite(value) or not 0 < value < 25:
            raise ValueError("invalid monthly ten-year yield")
        on = period.replace(day=calendar.monthrange(period.year, period.month)[1])
        rows.append(
            Observation(
                on=on,
                value=value,
                available_on=capture_day(metadata),
                source_url=metadata["url"],
                unit="percent",
            )
        )
    if len(rows) != 7 or {r.on.month for r in rows} != set(range(3, 10)):
        raise ValueError("FRED main ten-year series must have exactly the seven months")
    return list(validate_observations("gsec_10y_pct", rows))


def ppac_rows(payload: bytes, metadata: dict) -> list[Observation]:
    if metadata.get("parameters") != {
        "financialYear": "2026-2027",
        "reportBy": "4",
        "pageId": "30",
    }:
        raise ValueError("unexpected public PPAC table definition")
    records = [r for r in json.loads(payload)["result"].values() if r.get("title") == "2026-27"]
    if len(records) != 1:
        raise ValueError("expected one current financial-year basket row")
    rows = []
    for month in range(4, 10):
        value = records[0][calendar.month_name[month].lower()]
        if type(value) not in {float, int} or not math.isfinite(value) or value <= 0:
            raise ValueError("PPAC monthly value is absent or invalid")
        on = date(2026, month, calendar.monthrange(2026, month)[1])
        rows.append(
            Observation(
                on=on,
                value=value,
                available_on=capture_day(metadata),
                source_url="https://ppac.gov.in/prices/international-prices-of-crude-oil",
                unit="USD per barrel",
            )
        )
    return rows


def acquire(
    *, raw: Path, cdsl: Path, visual_seed: Path, canonical: Path, output: Path, report: Path
) -> dict:
    if output.resolve() == canonical.resolve() or output.exists():
        raise ValueError(
            "use a fresh separate retrospective directory; never replace the default store"
        )
    before = {p.name: digest(p) for p in canonical.glob("*.csv")}
    series, sources = {}, {}
    for name, source_id, parser in [
        ("brent_nymex_chart", "brent_usd_bbl", brent_rows),
        ("gsec_oecd_fred_main", "gsec_10y_pct", fred_rows),
        ("ppac_current_monthly", "indian_basket_usd_bbl", ppac_rows),
    ]:
        extension = ".csv" if name == "gsec_oecd_fred_main" else ".json"
        payload, metadata = checked_source(raw / (name + extension), raw / (name + ".meta.json"))
        series[source_id] = parser(payload, metadata)
        sources[source_id] = [{"raw": str(raw / (name + extension)), **metadata}]
    seed = json.loads(visual_seed.read_text())
    metadata_path = Path(seed["source_metadata"])
    pdf = metadata_path.with_name(metadata_path.name.replace(".meta.json", ".pdf"))
    payload, metadata = checked_source(pdf, metadata_path)
    if (
        seed["raw_sha256"] != hashlib.sha256(payload).hexdigest()
        or seed["on"] != "2026-03-31"
        or seed["unit"] != "USD per barrel"
    ):
        raise ValueError("visual transcription does not match the identified March source")
    april = next(row.value for row in series["indian_basket_usd_bbl"] if row.on.month == 4)
    if any(value != april for value in seed["crosscheck"].values()):
        raise ValueError("visual source and current PPAC April cross-check differ")
    series["indian_basket_usd_bbl"].append(
        Observation(
            on=date.fromisoformat(seed["on"]),
            value=seed["value"],
            available_on=capture_day(metadata),
            source_url=metadata["url"],
            unit=seed["unit"],
        )
    )
    sources["indian_basket_usd_bbl"].append(
        {
            "raw": str(pdf),
            "raw_sha256": seed["raw_sha256"],
            "captured_at": metadata["fetched_at"],
            "transcription": seed,
        }
    )
    fpi = []
    sources["fpi_flows_usd_mn"] = []
    for month in range(3, 10):
        end = date(2026, month, calendar.monthrange(2026, month)[1])
        path = cdsl / f"archive_{end}.html"
        payload, metadata = checked_source(path, path.with_suffix(".meta.json"))
        if (
            metadata.get("url") != ARCHIVE_URL
            or metadata.get("form_url") != FORM_URL
            or metadata.get("requested_as_of") != str(end)
        ):
            raise ValueError("CDSL snapshot selection does not match the requested month")
        row, details = parse_month(
            payload.decode("utf-8"), cutoff=end, captured_on=capture_day(metadata)
        )
        fpi.append(row)
        sources["fpi_flows_usd_mn"].append({"raw": str(path), **metadata, **details})
    series["fpi_flows_usd_mn"] = fpi
    for source_id, rows in series.items():
        validate_observations(source_id, rows)
    output.mkdir(parents=True, exist_ok=False)
    for source_id, rows in series.items():
        write_csv(output / (source_id + ".csv"), series_id=source_id, records=rows)
    for name in ("cpi_headline_yoy.csv", "inr_usd.csv"):
        shutil.copyfile(canonical / name, output / name)
    after = {p.name: digest(p) for p in canonical.glob("*.csv")}
    if before != after:
        raise ValueError("default point-in-time series changed unexpectedly")
    result = {
        "status": "retrospective capture, not an original point-in-time history or human acceptance",
        "directory": str(output),
        "new_historical_observations": {sid: len(rows) for sid, rows in series.items()},
        "original_cpi_fx_copied_unchanged": True,
        "canonical_sha256_before": before,
        "canonical_sha256_after": after,
        "files": {
            p.name: {"sha256": digest(p), "observations": sum(1 for _ in p.open()) - 1}
            for p in output.glob("*.csv")
        },
        "sources": sources,
        "definitions": {
            "brent_usd_bbl": "Yahoo BZ=F NYMEX Brent Last Day Financial futures vendor continuous daily closes; cents normalized from float encoding. Vendor roll mapping is not independently verified against every ICE contract; not spot, not the previous intraday news series.",
            "gsec_10y_pct": "FRED/OECD INDIRLTLT01STM, main (including benchmark) Indian ten-year government bond yield, monthly percent. Monthly period labels are stored on month end; not daily or month-end closes and not a generic par-yield substitute.",
            "indian_basket_usd_bbl": "PPAC monthly averages. April-September from the public current-year table; March from the identified scanned snapshot, with the overlapping April value cross-checked against both the page 38 table and public table.",
            "fpi_flows_usd_mn": "CDSL monthly custodian-reporting flows: Equity + Debt + Debt-VRR + Debt FAR, native USD million. Last reporting day may precede a calendar month end; no reporting/release date is inferred from that fact.",
        },
        "availability": "The particular captured values become visible only from their actual verified cache capture dates in India time. Those dates are conservative known-availability upper bounds, not first release dates. No original March-September vintage is asserted.",
        "limits": [
            "Retrospective files are separate from the default agent store and cannot supply information to earlier as-of queries.",
            "Monthly observations cannot confirm a particular daily threshold crossing or daily episode date.",
            "Vendor continuous futures contract rolls and quoted closes differ from intraday ICE news quotes.",
            "Retrospective values may differ from earlier published values; existing vintages are never overwritten.",
            "No anchor-confirmation flags, human-review attestations or causal evidence labels are generated.",
        ],
        "citation": "OECD (2026), Main Economic Indicators, via FRED, Federal Reserve Bank of St. Louis, INDIRLTLT01STM; accessed 25 October 2026. Yahoo Finance BZ=F and PPAC/CDSL sources are linked per observation.",
    }
    (output / "PROVENANCE.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, default=Path("data/raw/track_a_20261025"))
    p.add_argument("--cdsl", type=Path, default=Path("data/raw/series/cdsl"))
    p.add_argument(
        "--visual-seed",
        type=Path,
        default=Path("scripts/fetch/ppac_retrospective_visual_seed.json"),
    )
    p.add_argument("--canonical", type=Path, default=Path("data/series"))
    p.add_argument("--output", type=Path, default=Path("data/series/retrospective_20261025"))
    p.add_argument(
        "--report",
        type=Path,
        default=Path("reports/retrospective_series_acquisition_20261025.json"),
    )
    a = p.parse_args()
    r = acquire(
        raw=a.raw,
        cdsl=a.cdsl,
        visual_seed=a.visual_seed,
        canonical=a.canonical,
        output=a.output,
        report=a.report,
    )
    print(
        json.dumps(
            {
                "status": r["status"],
                "new_historical_observations": r["new_historical_observations"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
