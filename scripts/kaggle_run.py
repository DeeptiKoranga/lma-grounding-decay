"""Validated vLLM handoff with readiness polling, resume audit and GPU allocation log."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from conditions.assets import verify_assets
from conditions.provenance import runtime_identity, write_json


def wait_for_server(process, url: str, *, timeout=600, poll_interval=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("vLLM exited during startup; inspect vllm.log")
        try:
            with urlopen(url.rstrip("/") + "/models", timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read())
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(poll_interval)
    raise RuntimeError("vLLM did not become ready within the startup budget")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", required=True, help="vLLM-compatible model repository, not MLX weights"
    )
    parser.add_argument("--revision", required=True, help="Immutable Hugging Face commit")
    parser.add_argument(
        "--manifest", type=Path, default=Path("reports/kaggle_data_manifest_20261030.json")
    )
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working/track_c_run"))
    parser.add_argument("--queries", default="data/eval/development_candidates.jsonl")
    parser.add_argument("--conditions", nargs="+", default=["B0", "B1", "B2", "M"])
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--max-run-seconds", type=int, default=3000)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.revision) is None:
        parser.error("--revision must be the immutable 40-character model commit")
    if not 60 <= args.max_run_seconds <= 3300:
        parser.error("--max-run-seconds must be between 60 and 3300")
    verified = verify_assets(Path.cwd(), args.manifest)
    if args.verify_only:
        print(json.dumps({"verified_assets": verified}, indent=2))
        return
    import torch

    count = torch.cuda.device_count()
    if count < 1:
        raise RuntimeError("Kaggle GPU acceleration is not enabled")
    if count > 2:
        raise RuntimeError("this verification is authorized for at most two GPUs")
    args.output.mkdir(parents=True, exist_ok=True)
    allocation_path = args.output / f"compute-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "gpu_count": count,
        "devices": [torch.cuda.get_device_name(i) for i in range(count)],
        "model": args.model,
        "revision": args.revision,
        "verified_assets": verified,
        "runtime": runtime_identity(),
        "scope": "visible GPU allocation interval; GPU-active time and prior notebook allocation excluded",
    }
    started, server = time.monotonic(), None

    def remaining_seconds():
        remaining = args.max_run_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("Kaggle verification reached its execution budget")
        return remaining

    write_json(allocation_path, {**record, "status": "running"})
    env = {**os.environ, "PYTHONPATH": str(Path("src").resolve())}
    try:
        with (args.output / "vllm.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "vllm.entrypoints.openai.api_server",
                    "--model",
                    args.model,
                    "--revision",
                    args.revision,
                    "--tensor-parallel-size",
                    str(count),
                    "--dtype",
                    "half",
                    "--max-model-len",
                    "12000",
                    "--port",
                    "8000",
                    "--max-num-seqs",
                    "1",
                    "--gpu-memory-utilization",
                    "0.85",
                    "--enforce-eager",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )
        record["served_models"] = wait_for_server(
            server, "http://127.0.0.1:8000/v1", timeout=min(600, remaining_seconds())
        )
        command = [
            sys.executable,
            "-m",
            "conditions",
            "--queries",
            args.queries,
            "--conditions",
            *args.conditions,
            "--backend",
            "vllm",
            "--base-url",
            "http://127.0.0.1:8000/v1",
            "--model",
            args.model,
            "--revision",
            args.revision,
            "--retrieval-python",
            sys.executable,
            "--output",
            str(args.output / "runs"),
            "--resume",
        ]
        if "B1-R" in args.conditions:
            command += ["--reranker-python", sys.executable]
        subprocess.run(command, check=True, env=env, timeout=remaining_seconds())
        subprocess.run(
            [
                sys.executable,
                "-m",
                "eval.run_audit",
                "--runs",
                str(args.output / "runs"),
                "--output",
                str(args.output / "audit.json"),
            ],
            check=True,
            env=env,
            timeout=remaining_seconds(),
        )
        subprocess.run(command, check=True, env=env, timeout=remaining_seconds())
        record["status"] = "passed: complete matrix, bound audit and unchanged resume"
    except Exception as exc:
        record.update(status="failed", error=str(exc))
        raise
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        elapsed = time.monotonic() - started
        record.update(
            finished_at=datetime.now(UTC).isoformat(),
            elapsed_seconds=elapsed,
            visible_allocated_gpu_hours=count * elapsed / 3600,
            gpu_active_hours=None,
        )
        write_json(allocation_path, record)


if __name__ == "__main__":
    main()
