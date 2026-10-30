"""Fail-closed acceptance gate for the eleven Phase 1 Track C deliverables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from conditions.config import SETTINGS
from conditions.provenance import digest, source_identity, write_json
from eval.agent_states import load_states
from eval.faults import evaluate as evaluate_faults
from eval.model_pilot import SELECTION_RULE, score
from eval.safety import load_safety_prompts, score_review
from schema import MAX_TOOL_CALLS, Condition, parse_run_log_line
from schema.export_schemas import build_schemas


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate() -> dict:
    gates = {}
    required = [
        "reports/project_model_pilot_20261030.json",
        "configs/model_selection.json",
        "data/eval/project_model_pilot_cases.jsonl",
        "data/eval/project_model_pilot_results.jsonl",
        "data/eval/safety_outputs_selected_20261030.json",
        "data/eval/safety_review_selected_20261030.json",
        "reports/kaggle_live_verification_20261030.json",
        "reports/track_c_portable_ci_final_20261030.json",
    ]
    missing = [name for name in required if not Path(name).is_file()]
    if missing:
        raise ValueError("Phase 1 execution evidence is incomplete: " + ", ".join(missing))
    for name, expected in build_schemas().items():
        if (Path("docs/schemas") / name).read_text(encoding="utf-8") != expected:
            raise ValueError(f"stale exported schema: {name}")
    parse_run_log_line(
        {
            "run_id": "acceptance",
            "query_id": "acceptance",
            "condition": "B0",
            "step": 0,
            "ts": "2026-10-30T00:00:00+00:00",
            "event": "model_call",
            "purpose": "answer",
            "model": "offline-contract",
            "backend": "claude",
            "temperature": 0,
            "prompt_sha256": "a" * 64,
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 0,
        }
    )
    gates["C1"] = "backend contract, integrated regression checks and live vLLM evidence"
    pilot = read("reports/project_model_pilot_20261030.json")
    selection = read("configs/model_selection.json")
    cases_path = Path("data/eval/project_model_pilot_cases.jsonl")
    cases = {
        c["id"]: c
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        if (c := json.loads(line))
    }
    outputs = [
        json.loads(line)
        for line in Path("data/eval/project_model_pilot_results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if (
        len(cases) != 100
        or len(outputs) != 200
        or len({(r["model"], r["id"]) for r in outputs}) != 200
        or pilot["cases_sha256"] != digest(cases_path)
        or pilot["selected"] != selection["selected"]
        or pilot["selection_rule"] != SELECTION_RULE
        or selection["selection_rule"] != SELECTION_RULE
    ):
        raise ValueError("C2 requires the unchanged complete two-model pilot and model decision")
    if any(row["scores"] != score(cases[row["id"]], row["raw_output"]) for row in outputs):
        raise ValueError("C2 raw scores no longer reproduce")
    chosen = pilot["models"][selection["selected"]]
    if (selection["model"], selection["revision"]) != (chosen["model"], chosen["revision"]):
        raise ValueError("D-01 config does not identify the actually selected pinned model")
    best = max(model["mean_task_accuracy"] for model in pilot["models"].values())
    eligible = {
        name: model
        for name, model in pilot["models"].items()
        if model["mean_task_accuracy"] >= best - 0.03 - 1e-12
    }
    if selection["selected"] != min(eligible, key=lambda name: eligible[name]["mean_latency_ms"]):
        raise ValueError("D-01 selection does not follow the pre-recorded rule")
    gates["C2"] = "100 shared cases, 200 outputs, reproduced scores and pinned D-01 selection"
    if MAX_TOOL_CALLS != 12 or len(Condition) != 7:
        raise ValueError("tool budget or condition count changed")
    flags = yaml.safe_load(Path("configs/conditions.yaml").read_text(encoding="utf-8"))
    if flags["conditions"] != {str(key): value.__dict__ for key, value in SETTINGS.items()}:
        raise ValueError("condition YAML and shared implementation differ")
    for task in ("C3", "C4", "C5", "C6", "C7", "C8"):
        gates[task] = "implemented; native full test/lint/format matrix verified separately below"
    states = load_states("data/eval/synthetic/agent_states.jsonl")
    faults = evaluate_faults(
        specs=Path("data/eval/synthetic/tool_faults.jsonl"),
        corpus=Path("tests/fixtures/passages.jsonl"),
        aliases=Path("data/aliases.yaml"),
    )
    if len(states) != 40 or faults["faults"] != 20 or faults["passed"] != 20:
        raise ValueError("C9 requires 40 states and 20 passing fresh fault cases")
    gates["C9"] = "40 frozen scripted states and 20/20 freshly executed tool faults"
    prompts = load_safety_prompts()
    safety_outputs = read("data/eval/safety_outputs_selected_20261030.json")
    safety_review = read("data/eval/safety_review_selected_20261030.json")
    safety = score_review(
        prompts, {r["prompt_id"]: r["completion"] for r in safety_outputs["outputs"]}, safety_review
    )
    if (
        len(prompts) != 25
        or safety_outputs["model"] != selection["model"]
        or safety_outputs["revision"] != selection["revision"]
    ):
        raise ValueError("C10 requires the selected pinned model's complete 25-response review")
    gates["C10"] = (
        "25 real model responses; all four risk outcomes recorded with truthful reviewer provenance"
    )
    cloud = read("reports/kaggle_live_verification_20261030.json")
    if not cloud["complete"] or cloud["completed_graphs"] != 14 or cloud["gpu_count"] != 2:
        raise ValueError("C11 requires the complete bounded two-T4 live verification")
    if not 0 < cloud["visible_allocated_gpu_hours"] <= 2 or not cloud["resume_passed"]:
        raise ValueError("C11 compute or unchanged-resume evidence is incomplete")
    evidence = Path("reports/kaggle_verification_evidence_20261030")
    if (
        digest(evidence / "bootstrap_compute.json") != cloud["bootstrap_receipt_sha256"]
        or digest(evidence / "compute-20261030T142047.json") != cloud["run_receipt_sha256"]
        or digest(evidence / "audit.json") != cloud["remote_audit_sha256"]
        or digest(Path("reports/kaggle_local_reaudit_20261030.json")) != cloud["local_audit_sha256"]
        or len((evidence / "resume.txt").read_text(encoding="utf-8").splitlines()) != 14
    ):
        raise ValueError("C11 saved evidence no longer matches the live-run receipts")
    audit = read(evidence / "audit.json")
    if not audit["passed"] or not audit["complete"] or audit["failures"]:
        raise ValueError("C11 complete-matrix audit did not pass")
    gates["C11"] = (
        "private live vLLM run, checked assets, complete matrix/resume and measured GPU allocation"
    )
    ci = read("reports/track_c_portable_ci_final_20261030.json")
    expected_platforms = {
        "track-c-macos-latest",
        "track-c-ubuntu-latest",
        "track-c-windows-latest",
    }
    if (
        ci["source_sha256"] != source_identity()["sha256"]
        or ci["conclusion"] != "success"
        or len(ci["jobs"]) != 3
        or {j["platform"] for j in ci["jobs"]} != expected_platforms
        or any(
            j["errors"] or j["failures"] or j["skipped"] or j["passed"] < 724 for j in ci["jobs"]
        )
    ):
        raise ValueError("native Windows/Linux/macOS acceptance matrix is incomplete")
    return {
        "status": "Phase 1 Track C deliverables complete",
        "passed": True,
        "gates": gates,
        "model": selection["model"],
        "model_revision": selection["revision"],
        "safety": safety,
        "native_ci": ci,
        "live_kaggle": cloud,
        "limits": [
            "Synthetic model/action/safety diagnostics are not research gold.",
            "Assistant safety review is not independent human adjudication.",
            "Passing checks establish these executions, not an absence of all possible future defects.",
            "Full scientific sweeps and human support/reference results remain later-phase work.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/phase1_track_c_acceptance_20261030.json")
    )
    args = parser.parse_args()
    try:
        result = validate()
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Track C acceptance failed: {exc}\n")
    write_json(args.output, result)
    print(
        json.dumps(
            {"status": result["status"], "passed": result["passed"], "gates": result["gates"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
