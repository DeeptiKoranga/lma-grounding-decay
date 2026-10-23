"""Mechanical prose extraction cannot masquerade as human-corrected baseline data."""

import json
from pathlib import Path

import pytest

from eval.prose_review import export, prepare
from schema import Graph


def test_correction_gate_preserves_original_and_rejects_stale_or_incomplete_work(tmp_path):
    fixture = Path(__file__).parents[1] / "fixtures/graph_brent_hormuz.json"
    graph = Graph.model_validate_json(fixture.read_text())
    graph.condition = "B1"
    folder = tmp_path / "runs" / "B1"
    folder.mkdir(parents=True)
    original = folder / "q.json"
    payload = {
        "graph": graph.model_dump(mode="json"),
        "prose_answer": "Fixture answer",
        "established_edge_ids": ["e1"],
    }
    original.write_text(json.dumps(payload))
    corrections = tmp_path / "corrections.json"
    assert prepare(folder.parent, corrections)["baseline_items"] == 1
    with pytest.raises(ValueError, match="attestation"):
        export(runs=folder.parent, corrections=corrections, output=tmp_path / "export")
    reviewed = json.loads(corrections.read_text())
    reviewed.update(
        reviewer="Fixture reviewer", reviewed_on="2026-10-23", human_correction_attestation=True
    )
    reviewed["items"][0]["correction_complete"] = True
    corrections.write_text(json.dumps(reviewed))
    receipt = export(runs=folder.parent, corrections=corrections, output=tmp_path / "export")
    corrected = json.loads((tmp_path / "export/B1/q.json").read_text())
    assert receipt["items"] == 1
    assert corrected["baseline_correction_receipt"]["human_correction_attestation"]
    assert original.read_text() == json.dumps(payload)
    original.write_text(original.read_text() + "\n")
    with pytest.raises(ValueError, match="stale"):
        export(runs=folder.parent, corrections=corrections, output=tmp_path / "another")
