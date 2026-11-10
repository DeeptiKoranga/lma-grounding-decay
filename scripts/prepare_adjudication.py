"""Write one blind adjudication worksheet per annotator (#15, #37).

    python scripts/prepare_adjudication.py --annotators Deepti Varun
    python scripts/prepare_adjudication.py --set test --annotators Deepti Harshal

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
from eval.gold import gold_path, load_gold_graph

REPO = Path(__file__).resolve().parent.parent

#: Which half to prepare. `dev` is the default so the Makefile target and every
#: existing invocation keep their meaning. The two halves differ in more than a
#: path: the dev set has a graph for all four of its queries, while the test
#: half has graphs for two of its four (D-27 excludes `test-cpi-why`, and
#: `test-cpi-effects` runs the wrong way through this corpus), so the test
#: worksheets are built from whichever graphs exist rather than from the query
#: list.
SETS = {
    "dev": (REPO / "data/eval/queries_dev.jsonl", REPO / "data/eval/gold/dev"),
    "test": (REPO / "data/eval/queries_test.jsonl", REPO / "data/eval/gold/test"),
}

#: Fixed per half, so two people on two laptops get the same worksheets. The
#: test half gets its own seed: reusing the dev seed would shuffle a different
#: number of items with the same stream and buys nothing.
SEEDS = {"dev": 20261028, "test": 20261110}


def _query_ids(queries: Path, gold_dir: Path) -> list[str]:
    """Query ids that actually have a gold graph on disk, in file order."""
    declared = [
        json.loads(line)["query_id"]
        for line in queries.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [q for q in declared if gold_path(q, gold_dir).is_file()]


def _has_answers(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open(encoding="utf-8-sig") as handle:
        return any((row.get("asserts") or "").strip() for row in csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--set",
        choices=sorted(SETS),
        default="dev",
        help="which half to prepare worksheets for (default: dev)",
    )
    parser.add_argument("--annotators", nargs="+", required=True, help="two or more names")
    parser.add_argument("--force", action="store_true", help="overwrite a started worksheet")
    args = parser.parse_args(argv)

    if len(args.annotators) < 2:
        print("kappa needs at least two annotators", file=sys.stderr)
        return 2

    queries, gold_dir = SETS[args.set]
    out_dir = gold_dir / "adjudication"
    query_ids = _query_ids(queries, gold_dir)
    if not query_ids:
        print(f"no gold graph exists for any {args.set} query; draft them first", file=sys.stderr)
        return 2

    items = build_items([load_gold_graph(q, gold_dir) for q in query_ids])
    out_dir.mkdir(parents=True, exist_ok=True)
    columns = [*FILLED_COLUMNS, *BLANK_COLUMNS]

    for annotator in args.annotators:
        slug = annotator.strip().lower().replace(" ", "-")
        path = out_dir / f"worksheet-{slug}.csv"
        if _has_answers(path) and not args.force:
            print(f"  kept    {path.relative_to(REPO)}  (already has answers; --force to replace)")
            continue
        rows = worksheet_rows(items, annotator, seed=SEEDS[args.set])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  wrote   {path.relative_to(REPO)}  ({len(rows)} items)")

    print(
        f"\n{len(items)} {args.set} edges per annotator over {len(query_ids)} "
        "quer(y/ies). Fill 'asserts', 'direction', 'strength', 'verdict'."
    )
    print("Do not open anyone else's worksheet until yours is finished and committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
