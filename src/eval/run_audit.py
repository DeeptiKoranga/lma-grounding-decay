"""Audit completed graphs and actual logs without inventing human support scores."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from conditions.pipeline import Query
from conditions.provenance import artifact_receipts, digest, validate_cached
from corpus.bindings import require_run_corpus
from schema import Condition, Graph, Passage, iter_run_log

from .safety import inspect_graph


def audit(
    *,
    runs: Path,
    corpus: Path,
    allow_partial: bool = False,
    expected_conditions: list[str] | None = None,
    expected_queries: list[str] | None = None,
) -> dict:
    require_run_corpus(runs, corpus)
    passages = [
        Passage.model_validate_json(line)
        for line in corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    graphs, conditions, failures = [], Counter(), []
    inputs_path = runs / "inputs.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8")) if inputs_path.exists() else {}
    if (
        expected_conditions
        and inputs.get("conditions")
        and set(expected_conditions) != set(inputs["conditions"])
    ):
        failures.append({"kind": "declared_conditions_differ_from_run_inputs"})
    if (
        expected_queries
        and inputs.get("queries")
        and set(expected_queries) != {q["query_id"] for q in inputs["queries"]}
    ):
        failures.append({"kind": "declared_queries_differ_from_run_inputs"})
    expected_conditions = expected_conditions or inputs.get("conditions")
    query_models = {q["query_id"]: Query.model_validate(q) for q in inputs.get("queries", [])}
    expected_queries = expected_queries or list(query_models)
    expected = {(c, q) for c in expected_conditions or [] for q in expected_queries or []}
    if not allow_partial and not expected:
        failures.append({"kind": "expected_run_matrix_not_declared"})
    observed, successful_logs = Counter(), set()
    receipts_path = runs / "artifacts.json"
    receipts = artifact_receipts(receipts_path)

    for path in sorted(runs.glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("graph artifact must be an object")
            if "graph" not in payload:
                continue
            graph = Graph.model_validate(payload["graph"])
            if path.parent.name != graph.condition or path.stem != graph.query_id:
                raise ValueError("artifact filename/condition differs from graph identity")
            if inputs.get("format_version") == 2:
                validate_cached(
                    payload,
                    query=query_models[graph.query_id],
                    condition=graph.condition,
                    inputs_sha256=digest(inputs_path),
                )
                if digest(path) != receipts.get(path.relative_to(runs).as_posix()):
                    raise ValueError("artifact checksum mismatch or missing receipt")
                log = path.parent / payload["log_file"]
                if log.parent != path.parent or digest(log) != payload["log_sha256"]:
                    raise ValueError("execution log checksum mismatch")
                records = iter_run_log(log)
                if not records or records[-1].event != "stop" or records[-1].reason == "error":
                    raise ValueError("bound execution log did not complete successfully")
                if any(
                    r.query_id != graph.query_id
                    or r.condition != graph.condition
                    or r.run_id != graph.run_id
                    for r in records
                ):
                    raise ValueError("execution log identity mismatch")
                calls = sum(r.event == "tool_call" for r in records)
                if calls != payload["tool_calls"] or records[-1].calls_used != calls:
                    raise ValueError("execution log tool count mismatch")
                successful_logs.add(log)
        except (ValueError, KeyError, OSError) as exc:
            failures.append({"artifact": str(path), "kind": "invalid_artifact", "error": str(exc)})
            continue
        observed[(graph.condition, graph.query_id)] += 1
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
    if not graphs:
        failures.append({"kind": "no_completed_graphs"})
    for pair, count in observed.items():
        if count > 1:
            failures.append({"kind": "duplicate_graph", "condition": pair[0], "query_id": pair[1]})
    for c, q in sorted(expected - set(observed)):
        if not allow_partial:
            failures.append({"kind": "missing_graph", "condition": c, "query_id": q})
    for c, q in sorted(set(observed) - expected):
        if expected:
            failures.append({"kind": "unexpected_graph", "condition": c, "query_id": q})
    failed_path = runs / "failures.json"
    if failed_path.exists() and json.loads(failed_path.read_text(encoding="utf-8")):
        failures.append(
            {
                "kind": "recorded_run_failures",
                "records": json.loads(failed_path.read_text(encoding="utf-8")),
            }
        )
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
    logs = successful_logs if inputs.get("format_version") == 2 else set(runs.glob("*/*.jsonl"))
    for path in sorted(logs):
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
        "passed": not failures,
        "complete": bool(expected)
        and set(observed) == expected
        and not failures
        and not allow_partial,
        "allow_partial": allow_partial,
        "expected_graphs": len(expected) if expected else None,
        "completed_graphs": len(graphs),
        "conditions": dict(conditions),
        "failures": failures,
        "graphs": graphs,
        "compute": dict(compute),
        "unbound_logs": [
            p.relative_to(runs).as_posix() for p in sorted(set(runs.glob("*/*.jsonl")) - logs)
        ],
        "compute_note": "completed artifacts' bound logs only for v2; legacy logs are unbound. Measured model-call wall times and actual token counts, excluding failed/orphan attempts; not GPU-active time or full phase time",
        "research_acceptance": "separate from structural completion; model selection, human correction/support review, independent gold and episode acceptance required",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Inspect an explicitly partial/legacy run; never establish completeness",
    )
    parser.add_argument("--conditions", nargs="+", choices=[c.value for c in Condition])
    parser.add_argument("--queries", type=Path, help="Declare expected queries for a legacy run")
    args = parser.parse_args()
    query_ids = (
        [
            Query.model_validate_json(line).query_id
            for line in args.queries.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if args.queries
        else None
    )
    result = audit(
        runs=args.runs,
        corpus=args.corpus,
        allow_partial=args.allow_partial,
        expected_conditions=args.conditions,
        expected_queries=query_ids,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: result[key] for key in ("status", "completed_graphs", "conditions", "failures")},
            indent=2,
        )
    )

    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
