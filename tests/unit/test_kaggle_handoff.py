"""Transferred assets fail closed; a GPU run cannot race model-server startup."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from conditions.assets import verify_assets
from conditions.provenance import digest, write_json
from eval.safety import load_safety_prompts, response_digest, score_review

spec = importlib.util.spec_from_file_location(
    "kaggle_run", Path(__file__).parents[2] / "scripts/kaggle_run.py"
)
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def test_transferred_asset_checks_hash_and_size(tmp_path):
    artifact = tmp_path / "vectors.json"
    artifact.write_text("fixture", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_json(
        manifest,
        {"version": 1, "files": {"vectors.json": {"sha256": digest(artifact), "bytes": 7}}},
    )
    assert verify_assets(tmp_path, manifest) == {"vectors.json": digest(artifact)}
    artifact.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        verify_assets(tmp_path, manifest)
    artifact.unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_assets(tmp_path, manifest)


def test_readiness_wait_detects_failed_server_and_retries_transport(monkeypatch):
    process = Mock()
    process.poll.return_value = 1
    with pytest.raises(RuntimeError, match="exited"):
        handoff.wait_for_server(process, "http://localhost:8000/v1")
    process.poll.return_value = None
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.status = 200
    response.read.return_value = json.dumps({"data": [{"id": "fixture"}]}).encode()
    transport = Mock(side_effect=[OSError("not ready"), response])
    monkeypatch.setattr(handoff, "urlopen", transport)
    monkeypatch.setattr(handoff.time, "sleep", lambda _: None)
    assert (
        handoff.wait_for_server(process, "http://localhost:8000/v1")["data"][0]["id"] == "fixture"
    )
    assert transport.call_count == 2


def test_safety_review_cannot_hide_missing_risks_or_claim_wrong_response_bytes():
    prompts = load_safety_prompts()
    outputs = {p["prompt_id"]: "I cannot follow that request." for p in prompts}
    rows = [
        {
            "prompt_id": p["prompt_id"],
            "reason": "Refusal",
            "advice": False,
            "own_forecast": False,
            "post_date_evidence": False,
            "asserted_without_span": False,
        }
        for p in prompts
    ]
    review = {
        "reviewer": "Assistant fixture",
        "reviewer_type": "assistant",
        "reviewed_on": "2026-10-30",
        "responses_sha256": response_digest(outputs),
        "judgments": rows,
    }
    result = score_review(prompts, outputs, review)
    assert result["reviewer_type"] == "assistant" and all(n == 0 for n in result["counts"].values())
    outputs[prompts[0]["prompt_id"]] = "Changed answer"
    with pytest.raises(ValueError, match="unchanged"):
        score_review(prompts, outputs, review)
