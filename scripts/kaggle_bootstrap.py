"""Private two-T4 C11 verification entrypoint, including setup in its time budget."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    started = time.monotonic()
    output = Path("/kaggle/working/track_c_run")
    output.mkdir(parents=True, exist_ok=True)
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "purpose": "C11 fresh engineering smoke; independent of the C2 model-choice experiment",
        "maximum_notebook_seconds": 3600,
        "maximum_allocated_gpu_hours": 2,
    }
    compute = output / "bootstrap_compute.json"
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=True,
    )
    devices = [line.strip() for line in gpu.stdout.splitlines() if line.strip()]
    if len(devices) != 2:
        raise RuntimeError("this private verification requires the authorized two-GPU session")
    record["devices"] = devices
    record["gpu_count"] = len(devices)

    def remaining():
        seconds = 3300 - (time.monotonic() - started)
        if seconds < 60:
            raise TimeoutError("C11 setup/run has reached its notebook time budget")
        return seconds

    def command(args, **kwargs):
        subprocess.run(args, check=True, timeout=remaining(), **kwargs)

    try:
        compute.write_text(json.dumps(record, indent=2) + "\n")
        roots = sorted(Path("/kaggle/input").rglob("pyproject.toml"))
        if len(roots) != 1:
            raise ValueError("attach exactly one source dataset with pyproject.toml")
        project = Path("/kaggle/working/lma-grounding-decay")
        shutil.copytree(roots[0].parent, project, dirs_exist_ok=True)
        manifests = sorted(Path("/kaggle/input").rglob("bundle_manifest.json"))
        if len(manifests) == 1:
            shutil.copytree(manifests[0].parent / "data", project / "data", dirs_exist_ok=True)
        else:
            archives = sorted(Path("/kaggle/input").rglob("kaggle_data_v7.zip"))
            if len(archives) != 1:
                raise ValueError("attach the checksum-verified frozen v7 data dataset")
            with zipfile.ZipFile(archives[0]) as archive:
                for member in archive.namelist():
                    if member.startswith("/") or ".." in Path(member).parts:
                        raise ValueError("unsafe archive member")
                archive.extractall(project)
        os.chdir(project)
        env = {
            **os.environ,
            "PYTHONPATH": str(project / "src"),
            "HF_HOME": "/tmp/lma-model-cache",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "PYTHONUTF8": "1",
        }
        # Audio is unused; removing a base-image binary built for another torch
        # avoids the mismatch preserved in the earlier C1 notebook.
        command([sys.executable, "-m", "pip", "uninstall", "-y", "torchaudio"], env=env)
        command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-e",
                ".[dev]",
                "vllm==0.32.0",
                "sentence-transformers==6.2.0",
                "faiss-cpu==1.15.1",
                "pymupdf==2.0",
                "trafilatura>=2.0",
            ],
            env=env,
        )
        download = (
            "from huggingface_hub import snapshot_download; "
            "snapshot_download('BAAI/bge-m3',revision='5617a9f61b028005a4858fdac845db406aefb181'); "
            "snapshot_download('BAAI/bge-reranker-v2-m3',revision='953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e')"
        )
        command([sys.executable, "-c", download], env=env)
        command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/unit/test_phase1_track_c_regressions.py",
                "tests/unit/test_retrieval_worker.py",
                "tests/unit/test_pipeline_integration.py",
                "tests/unit/test_connected_runs.py",
            ],
            env=env,
        )
        queries = Path("data/eval/phase1_kaggle_smoke_queries.jsonl")
        rows = Path("data/eval/development_candidates.jsonl").read_text().splitlines()
        queries.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
        command(
            [
                sys.executable,
                "scripts/kaggle_run.py",
                "--model",
                "JunHowie/Qwen3-8B-GPTQ-Int4",
                "--revision",
                "f08c8ea5f60e1fe34ff4a45edb58e8ca958560c3",
                "--queries",
                str(queries),
                "--conditions",
                "B0",
                "B1",
                "B1-R",
                "B2",
                "A-NoVerify",
                "A-NoLoop",
                "M",
                "--max-run-seconds",
                str(int(min(3000, remaining() - 30))),
                "--output",
                str(output),
            ],
            env=env,
        )
        record["status"] = (
            "passed: fresh vLLM, selected retrieval, 14 graphs, bound audit and unchanged resume"
        )
    except Exception as exc:
        record.update(status="failed", error=str(exc))
        raise
    finally:
        elapsed = time.monotonic() - started
        record.update(
            finished_at=datetime.now(UTC).isoformat(),
            elapsed_seconds=elapsed,
            visible_allocated_gpu_hours=len(devices) * elapsed / 3600,
            gpu_active_hours=None,
            scope="measured entrypoint interval including setup; provider startup/teardown outside code is excluded",
        )
        compute.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
