"""Cross-component failures reported during the Phase 1 Track C audit."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from conditions.pipeline import Pipeline, Query
from conditions.provenance import artifact_receipts, source_identity, write_json
from corpus.series import SeriesStore
from llm.generate import AnthropicGenerator, Completion
from retrieval.bm25 import Aliases, BM25Retriever
from schema import Anchor, Edge, iter_run_log
from schema.tools import VerifyEdgeResult
from tools.runtime import ToolRuntime
from verify.llm_verifier import Verifier
from verify.paths import rebuild

ROOT = Path(__file__).parents[2]


def query():
    return Query(
        query_id="phase1",
        query="Brent Indian basket crude",
        as_of=date(2026, 3, 20),
        anchor=Anchor(
            var="BRENT", direction="up", event="Fixture oil move", event_date=date(2026, 3, 12)
        ),
    )


@pytest.mark.parametrize("condition", ["B0", "M"])
def test_native_claude_completion_survives_actual_pipeline_logging(
    monkeypatch, tmp_path, condition
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=-1):
            return json.dumps(
                {
                    "content": [{"type": "text", "text": '{"edges":[]}'}],
                    "usage": {"input_tokens": 10, "output_tokens": 4},
                }
            ).encode()[:limit]

    monkeypatch.setattr("llm.generate.urlopen", lambda *a, **k: Response())
    retriever = BM25Retriever.from_jsonl(ROOT / "tests/fixtures/passages.jsonl")
    path = tmp_path / "claude.jsonl"
    result = Pipeline(
        generator=AnthropicGenerator(api_key="offline-test-key"),
        retriever=retriever,
        series=SeriesStore({}),
    ).run(query(), condition=condition, run_id="test", log_path=path)
    records = iter_run_log(path)
    calls = [r for r in records if r.event == "model_call"]
    assert calls and all(r.backend == "claude" and r.prompt_tokens == 10 for r in calls)
    assert records[-1].reason != "error"
    assert result["graph"]["condition"] == condition


@pytest.mark.parametrize("explicit_provenance", [False, True])
def test_verified_strength_cannot_change_without_new_approval(explicit_provenance):
    class Conditional:
        def generate(self, *args, **kwargs):
            return Completion(
                json.dumps(
                    {
                        "verdict": "supported",
                        "direction": "up",
                        "strength": "conditional",
                        "reason": "fixture",
                    }
                ),
                "fixture",
                "api",
                1,
                1,
                0,
            )

    retriever = BM25Retriever.from_jsonl(
        ROOT / "tests/fixtures/passages.jsonl", aliases=Aliases.load(ROOT / "data/aliases.yaml")
    )
    q = query()
    edge = Edge(
        edge_id="e",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="conditional",
        provenance="model_inferred",
        hop=1,
    )
    runtime = ToolRuntime(
        graph=rebuild(query_id=q.query_id, anchor=q.anchor, as_of=q.as_of, edges=[edge]),
        retriever=retriever,
        series=SeriesStore({}),
        verifier=Verifier(Conditional(), list(retriever.passages)),
    )
    pid = "bl-2026-03-12-brent100#p1"
    runtime.seen.add(pid)
    assert (
        runtime.call("verify_edge", edge_id="e", passage_ids=[pid], as_of=q.as_of).provenance
        == "source_asserted"
    )
    assert runtime.call(
        "update_graph", op="relabel_edge", edge_id="e", provenance="source_asserted"
    ).ok
    args = {"provenance": "source_asserted"} if explicit_provenance else {}
    rejected = runtime.call(
        "update_graph", op="relabel_edge", edge_id="e", strength="direct", **args
    )
    assert not rejected.ok and "verifier strength" in rejected.error.message
    assert runtime.graph.edges[0].strength == "conditional"
    assert runtime.call("update_graph", op="relabel_edge", edge_id="e", strength="conditional").ok
    assert runtime.call(
        "update_graph", op="relabel_edge", edge_id="e", provenance="model_inferred"
    ).ok
    assert runtime.graph.edges[0].verified_by is None and not runtime.approved
    assert not runtime.call(
        "update_graph", op="relabel_edge", edge_id="e", provenance="source_asserted"
    ).ok


@pytest.mark.parametrize(
    "changes",
    [
        {"evidence_span": None},
        {"strength": None},
        {"direction": None},
        {"verdict": "unsupported"},
        {"evidence_passage_id": None},
    ],
)
def test_verify_edge_cannot_claim_assertion_with_incomplete_proof(changes):
    payload = {
        "call_id": "v",
        "edge_id": "e",
        "verdict": "supported",
        "provenance": "source_asserted",
        "strength": "direct",
        "direction": "up",
        "evidence_span": "a source quote",
        "evidence_passage_id": "fixture#p1",
    }
    with pytest.raises(ValidationError, match="complete evidence"):
        VerifyEdgeResult(**{**payload, **changes})


def test_receipts_accept_legacy_windows_keys_but_reject_aliases_and_tampering(tmp_path):
    path = tmp_path / "artifacts.json"
    write_json(path, {"M\\q.json": "a" * 64})
    assert artifact_receipts(path) == {"M/q.json": "a" * 64}
    write_json(path, {"M\\q.json": "a" * 64, "M/q.json": "b" * 64})
    with pytest.raises(ValueError, match="duplicate"):
        artifact_receipts(path)
    write_json(path, {"../q.json": "a" * 64})
    with pytest.raises(ValueError):
        artifact_receipts(path)


def test_source_identity_survives_windows_line_endings_and_json_bytes_are_fixed(tmp_path):
    module = tmp_path / "agent/example.py"
    module.parent.mkdir()
    module.write_bytes(b"first\nsecond\n")
    original = source_identity(tmp_path)
    module.write_bytes(b"first\r\nsecond\r\n")
    assert source_identity(tmp_path) == original
    assert list(original["files"]) == ["agent/example.py"]
    target = tmp_path / "unicode.json"
    write_json(target, {"text": "rupee ₹ →"})
    assert b"\r\n" not in target.read_bytes()
    assert json.loads(target.read_text(encoding="utf-8"))["text"] == "rupee ₹ →"


def test_new_rejected_verification_invalidates_old_approval():
    class ChangingVerifier:
        calls = 0

        def verify(self, edge, *, passage, span, as_of, call_id):
            self.calls += 1
            if self.calls == 1:
                return VerifyEdgeResult(
                    call_id=call_id,
                    edge_id=edge.edge_id,
                    verdict="supported",
                    provenance="source_asserted",
                    strength="conditional",
                    direction="up",
                    evidence_span=span,
                    evidence_passage_id=passage.passage_id,
                )
            return VerifyEdgeResult(
                call_id=call_id,
                edge_id=edge.edge_id,
                verdict="unsupported",
                provenance="model_inferred",
            )

    retriever = BM25Retriever.from_jsonl(ROOT / "tests/fixtures/passages.jsonl")
    q = query()
    edge = Edge(
        edge_id="e",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="conditional",
        provenance="model_inferred",
        hop=1,
    )
    tools = ToolRuntime(
        graph=rebuild(query_id=q.query_id, anchor=q.anchor, as_of=q.as_of, edges=[edge]),
        retriever=retriever,
        series=SeriesStore({}),
        verifier=ChangingVerifier(),
    )
    pid = "bl-2026-03-12-brent100#p1"
    tools.seen.add(pid)
    assert (
        tools.call("verify_edge", edge_id="e", passage_ids=[pid], as_of=q.as_of).verdict
        == "supported"
    )
    assert tools.approved
    assert (
        tools.call("verify_edge", edge_id="e", passage_ids=[pid], as_of=q.as_of).verdict
        == "unsupported"
    )
    assert not tools.approved
    assert not tools.call(
        "update_graph", op="relabel_edge", edge_id="e", provenance="source_asserted"
    ).ok
