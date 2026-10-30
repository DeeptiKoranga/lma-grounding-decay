"""Validate both complete frozen pilots and apply the pre-recorded selection rule."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from conditions.provenance import digest, write_json
from eval.model_pilot import MODEL_SPECS, SELECTION_RULE, score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=Path("runs/project_model_pilot_20261030"))
    parser.add_argument(
        "--cases", type=Path, default=Path("data/eval/project_model_pilot_cases.jsonl")
    )
    args = parser.parse_args()
    cases = [
        json.loads(line)
        for line in args.cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cases) != 100 or len({c["id"] for c in cases}) != 100:
        raise ValueError("pilot requires exactly 100 unique frozen cases")
    outputs, summaries, identities = [], {}, {}
    for name, (model, revision, _) in MODEL_SPECS.items():
        folder = args.runs / name
        inputs = json.loads((folder / "inputs.json").read_text(encoding="utf-8"))
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        if inputs["case_sha256"] != digest(args.cases) or summary["inputs_sha256"] != digest(
            folder / "inputs.json"
        ):
            raise ValueError("pilot provenance does not match frozen inputs")
        if summary["cases"] != 100 or summary["selection_rule"] != SELECTION_RULE:
            raise ValueError("pilot is incomplete or selection rule changed")
        model_outputs = []
        for case in cases:
            path = folder / f"{case['id']}.json"
            row = json.loads(path.read_text(encoding="utf-8"))
            if (row["model"], row["revision"], row["prompt"]) != (model, revision, case["prompt"]):
                raise ValueError("model, revision or prompt mismatch")
            if (
                row["case_sha256"]
                != hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()
            ):
                raise ValueError("frozen case mismatch")
            if row["scores"] != score(case, row["raw_output"]):
                raise ValueError("recorded scores do not reproduce from raw output")
            outputs.append({**row, "artifact_sha256": digest(path)})
            model_outputs.append(row)
        for task in {case["task"] for case in cases}:
            rows = [row for row in model_outputs if row["task"] == task]
            actual = {
                "n": len(rows),
                "accuracy": sum(row["scores"]["score"] for row in rows) / len(rows),
                "strict_json_validity": sum(row["scores"]["strict_json_valid"] for row in rows)
                / len(rows),
                "schema_validity": sum(row["scores"]["schema_valid"] for row in rows) / len(rows),
            }
            if summary["tasks"][task] != actual:
                raise ValueError("task summary does not reproduce from raw outputs")
        if (
            summary["mean_task_accuracy"]
            != sum(task["accuracy"] for task in summary["tasks"].values()) / 5
            or summary["prompt_tokens"] != sum(row["prompt_tokens"] for row in model_outputs)
            or summary["completion_tokens"]
            != sum(row["completion_tokens"] for row in model_outputs)
            or abs(
                summary["mean_latency_ms"]
                - sum(row["latency_ms"] for row in model_outputs) / len(model_outputs)
            )
            > 1e-6
        ):
            raise ValueError("aggregate summary does not reproduce from raw outputs")
        summaries[name] = summary
        identities[name] = inputs
    best = max(summary["mean_task_accuracy"] for summary in summaries.values())
    eligible = [
        name
        for name, summary in summaries.items()
        if summary["mean_task_accuracy"] >= best - 0.03 - 1e-12
    ]
    selected = min(eligible, key=lambda name: summaries[name]["mean_latency_ms"])
    selected_model, selected_revision, selected_dir = MODEL_SPECS[selected]
    combined = {
        "status": "complete project-schema C2 pilot",
        "cases_sha256": digest(args.cases),
        "selection_rule": SELECTION_RULE,
        "models": summaries,
        "selected": selected,
        "selection_scope": "synthetic development selection; no human research gold or hypothesis result",
        "raw_outputs": 200,
        "raw_scores_reproduced": True,
    }
    write_json(Path("reports/project_model_pilot_20261030.json"), combined)
    write_json(Path("reports/project_model_pilot_inputs_20261030.json"), identities)
    Path("data/eval/project_model_pilot_results.jsonl").write_bytes(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in outputs).encode(
            "utf-8"
        )
    )
    vllm = (
        {
            "model": "JunHowie/Qwen3-8B-GPTQ-Int4",
            "revision": "f08c8ea5f60e1fe34ff4a45edb58e8ca958560c3",
            "precision": "GPTQ Int4",
            "live_engineering_evidence": "reports/c1_live_verification_20261030.md",
        }
        if selected == "qwen3-8b"
        else {
            "model": "Qwen/Qwen3.5-9B",
            "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
            "precision": "FP16; distinct backend format; revalidate before research comparisons",
            "live_engineering_evidence": None,
        }
    )
    write_json(
        Path("configs/model_selection.json"),
        {
            "decision": "D-01",
            "resolved_on": "2026-10-30",
            "selected": selected,
            "model": selected_model,
            "revision": selected_revision,
            "model_path": "data/raw/generator/" + selected_dir,
            "backend": "mlx",
            "quantization": "affine 4-bit",
            "vllm": vllm,
            "pilot_report": "reports/project_model_pilot_20261030.json",
            "selection_rule": SELECTION_RULE,
            "scope": "one pinned model for all conditions within a sweep; format changes are separately recorded",
        },
    )
    lines = [
        "# C2 project-specific model pilot — 30 October 2026",
        "",
        "Both pinned MLX 4-bit models completed the same 100 frozen project-schema cases. "
        "These are synthetic development diagnostics, separate from research gold.",
        "",
        "Selection rule, recorded before the included runs: " + SELECTION_RULE,
        "",
        "| Model | Extraction | Strength | JSON validity | Tool choice | Unsupported edges | Mean | Mean latency (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries.values():
        values = [
            summary["tasks"][task]["accuracy"]
            for task in (
                "extraction",
                "strength",
                "json_validity",
                "tool_choice",
                "unsupported_edges",
            )
        ]
        lines.append(
            "| "
            + summary["model"]
            + " | "
            + " | ".join(f"{v:.1%}" for v in values)
            + f" | {summary['mean_task_accuracy']:.1%} | {summary['mean_latency_ms']/1000:.3f} |"
        )
    lines += [
        "",
        f"**D-01 selection: `{selected_model}`, revision `{selected_revision}`.**",
        "",
        "The extraction task requires closed-ontology variables, correct direction/strength and a "
        "verbatim quote from the supplied synthetic passage. Strength uses direct/conditional/correlational. "
        "JSON validity uses the actual Extraction schema; tool choice must parse under the actual tool schema "
        "and preserve the cutoff. Unsupported-edge cases distinguish absent relations from opposite directions.",
        "",
        "Each task has 20 cases. Schema validity is recorded separately in the JSON report. "
        "Weak extraction or tool-choice scores remain limitations of the selected model; the deterministic "
        "controller and verification guards are still required. This pilot does not prove model accuracy "
        "on the corpus or an accepted research result.",
        "",
        "Raw outputs, token counts, measured latency, model-file hashes and source/runtime identities are retained. "
        "The local MLX hardware was used as planned. The original Kaggle NF4 generic pilot is preserved in "
        "`reports/pilot_model.md`; its labels and scores are not relabelled as this pilot. "
        "An excluded preliminary prompt-ambiguity attempt is documented separately.",
        "",
        "Reproduce: run `scripts/run_model_pilot.py --model qwen3-8b`, then "
        "`--model qwen3.5-9b` in the pinned local environment with `PYTHONPATH=src`, "
        "followed by `scripts/finalize_model_pilot.py`. Resume requires the identical recorded sources, "
        "runtime, cases and model bytes. Use a new output directory after a change.",
    ]
    Path("reports/pilot_model_project_20261030.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"selected": selected, "model": selected_model, "summaries": summaries}, indent=2
        )
    )


if __name__ == "__main__":
    main()
