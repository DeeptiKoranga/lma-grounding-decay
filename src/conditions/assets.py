"""Verify transferred inputs before a GPU session spends time loading models."""

import json
from pathlib import Path, PurePosixPath

from .provenance import digest


def verify_assets(root: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or not manifest.get("files"):
        raise ValueError("asset manifest is empty or has an unsupported version")
    verified = {}
    for name, expected in manifest["files"].items():
        address = PurePosixPath(name)
        if address.is_absolute() or ".." in address.parts or "\\" in name or ":" in name:
            raise ValueError("asset address must be a safe project-relative path")
        path = root.joinpath(*address.parts)
        if not path.is_file():
            raise ValueError(f"missing transferred asset: {name}")
        if path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]:
            raise ValueError(f"transferred asset checksum mismatch: {name}")
        verified[name] = expected["sha256"]
    return verified
