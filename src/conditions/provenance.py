"""Bind resumed runs to all runtime source, configuration, data and artifacts."""

import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from schema import Graph


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_json(path: Path, value) -> None:
    """Write identical UTF-8/LF bytes on every platform before computing receipts."""
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def artifact_receipts(path: Path) -> dict[str, str]:
    """Read older Windows receipt keys without relaxing artifact byte checks."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("artifact receipts must be an object")
    result = {}
    for address, checksum in raw.items():
        if not isinstance(address, str):
            raise ValueError("artifact receipt address must be a string")
        key = address.replace("\\", "/")
        parts = PurePosixPath(key).parts
        if (
            len(parts) != 2
            or PurePosixPath(key).is_absolute()
            or any(part in {".", ".."} or ":" in part for part in parts)
            or not key.endswith(".json")
            or not isinstance(checksum, str)
            or re.fullmatch(r"[0-9a-f]{64}", checksum) is None
            or key in result
        ):
            raise ValueError("invalid or duplicate artifact receipt address/checksum")
        result[key] = checksum
    return result


def source_identity(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parents[1]
    files = {
        p.relative_to(root)
        .as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n"))
        .hexdigest()
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
        p.relative_to(path).as_posix(): digest(p)
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
        or any(separator in payload["log_file"] for separator in ("/", "\\"))
        or Path(payload["log_file"]).name != payload["log_file"]
        or payload.get("log_sha256") is None
    ):
        raise ValueError("cached artifact has no bound execution log")
    if not set(payload["established_edge_ids"]) <= {e.edge_id for e in graph.edges}:
        raise ValueError("cached artifact has unknown established edges")
    return graph
