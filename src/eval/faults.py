"""Execute frozen synthetic backend faults against the real tool boundary."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from corpus.series import SeriesStore
from retrieval.bm25 import Aliases, BM25Retriever, Hit
from schema import Anchor
from tools.runtime import ToolRuntime
from verify.paths import rebuild


def evaluate(*, specs: Path, corpus: Path, aliases: Path) -> dict:
    records = [json.loads(line) for line in specs.read_text().splitlines() if line.strip()]
    outcomes = []
    for i, record in enumerate(records):
        retriever = BM25Retriever.from_jsonl(corpus, aliases=Aliases.load(aliases))
        graph = rebuild(
            query_id=record["fault_id"],
            anchor=Anchor(
                var="BRENT",
                direction="up",
                event="Synthetic tool fault",
                event_date=date(2026, 3, 12),
            ),
            as_of=date(2026, 3, 20),
            edges=[],
        )
        tools = ToolRuntime(graph=graph, retriever=retriever, series=SeriesStore({}))
        kind = record["kind"]
        cutoff = graph.as_of
        if kind == "empty_result":
            retriever.search = lambda **_: []
        elif kind == "backend_error":
            error = [OSError, RuntimeError, ValueError, KeyError, TimeoutError][i // 4 % 5]

            def broken(error_type=error, **_):
                raise error_type("scripted backend failure")

            retriever.search = broken
        elif kind == "malformed_backend_passage":
            p = retriever.passages[0]
            modifications = [
                {"title": "forged"},
                {"doc_id": "forged"},
                {"passage_id": "absent"},
                {"text": "x" * len(p.text)},
                {},
            ][i // 4 % 5]
            hit = Hit(p.model_copy(update=modifications), float("nan") if not modifications else 1)
            retriever.search = lambda stored=hit, **_: [stored]
        elif kind == "future_cutoff":
            cutoff += timedelta(days=i // 4 + 1)
        else:
            raise ValueError(f"unknown scripted fault {kind}")
        result = tools.call("search_corpus", query=f"oil fault {i}", as_of=cutoff)
        expected = "after_as_of" if kind == "future_cutoff" else "backend_error"
        passed = (
            (result.ok and not result.passages)
            if kind == "empty_result"
            else (not result.ok and result.error.kind == expected)
        )
        outcomes.append(
            {
                "fault_id": record["fault_id"],
                "kind": kind,
                "passed": passed,
                "calls_used": tools.calls_used,
                "cutoff_preserved": tools.graph.as_of == graph.as_of,
                "graph_unchanged": tools.graph == graph,
            }
        )
    return {
        "status": "executed synthetic fault diagnostic; not a model recovery benchmark",
        "faults": len(outcomes),
        "passed": sum(row["passed"] for row in outcomes),
        "outcomes": outcomes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs", type=Path, default=Path("data/eval/synthetic/tool_faults.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("tests/fixtures/passages.jsonl"))
    parser.add_argument("--aliases", type=Path, default=Path("data/aliases.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(specs=args.specs, corpus=args.corpus, aliases=args.aliases)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "outcomes"}, indent=2))


if __name__ == "__main__":
    main()
