"""Bind resumed runs to all runtime source, configuration, data and artifacts."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from schema import Graph


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def source_identity(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parents[1]
    files = {
        str(p.relative_to(root)): digest(p)
        for package in (
            "agent",
            "conditions",
            "corpus",
            "eval",
            "extract",
            "llm",
            "retrieval",
            "schema",
            "tools",
            "verify",
        )
        for p in sorted((root / package).rglob("*"))
        if p.is_file() and p.suffix in {".py", ".yaml"}
    }
    return {
        "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "files": files,
    }


def model_identity(path: Path) -> dict:
    """Hash actual local model files, following cached snapshot links."""
    if not path.is_dir():
        raise ValueError(f"local model directory does not exist: {path}")
    return {
        str(p.relative_to(path)): digest(p)
        for p in sorted(path.rglob("*"))
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(path).parts)
    }


def runtime_identity(python: str | None = None) -> dict:
    if python:
        result = subprocess.run(
            [
                python,
                "-c",
                "import importlib.metadata,json,platform; print(json.dumps({'python': platform.python_version(), 'packages': sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions())}))",
            ],
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        )
        identity = json.loads(result.stdout)
    else:
        identity = {
            "python": platform.python_version(),
            "packages": sorted(
                [d.metadata["Name"], d.version] for d in importlib.metadata.distributions()
            ),
        }
    executable = Path(python or sys.executable).absolute()
    return {**identity, "executable": str(executable), "executable_sha256": digest(executable)}


def validate_cached(payload: dict, *, query, condition: str, inputs_sha256: str):
    graph = Graph.model_validate(payload["graph"])
    if (
        graph.query_id != query.query_id
        or graph.condition != condition
        or graph.as_of != query.as_of
        or graph.anchor.var != query.anchor.var
        or graph.anchor.direction != query.anchor.direction
        or graph.anchor.event != query.anchor.event
        or graph.anchor.event_date != query.anchor.event_date
        or not graph.run_id
        or payload.get("inputs_sha256") != inputs_sha256
    ):
        raise ValueError("cached artifact does not match its query, condition or run inputs")
    if (
        not isinstance(payload.get("log_file"), str)
        or Path(payload["log_file"]).name != payload["log_file"]
        or payload.get("log_sha256") is None
    ):
        raise ValueError("cached artifact has no bound execution log")
    if not set(payload["established_edge_ids"]) <= {e.edge_id for e in graph.edges}:
        raise ValueError("cached artifact has unknown established edges")
    return graph
