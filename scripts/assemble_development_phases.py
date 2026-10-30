"""Assemble completed development phases while retaining their distinct provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from conditions.pipeline import Query
from schema import Graph, iter_run_log

PHASES = (
    ("baseline", ("B0", "B1", "B1-R", "B2"), "20389a2"),
    ("agent", ("A-NoVerify", "A-NoLoop", "M"), "79a1326"),
)
SHARED = (
    "protocol",
    "queries_sha256",
    "corpus_sha256",
    "aliases_sha256",
    "model",
    "revision",
    "backend",
    "reranker_revision",
    "first_stage",
    "series_sha256",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble(baseline: Path, agent: Path, queries: Path, output: Path):
    """Validate every case before creating a new, fully traceable run folder."""
    query_rows = [Query.model_validate_json(line) for line in queries.read_text().splitlines()]
    by_id = {query.query_id: query for query in query_rows}
    if len(by_id) != len(query_rows) or not by_id:
        raise ValueError("query IDs must be unique and nonempty")
    inputs = [json.loads((root / "inputs.json").read_text()) for root in (baseline, agent)]
    if any(inputs[0][key] != inputs[1][key] for key in SHARED):
        raise ValueError("development phases differ in a shared experimental input")
    if digest(queries) != inputs[0]["queries_sha256"]:
        raise ValueError("query file changed after the run")
    if json.loads((agent / "failures.json").read_text()):
        raise ValueError("agent phase has unresolved run failures")
    files, phases = [], []
    for root, metadata, (name, conditions, commit) in zip(
        (baseline, agent), inputs, PHASES, strict=True
    ):
        artifacts = {}
        for condition in conditions:
            actual = {path.stem for path in (root / condition).glob("*.json")}
            if actual != set(by_id):
                raise ValueError(f"{condition} does not contain exactly the declared queries")
            for qid, query in by_id.items():
                artifact = root / condition / f"{qid}.json"
                payload = json.loads(artifact.read_text())
                graph = Graph.model_validate(payload["graph"])
                if (graph.query_id, graph.condition, graph.as_of, graph.anchor) != (
                    qid,
                    condition,
                    query.as_of,
                    query.anchor,
                ):
                    raise ValueError("graph identity differs from its declared query/condition")
                if payload["tool_calls"] > 12 or payload["status"] != "development_unreviewed":
                    raise ValueError("unexpected budget or research status")
                matching = []
                for log in artifact.parent.glob(f"{qid}-*.jsonl"):
                    records = list(iter_run_log(log))
                    if records and records[0].run_id == graph.run_id:
                        matching.append(records)
                if len(matching) != 1 or matching[0][-1].event != "stop":
                    raise ValueError("completed artifact needs a complete validated event log")
                relative = artifact.relative_to(root)
                artifacts[relative.as_posix()] = digest(artifact)
                files.append((artifact, relative))
            # Retain failed attempts too: compute must not silently omit their calls.
            for log in sorted((root / condition).glob("*.jsonl")):
                list(iter_run_log(log))
                relative = log.relative_to(root)
                artifacts[relative.as_posix()] = digest(log)
                files.append((log, relative))
        phases.append(
            {
                "name": name,
                "source_root": str(root.resolve()),
                "source_commit": commit,
                "included_conditions": list(conditions),
                "inputs_sha256": digest(root / "inputs.json"),
                "inputs": metadata,
                "artifact_sha256": artifacts,
            }
        )
    manifest = {
        "status": "completed development integration; independent review pending",
        "assembly_note": (
            "Baseline generation used the original integration code. Agent conditions were "
            "rerun after the controller stop-state correction. This is a traced development "
            "assembly, not a single-source-version frozen experiment."
        ),
        "shared_inputs": {key: inputs[0][key] for key in SHARED},
        "queries": len(by_id),
        "graphs": sum(path.suffix == ".json" for path, _ in files),
        "phases": phases,
    }
    output.mkdir(parents=True, exist_ok=False)
    for path, relative in files:
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
    (output / "phases.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "failures.json").write_text("[]\n")
    return {key: manifest[key] for key in ("status", "queries", "graphs")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(args.baseline, args.agent, args.queries, args.output), indent=2))


if __name__ == "__main__":
    main()
