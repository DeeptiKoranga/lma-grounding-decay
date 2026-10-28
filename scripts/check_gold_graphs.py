"""Check the reviewer evidence graphs (B4).

    python scripts/check_gold_graphs.py [--require] [--corpus PATH]

Structure is always checked. Spans are confirmed verbatim against the corpus
when it is present; the corpus payload is not in git, so without it the script
says so rather than passing silently. `--require` additionally fails while any
dev query still has no gold graph.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.gold import (
    GOLD_DIR,
    check_against_corpus,
    load_gold_graph,
    missing_gold_graphs,
    validate_gold_graph,
)
from schema import Passage

REPO = Path(__file__).resolve().parent.parent
DEV_QUERIES = REPO / "data/eval/queries_dev.jsonl"
DEFAULT_CORPUS = REPO / "data/processed/articles.jsonl"


def _dev_query_ids() -> list[str]:
    return [
        json.loads(line)["query_id"]
        for line in DEV_QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_corpus(path: Path) -> list[Passage] | None:
    if not path.is_file():
        return None
    return [
        Passage.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require", action="store_true", help="fail while any graph is missing")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--gold", type=Path, default=REPO / GOLD_DIR)
    args = parser.parse_args(argv)

    query_ids = _dev_query_ids()
    missing = missing_gold_graphs(query_ids, args.gold)
    passages = _load_corpus(args.corpus)

    if passages is None:
        print(f"corpus not found at {args.corpus} - checking structure only", file=sys.stderr)

    failures = 0
    for query_id in query_ids:
        if query_id in missing:
            print(f"  MISSING   {query_id}")
            continue
        graph = load_gold_graph(query_id, args.gold)
        report = (
            check_against_corpus(graph, passages)
            if passages is not None
            else validate_gold_graph(graph, expect_query_id=query_id)
        )
        scope = "spans+structure" if report.corpus_checked else "structure"
        if report.ok:
            print(f"  ok        {query_id}  ({report.edge_count} edges, {scope})")
        else:
            failures += 1
            print(f"  FAILED    {query_id}  ({report.edge_count} edges, {scope})")
            for issue in report.issues:
                where = f" [{issue.edge_id}]" if issue.edge_id else ""
                print(f"              {where} {issue.problem}")

    done = len(query_ids) - len(missing)
    print(f"\n{done}/{len(query_ids)} gold graphs present, {failures} failing")
    if failures:
        return 1
    if args.require and missing:
        print(f"still missing: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
