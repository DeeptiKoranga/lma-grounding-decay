"""Validate actual snapshot files through the date-aware tool read layer."""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from corpus.series import SERIES_SPECS, SeriesStore
from schema.tools import GetSeriesArgs


def validate(*, canonical: Path, snapshot: Path) -> dict:
    provenance = json.loads((snapshot / "PROVENANCE.json").read_text())
    original = SeriesStore.from_directory(canonical)
    retrospective = SeriesStore.from_directory(snapshot)
    checks, details = {}, {}
    for sid in SERIES_SPECS:
        args = GetSeriesArgs(
            series_id=sid,
            start=date(2026, 3, 1),
            end=date(2026, 9, 30),
            as_of=date(2026, 9, 30),
        )
        late = args.model_copy(update={"as_of": date(2026, 10, 25)})
        early_rows = retrospective.observations(args)
        late_rows = retrospective.observations(late)
        result = retrospective.get_series(late, call_id=f"snapshot-{sid}")
        assert result.ok and len(result.points) == len(late_rows)
        if sid not in {"cpi_headline_yoy", "inr_usd"}:
            assert early_rows == (), f"retrospective values leaked before capture: {sid}"
            assert {r.on.month for r in late_rows} == set(range(3, 10))
            checks[f"{sid}_hidden_at_september_cutoff"] = True
            checks[f"{sid}_covers_all_seven_months_after_capture"] = True
        else:
            assert (snapshot / f"{sid}.csv").read_bytes() == (canonical / f"{sid}.csv").read_bytes()
            assert early_rows == original.observations(args)
            checks[f"{sid}_unchanged"] = True
        path = snapshot / f"{sid}.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == provenance["files"][path.name]["sha256"]
        details[sid] = {
            "stored_observations": len(retrospective.series[sid]),
            "visible_at_september_30": len(early_rows),
            "visible_at_october_25": len(late_rows),
            "move_at_october_25": result.move,
            "sha256": digest,
        }
    current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in canonical.glob("*.csv")}
    assert current == provenance["canonical_sha256_before"] == provenance["canonical_sha256_after"]
    assert sum(len(rows) for rows in original.series.values()) == 161
    assert sum(len(rows) for rows in retrospective.series.values()) == 317
    checks["default_store_ignores_nested_snapshot"] = True
    checks["all_default_csv_hashes_unchanged"] = True
    return {
        "status": "passed; read-layer and source-byte validation, not research acceptance",
        "canonical": str(canonical),
        "snapshot": str(snapshot),
        "canonical_observations": 161,
        "snapshot_observations": 317,
        "checks": checks,
        "series": details,
        "limits": [
            "Monthly observations do not validate daily episode dates.",
            "Capture dates establish known availability, not original publication dates.",
            "Brent vendor continuous closes and monthly main bond yields differ from the sparse news definitions.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=Path("data/series"))
    parser.add_argument("--snapshot", type=Path, default=Path("data/series/retrospective_20261025"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate(canonical=args.canonical, snapshot=args.snapshot)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
