"""The JSON Schemas in `docs/schemas/` are a published contract, so they must not drift.

If this fails you changed a model without regenerating. Run `make schemas` and
commit the diff in the same PR, so the other two tracks see what moved.
"""

from __future__ import annotations

import json

import pytest

from schema.export_schemas import EXPORTS, SCHEMA_DIR, build_schemas

EXPECTED = {
    "passage.schema.json",
    "edge.schema.json",
    "graph.schema.json",
    "tool_call.schema.json",
    "tool_result.schema.json",
    "run_log_line.schema.json",
}


def test_all_five_frozen_records_are_exported():
    assert set(build_schemas()) == EXPECTED
    assert set(EXPORTS) == {name.removesuffix(".schema.json") for name in EXPECTED}


def test_schema_directory_holds_exactly_those_files():
    assert {p.name for p in SCHEMA_DIR.glob("*.json")} == EXPECTED


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_exported_schema_matches_the_model(name: str):
    on_disk = (SCHEMA_DIR / name).read_text(encoding="utf-8")
    assert on_disk == build_schemas()[name], f"{name} is stale; run `make schemas`"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_exported_schema_is_valid_json_with_an_id(name: str):
    payload = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    assert payload["$schema"].startswith("https://json-schema.org/")
    assert payload["$id"].endswith(name)


def test_tool_call_schema_is_a_discriminated_union():
    payload = json.loads((SCHEMA_DIR / "tool_call.schema.json").read_text(encoding="utf-8"))
    assert "oneOf" in payload
    assert len(payload["oneOf"]) == 6


def test_edge_schema_names_the_three_strength_levels():
    text = (SCHEMA_DIR / "edge.schema.json").read_text(encoding="utf-8")
    for label in ("direct", "conditional", "correlational"):
        assert label in text
