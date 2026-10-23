"""Audit completed graphs and actual logs without inventing human support scores."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from corpus.bindings import require_run_corpus
from schema import Graph, Passage, iter_run_log

from .safety import inspect_graph


def audit(*, runs: Path, corpus: Path) -> dict:
    require_run_corpus(runs, corpus)
    passages = [
        Passage.model_validate_json(line)
        for line in corpus.read_text().splitlines()
        if line.strip()
    ]
    graphs, conditions, failures = [], Counter(), []
    for path in sorted(runs.glob("*/*.json")):
        payload = json.loads(path.read_text())
        if "graph" not in payload:
            continue
        graph = Graph.model_validate(payload["graph"])
        safety = inspect_graph(graph, passages)
        conditions[graph.condition] += 1
        graphs.append(
            {
                "query_id": graph.query_id,
                "condition": graph.condition,
                "edges": len(graph.edges),
                "established_edges": len(payload["established_edge_ids"]),
                "paths": len(graph.paths),
                "tool_calls": payload["tool_calls"],
                "stop_reason": payload["stop_reason"],
                "unchecked_inferred_edges": sum(
                    not edge.is_asserted and edge.verdict is None for edge in graph.edges
                ),
                "verifier_verdicts": dict(
                    Counter(str(edge.verdict) for edge in graph.edges if edge.verdict is not None)
                ),
                "safety": safety,
                "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        if payload["tool_calls"] > 12:
            failures.append({"artifact": str(path), "kind": "budget_exceeded"})
        if graph.condition in {"M", "A-NoLoop"} and not safety["passed"]:
            failures.append({"artifact": str(path), "kind": "verified_graph_failed_source_checks"})
    compute = defaultdict(
        lambda: {
            "model_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "model_call_wall_s": 0,
            "tool_calls": 0,
            "invalid_json_calls": 0,
        }
    )
    for path in sorted(runs.glob("*/*.jsonl")):
        for record in iter_run_log(path):
            row = compute[str(record.condition)]
            if record.event == "model_call":
                row["model_calls"] += 1
                row["prompt_tokens"] += record.prompt_tokens
                row["completion_tokens"] += record.completion_tokens
                row["model_call_wall_s"] += record.latency_ms / 1000
                row["invalid_json_calls"] += record.json_valid is False
            elif record.event == "tool_call":
                row["tool_calls"] += 1
    return {
        "status": "development integration audit; no human support scores",
        "completed_graphs": len(graphs),
        "conditions": dict(conditions),
        "failures": failures,
        "graphs": graphs,
        "compute": dict(compute),
        "compute_note": "measured model-call wall times and actual token counts; not GPU-active time or full phase time",
        "research_acceptance": "pending model/retriever selection, human correction/support review, independent gold and anchor confirmation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(runs=args.runs, corpus=args.corpus)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: result[key] for key in ("status", "completed_graphs", "conditions", "failures")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
