"""Import sparse, explicitly dated market observations from archived news.

These are published news vintages, not exchange settlement histories. Preserve
the measurement type, precision and source limitations in the provenance file.
No interpolation, FX conversion, causal labels or historical archive backdating.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from corpus import parse_html
from corpus.quality import rejection_reason
from corpus.series import Observation, validate_observations, write_csv
from schema import Passage

SPECS = {
    "brent_front_quote": ("brent_usd_bbl", "USD per barrel"),
    "brent_expiry_quote": ("brent_usd_bbl", "USD per barrel"),
    "gsec_close": ("gsec_10y_pct", "percent"),
    "fpi_monthly_net": ("fpi_flows_usd_mn", "USD million, net"),
}


def extract_claim(kind: str, passage: Passage, on: date) -> tuple[Observation, dict]:
    if kind not in SPECS:
        raise ValueError("unknown news series claim kind")
    # Match presentation-only format controls without changing the archived quote.
    text = "".join(c for c in passage.text if unicodedata.category(c) != "Cf")
    published = passage.published_at.date()
    if on > published or (kind != "fpi_monthly_net" and on != published):
        raise ValueError("news quote/close must date to its publication day")
    details = {}
    if kind == "brent_front_quote":
        match = re.search(
            r"\b(?:Front[ -]month Brent crude futures|front-month Brent contract(?: for (?P<contract>\w+) delivery)?) (?:gained|rose|fell|declined|increased|decreased).{0,100}?to \$(?P<value>\d+\.\d+) (?:a|per) barrel",
            text,
            re.IGNORECASE,
        )
        if match is None:
            raise ValueError("explicit front-month Brent price missing")
        value = float(match["value"])
        details = {
            "measure": "intraday front-month futures quote; not daily settlement",
            "contract_basis": "explicit front-month label",
        }
        if match["contract"]:
            details["contract_month"] = match["contract"]
    elif kind == "brent_expiry_quote":
        match = re.search(
            r"Brent crude futures for (\w+)(?: delivery)?, which expire on (\w+)[\u2019']?s?(?: settlement)?, ((?:rose|gained|fell|was down|were down|was up|were up|traded).{0,100}?)(?:at|reach) \$(\d+\.\d+) (?:a|per) barrel",
            text,
        )
        if match is None or match[2] != on.strftime("%A"):
            raise ValueError("nearby Brent contract must explicitly expire on the observation day")
        contract_month = list(calendar.month_name).index(match[1])
        if contract_month != (on.month + 1) % 12 + 1:
            raise ValueError("expiring Brent contract month inconsistent with observation")
        value = float(match[4])
        details = {
            "measure": "intraday front-month futures quote; not daily settlement",
            "contract_basis": "nearby contract explicitly expiring today; deferred contract excluded",
            "contract_month": match[1],
        }
    elif kind == "gsec_close":
        security = re.search(r"(\d+\.\d+)\s*(?:per cent|%)\s*(?:GS\s*)?(203\d)", text)
        closing = re.search(
            r"(?:closed|ended(?: the session)?) at (\d+\.\d+)\s*(?:per cent|%)", text
        )
        if "benchmark" not in text.lower() or not security or not closing:
            raise ValueError("named benchmark security and realised closing yield required")
        if int(security[2]) - on.year not in {9, 10}:
            raise ValueError("security does not match current ten-year benchmark maturity")
        value = float(closing[1])
        details = {
            "measure": "reported current ten-year benchmark closing yield",
            "security": f"{security[1]}% GS {security[2]}",
            "roll_policy": "only explicitly identified current benchmark on each observed date; no inferred roll date",
        }
    else:
        if not re.search(r"overseas investors have net sold.*local stock and bonds", text):
            raise ValueError("explicit net local equity-plus-debt universe required")
        month = calendar.month_name[on.month]
        match = re.search(
            rf"\b{month}[\u2019']s \$(\d+(?:\.\d+)?) billion (outflow|inflow)\b", text
        )
        if not match or on.day != calendar.monthrange(on.year, on.month)[1]:
            raise ValueError("explicit completed-month net total required; bounds/MTD excluded")
        if (published.year * 12 + published.month) - (on.year * 12 + on.month) != 1:
            raise ValueError("month label must refer to the immediately preceding completed month")
        value = float(match[1]) * 1000 * (-1 if match[2] == "outflow" else 1)
        details = {
            "measure": "reported completed-calendar-month net equity-plus-debt flow",
            "conversion": "native USD billion multiplied by 1000; no exchange-rate conversion",
            "reported_precision_usd_million": 1000
            * 10 ** (-len(match[1].split(".")[1]) if "." in match[1] else 0),
            "coverage": "one observation; no flow move or monthly history established",
        }
    if kind != "fpi_monthly_net" and value <= 0:
        raise ValueError("market level must be positive")
    series_id, unit = SPECS[kind]
    row = Observation(on=on, value=value, available_on=published, source_url=passage.url, unit=unit)
    validate_observations(series_id, [row])
    return row, details


def acquire(*, seeds: Path, corpus: Path, raw: Path, output: Path, report: Path) -> dict:
    specification = json.loads(seeds.read_text(encoding="utf-8"))
    corpus_digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    if specification["corpus_sha256"] != corpus_digest:
        raise ValueError("claim corpus hash mismatch")
    passages = {
        p.passage_id: p
        for p in (
            Passage.model_validate_json(line)
            for line in corpus.read_text(encoding="utf-8").splitlines()
        )
    }
    records, sources = {}, []
    for claim in specification["claims"]:
        passage = passages[claim["passage_id"]]
        key = hashlib.sha256(passage.url.encode()).hexdigest()[:20]
        sidecar = raw / passage.source / f"{key}.meta.json"
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        payload = sidecar.with_name(f"{key}.html").read_bytes()
        if (
            not meta.get("accepted")
            or meta["url"] != passage.url
            or meta["source"] != passage.source
        ):
            raise ValueError("claim raw source identity/acceptance mismatch")
        if hashlib.sha256(payload).hexdigest() != meta["sha256"]:
            raise ValueError("claim raw source checksum mismatch")
        document = parse_html(
            payload.decode(meta.get("charset") or "utf-8"), source=passage.source, url=passage.url
        )
        if reason := rejection_reason(document):
            raise ValueError(reason)
        if document.published_at != passage.published_at or passage.text not in document.text:
            raise ValueError("claim does not match the dated archived source body")
        row, details = extract_claim(claim["kind"], passage, date.fromisoformat(claim["on"]))
        series_id = SPECS[claim["kind"]][0]
        records.setdefault(series_id, []).append(row)
        sources.append(
            {
                "series_id": series_id,
                "passage_id": passage.passage_id,
                "published_at": passage.published_at.isoformat(),
                "raw_metadata": str(sidecar),
                "raw_sha256": meta["sha256"],
                "passage_sha256": hashlib.sha256(passage.text.encode()).hexdigest(),
                "observation": row.model_dump(mode="json"),
                **details,
            }
        )
    for series_id, rows in records.items():
        validate_observations(series_id, rows)
        if (output / f"{series_id}.csv").exists():
            raise ValueError("news importer refuses to overwrite an existing series")
    result = {
        "status": "sparse news-reported observations; coverage incomplete",
        "corpus_sha256": corpus_digest,
        "seeds_sha256": hashlib.sha256(seeds.read_bytes()).hexdigest(),
        "counts": {sid: len(rows) for sid, rows in sorted(records.items())},
        "sources": sources,
        "limitations": [
            "News-reported vintages, not an official continuous exchange/depository history.",
            "Known later-day article versions are rejected; unknown historical edits remain a limitation of the archived corpus.",
            "Brent values are intraday quotes at different times and contract months, not settlement closes or a back-adjusted continuous series.",
            "GSEC uses each report's explicitly named current benchmark; security changes are retained, with no filled roll date.",
            "FPI is one rounded completed-month total; move=None, with no monthly coverage inferred.",
            "Do not use sparse observations to confirm unsampled daily thresholds, anchor dates or causal edges.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    for series_id, rows in records.items():
        write_csv(output / f"{series_id}.csv", series_id=series_id, records=rows)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds", type=Path, default=Path("scripts/fetch/news_series_seeds_v7_20261030.json")
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/processed/articles.jsonl"),
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/series"))
    parser.add_argument(
        "--report", type=Path, default=Path("data/series/news_reported_provenance.json")
    )
    args = parser.parse_args()
    result = acquire(
        seeds=args.seeds, corpus=args.corpus, raw=args.raw, output=args.output, report=args.report
    )
    print(json.dumps({"status": result["status"], "counts": result["counts"]}))


if __name__ == "__main__":
    main()
