"""Run one pinned local model against frozen project-specific C2 cases, resumably."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from collections import defaultdict
from pathlib import Path

from conditions.provenance import digest, model_identity, runtime_identity, write_json
from eval.model_pilot import MODEL_SPECS, SELECTION_RULE, build_cases, score
from llm.generate import MLXGenerator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODEL_SPECS, required=True)
    parser.add_argument(
        "--cases", type=Path, default=Path("data/eval/project_model_pilot_cases.jsonl")
    )
    parser.add_argument("--output", type=Path, default=Path("runs/project_model_pilot_20261030"))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    serialized = "".join(
        json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in build_cases()
    ).encode()
    if args.cases.exists() and args.cases.read_bytes() != serialized:
        raise ValueError("frozen case file changed; use a new case path")
    args.cases.write_bytes(serialized)
    if args.prepare_only:
        print(
            json.dumps(
                {"cases": 100, "sha256": digest(args.cases), "selection_rule": SELECTION_RULE}
            )
        )
        return
    cases = [json.loads(line) for line in serialized.decode().splitlines()]
    model_id, revision, dirname = MODEL_SPECS[args.model]
    model_path = Path("data/raw/generator") / dirname
    output = args.output / args.model
    output.mkdir(parents=True, exist_ok=True)
    sources = [
        Path("src/eval/model_pilot.py"),
        Path("src/llm/generate.py"),
        Path("src/extract/candidates.py"),
        Path("scripts/run_model_pilot.py"),
    ]
    inputs = {
        "model": model_id,
        "revision": revision,
        "case_sha256": digest(args.cases),
        "model_files": model_identity(model_path),
        "runtime": runtime_identity(),
        "source_sha256": {str(p): digest(p) for p in sources},
        "selection_rule": SELECTION_RULE,
        "quantization": "MLX affine 4-bit",
        "max_tokens": 512,
        "platform": platform.platform(),
        "status": "synthetic project-schema model selection",
    }
    provenance = output / "inputs.json"
    if provenance.exists() and json.loads(provenance.read_text(encoding="utf-8")) != inputs:
        raise ValueError("resume requires unchanged cases, model bytes, source and runtime")
    write_json(provenance, inputs)
    completed = {p.stem for p in output.glob("*-*.json")}
    generator = None
    if any(c["id"] not in completed for c in cases):
        generator = MLXGenerator(model_path, model_id=model_id, revision=revision)
    started = time.monotonic()
    for index, case in enumerate(cases):
        target = output / f"{case['id']}.json"
        if target.exists():
            continue
        completion = generator.generate(case["prompt"], max_tokens=512)
        row = {
            "id": case["id"],
            "task": case["task"],
            "model": model_id,
            "revision": revision,
            "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
            "prompt": case["prompt"],
            "raw_output": completion.text,
            "prompt_tokens": completion.prompt_tokens,
            "completion_tokens": completion.completion_tokens,
            "latency_ms": completion.latency_ms,
            "scores": score(case, completion.text),
        }
        write_json(target, row)
        print(f"{args.model} {index+1}/100 {case['id']} score={row['scores']['score']}", flush=True)
    grouped = defaultdict(list)
    for case in cases:
        row = json.loads((output / f"{case['id']}.json").read_text(encoding="utf-8"))
        grouped[case["task"]].append(row)
    tasks = {
        task: {
            "n": len(rows),
            "accuracy": sum(r["scores"]["score"] for r in rows) / len(rows),
            "strict_json_validity": sum(r["scores"]["strict_json_valid"] for r in rows) / len(rows),
            "schema_validity": sum(r["scores"]["schema_valid"] for r in rows) / len(rows),
        }
        for task, rows in grouped.items()
    }
    rows = [r for group in grouped.values() for r in group]
    summary = {
        "model": model_id,
        "revision": revision,
        "cases": len(rows),
        "tasks": tasks,
        "mean_task_accuracy": sum(t["accuracy"] for t in tasks.values()) / len(tasks),
        "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
        "completion_tokens": sum(r["completion_tokens"] for r in rows),
        "model_call_seconds": sum(r["latency_ms"] for r in rows) / 1000,
        "mean_latency_ms": sum(r["latency_ms"] for r in rows) / len(rows),
        "current_invocation_wall_seconds": time.monotonic() - started,
        "inputs_sha256": digest(provenance),
        "selection_rule": SELECTION_RULE,
        "status": "complete synthetic project-schema pilot; not research evaluation",
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
