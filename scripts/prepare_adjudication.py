"""Write one blind adjudication worksheet per annotator (#15, #37).

    python scripts/prepare_adjudication.py --annotators Deepti Varun

Each worksheet holds every gold edge as span + the two variables + the dates,
and **no label**. `data/eval/gold/dev/ADJUDICATION.md` prints the drafter's own
labels, so two people working from that would be agreeing with the draft rather
than with each other; kappa on that measures how persuasive the draft is, not
how reliable the annotation is.

Both annotators get **all** the edges, not a half each. The dev gold set is 20
edges; splitting it would leave kappa resting on 4 to 6 items, which cannot
support any claim, and double-labelling the whole set also means every edge is
settled by two people rather than one.

Worksheets are not overwritten once they have an answer in them, so a re-run
cannot wipe an evening's work.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from eval.adjudication import BLANK_COLUMNS, FILLED_COLUMNS, build_items, worksheet_rows
from eval.gold import load_gold_graph

REPO = Path(__file__).resolve().parent.parent
QUERIES = REPO / "data/eval/queries_dev.jsonl"
OUT_DIR = REPO / "data/eval/gold/dev/adjudication"

#: Fixed, so two people on two laptops get the same worksheets.
SEED = 20261028


def _query_ids() -> list[str]:
    return [
        json.loads(line)["query_id"]
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _has_answers(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open(encoding="utf-8-sig") as handle:
        return any((row.get("asserts") or "").strip() for row in csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotators", nargs="+", required=True, help="two or more names")
    parser.add_argument("--force", action="store_true", help="overwrite a started worksheet")
    args = parser.parse_args(argv)

    if len(args.annotators) < 2:
        print("kappa needs at least two annotators", file=sys.stderr)
        return 2

    items = build_items([load_gold_graph(q) for q in _query_ids()])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    columns = [*FILLED_COLUMNS, *BLANK_COLUMNS]

    for annotator in args.annotators:
        slug = annotator.strip().lower().replace(" ", "-")
        path = OUT_DIR / f"worksheet-{slug}.csv"
        if _has_answers(path) and not args.force:
            print(f"  kept    {path.relative_to(REPO)}  (already has answers; --force to replace)")
            continue
        rows = worksheet_rows(items, annotator, seed=SEED)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  wrote   {path.relative_to(REPO)}  ({len(rows)} items)")

    print(
        f"\n{len(items)} edges per annotator. Fill 'asserts', 'direction', 'strength', 'verdict'."
    )
    print("Do not open anyone else's worksheet until yours is finished and committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
