"""Export the frozen Pydantic models as JSON Schema into `docs/schemas/`.

Run with `make schemas`. The exported files are tracked in git and a test
(`tests/unit/test_exported_schemas.py`) fails when they drift from the models,
so a schema change can never land without the other two tracks seeing the diff.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from .models import Edge, Graph, Passage
from .runlog import RunLogAdapter
from .tools import ToolCallAdapter, ToolResultAdapter

__all__ = ["EXPORTS", "SCHEMA_DIR", "build_schemas", "main", "write_schemas"]

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "docs" / "schemas"

#: filename stem -> model or adapter. These are the five records frozen on Day 1.
EXPORTS: dict[str, type[BaseModel] | TypeAdapter] = {
    "passage": Passage,
    "edge": Edge,
    "graph": Graph,
    "tool_call": ToolCallAdapter,
    "tool_result": ToolResultAdapter,
    "run_log_line": RunLogAdapter,
}


def _schema_for(stem: str, model: type[BaseModel] | TypeAdapter) -> dict:
    schema = (
        model.model_json_schema(mode="serialization")
        if isinstance(model, type) and issubclass(model, BaseModel)
        else model.json_schema(mode="serialization")
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://github.com/lma-major/schemas/{stem}.schema.json",
        **schema,
    }


def build_schemas() -> dict[str, str]:
    """Return {filename: json text} without touching the disk."""
    return {
        f"{stem}.schema.json": json.dumps(_schema_for(stem, model), indent=2, sort_keys=True) + "\n"
        for stem, model in EXPORTS.items()
    }


def write_schemas(target: Path | None = None) -> list[Path]:
    directory = target or SCHEMA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in build_schemas().items():
        path = directory / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    for path in write_schemas():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
