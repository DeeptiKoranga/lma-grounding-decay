"""Development phases must not lose provenance or mix unmatched run logs."""

import json
import runpy
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures"
MODULE = runpy.run_path(str(Path(__file__).parents[2] / "scripts/assemble_development_phases.py"))
PHASES, SHARED, assemble, digest = (
    MODULE[name] for name in ("PHASES", "SHARED", "assemble", "digest")
)


def phases(tmp_path):
    graph = json.loads((FIXTURES / "graph_brent_hormuz.json").read_text())
    query = {
        "query_id": graph["query_id"],
        "query": "Synthetic fixture question",
        "as_of": graph["as_of"],
        "anchor": graph["anchor"],
    }
    queries = tmp_path / "queries.jsonl"
    queries.write_text(json.dumps(query) + "\n")
    roots = [tmp_path / "baseline", tmp_path / "agent"]
    for index, (root, (_, conditions, _)) in enumerate(zip(roots, PHASES, strict=True)):
        root.mkdir()
        metadata = dict.fromkeys(SHARED, "fixture")
        metadata.update(queries_sha256=digest(queries), pipeline_sha256=f"phase-{index}")
        (root / "inputs.json").write_text(json.dumps(metadata))
        (root / "failures.json").write_text("[]")
        for condition in conditions:
            folder = root / condition
            folder.mkdir()
            run_id = f"fixture-{condition}"
            payload = {
                "graph": {**graph, "condition": condition, "run_id": run_id},
                "status": "development_unreviewed",
                "tool_calls": 0,
            }
            (folder / f'{query["query_id"]}.json').write_text(json.dumps(payload))
            record = {
                "run_id": run_id,
                "query_id": query["query_id"],
                "condition": condition,
                "event": "stop",
                "step": 0,
                "ts": "2026-03-20T10:00:00+05:30",
                "reason": "important_edges_resolved",
                "calls_used": 0,
                "open_edges_remaining": 0,
                "wall_clock_s": 1.0,
            }
            (folder / f'{query["query_id"]}-attempt.jsonl').write_text(json.dumps(record) + "\n")
    return *roots, queries


def test_distinct_source_fingerprints_and_failed_attempts_are_retained(tmp_path):
    baseline, agent, queries = phases(tmp_path)
    log = next((agent / "M").glob("*.jsonl"))
    failed = json.loads(log.read_text())
    failed.update(run_id="failed-attempt", reason="error")
    (log.parent / "failed-attempt.jsonl").write_text(json.dumps(failed) + "\n")
    output = tmp_path / "assembled"
    assert assemble(baseline, agent, queries, output)["graphs"] == 7
    manifest = json.loads((output / "phases.json").read_text())
    assert [phase["inputs"]["pipeline_sha256"] for phase in manifest["phases"]] == [
        "phase-0",
        "phase-1",
    ]
    assert (output / "M/failed-attempt.jsonl").exists()
    assert manifest["phases"][1]["artifact_sha256"]["M/failed-attempt.jsonl"] == digest(
        output / "M/failed-attempt.jsonl"
    )


@pytest.mark.parametrize("corruption", ["shared_input", "matching_log"])
def test_mismatched_phase_or_missing_matching_log_cannot_create_assembly(tmp_path, corruption):
    baseline, agent, queries = phases(tmp_path)
    if corruption == "shared_input":
        path = agent / "inputs.json"
        metadata = json.loads(path.read_text())
        metadata["corpus_sha256"] = "different"
        path.write_text(json.dumps(metadata))
    else:
        path = next((agent / "M").glob("*.jsonl"))
        record = json.loads(path.read_text())
        record["run_id"] = "unrelated-run"
        path.write_text(json.dumps(record) + "\n")
    output = tmp_path / "assembled"
    with pytest.raises(ValueError):
        assemble(baseline, agent, queries, output)
    assert not output.exists()
