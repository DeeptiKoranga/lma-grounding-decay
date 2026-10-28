"""Import audited local macro CSVs or query their as-of-safe series store.

This command does not infer values from news, interpolate missing observations,
or assign a release date when the source does not state one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path

from corpus.series import SERIES_SPECS, SeriesStore, read_csv, write_csv
from schema.tools import GetSeriesArgs


def import_series(input_path: Path, *, series_id: str, root: Path, replace: bool = False) -> dict:
    records = read_csv(input_path, series_id=series_id)
    if not records:
        raise ValueError("refusing to import an empty series")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{series_id}.csv"
    if target.exists() and not replace:
        raise FileExistsError(f"{target} exists; use --replace after reviewing its vintages")
    handle, temporary = tempfile.mkstemp(dir=root, prefix=f".{series_id}-", suffix=".tmp")
    os.close(handle)
    temporary_path = Path(temporary)
    try:
        write_csv(temporary_path, series_id=series_id, records=records)
        if replace:
            os.replace(temporary_path, target)
        else:
            # Atomic create-if-absent, including a concurrent import race.
            os.link(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {
        "series_id": series_id,
        "path": str(target),
        "observations": len({row.on for row in records}),
        "vintages": len(records),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "unit": SERIES_SPECS[series_id].unit,
        "use": "move_confirmation_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="Import a normalized local CSV")
    importer.add_argument("--input", type=Path, required=True)
    importer.add_argument("--series-id", choices=SERIES_SPECS, required=True)
    importer.add_argument("--root", type=Path, default=Path("data/series"))
    importer.add_argument("--replace", action="store_true")
    query = commands.add_parser("read", help="Read only observations available by as-of")
    query.add_argument("--series-id", choices=SERIES_SPECS, required=True)
    query.add_argument("--root", type=Path, default=Path("data/series"))
    query.add_argument("--start", type=date.fromisoformat, required=True)
    query.add_argument("--end", type=date.fromisoformat, required=True)
    query.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    try:
        if args.command == "import":
            result = import_series(
                args.input, series_id=args.series_id, root=args.root, replace=args.replace
            )
        else:
            result = (
                SeriesStore.from_directory(args.root)
                .get_series(
                    GetSeriesArgs(
                        series_id=args.series_id, start=args.start, end=args.end, as_of=args.as_of
                    ),
                    call_id="series-cli",
                )
                .model_dump(mode="json")
            )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
