"""Reconcile saved Kaggle timing evidence without inventing quota or active GPU time."""

import json
from datetime import datetime
from pathlib import Path

from conditions.provenance import digest, write_json


def notebook_timing(path: Path) -> dict:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    intervals = []
    for index, cell in enumerate(notebook["cells"]):
        execution = cell.get("metadata", {}).get("execution", {})
        start, end = execution.get("iopub.status.busy"), execution.get("iopub.status.idle")
        if start and end:
            seconds = (
                datetime.fromisoformat(end.replace("Z", "+00:00"))
                - datetime.fromisoformat(start.replace("Z", "+00:00"))
            ).total_seconds()
            if seconds < 0:
                raise ValueError("saved notebook interval ends before it starts")
            intervals.append({"cell": index, "start": start, "end": end, "seconds": seconds})
    return {
        "notebook": str(path),
        "sha256": digest(path),
        "executed_intervals": intervals,
        "summed_cell_wall_seconds": sum(i["seconds"] for i in intervals),
        "gpu_active_hours": None,
        "billed_or_allocated_gpu_hours": None,
        "scope": "saved cell wall timestamps; inter-cell idle and full session allocation are not measured",
    }


def main():
    paths = [Path("notebooks/c1_live_verification.ipynb"), Path("notebooks/c2_model_pilot.ipynb")]
    report = {
        "status": "reconciled historical Kaggle execution evidence",
        "notebooks": [notebook_timing(p) for p in paths],
        "new_kaggle_runs": 0,
        "notes": [
            "The exported notebook GPU-enabled metadata is false, but saved CUDA/device and successful inference outputs establish earlier GPU execution.",
            "C1 saved output detects two visible GPUs; the pilot reports Tesla T4, with no complete allocation receipt.",
            "Cell wall time is not converted into invented GPU-active or billed hours.",
            "scripts/kaggle_run.py now records visible allocated GPU-hours from its own measured interval and visible device count, including failure cleanup.",
        ],
    }
    write_json(Path("reports/kaggle_compute_evidence_20261030.json"), report)
    for item in report["notebooks"]:
        print(item["notebook"], item["summed_cell_wall_seconds"])


if __name__ == "__main__":
    main()
