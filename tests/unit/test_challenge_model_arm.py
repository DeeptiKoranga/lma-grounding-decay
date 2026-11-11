"""Detection rules for the challenge set's model arm.

The arm cannot run here -- it needs the model and the corpus -- so these cover
the part that decides what the run means. The rule that matters is that
`inflated_strength` is not scored on provenance: the underlying edge is real,
so a correct verifier returns source-asserted, and reading provenance would
record zero detections for a verifier doing exactly the right thing.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from llm.generate import Completion
from schema import Edge, Provenance, Strength, VerifyVerdict, iter_run_log

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "run_challenge_model_arm", REPO / "scripts/run_challenge_model_arm.py"
)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


def _edge(strength="conditional", direction="up"):
    return Edge(
        edge_id="e1",
        src_var="BRENT",
        dst_var="INR_USD",
        direction=direction,
        provenance="source_asserted",
        strength=strength,
        hop=1,
        evidence_span="crude pushed the rupee lower",
        evidence_doc_id="doc",
        evidence_passage_id="doc#p1",
        evidence_published_at=date(2026, 3, 1),
    )


def _result(verdict, provenance, strength=None):
    return SimpleNamespace(verdict=verdict, provenance=provenance, strength=strength)


def test_a_reversed_edge_is_caught_when_the_verifier_refuses_to_source_it():
    hit, _ = module.flagged(
        "reversed_relation",
        _edge(),
        _result(VerifyVerdict.CONTRADICTED, Provenance.MODEL_INFERRED),
    )
    assert hit


def test_unsupported_also_counts_for_a_reversed_edge():
    """Either verdict keeps the edge out of a graph as sourced, which is what
    the corruption was trying to achieve."""
    hit, _ = module.flagged(
        "reversed_relation",
        _edge(),
        _result(VerifyVerdict.UNSUPPORTED, Provenance.MODEL_INFERRED),
    )
    assert hit


def test_a_reversed_edge_the_verifier_sources_anyway_is_a_miss():
    hit, _ = module.flagged(
        "reversed_relation",
        _edge(),
        _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.DIRECT),
    )
    assert not hit


def test_inflated_strength_is_caught_by_the_strength_returned_not_by_provenance():
    """The claim is conditional-presented-as-direct over a genuine edge. A
    correct verifier sources it and returns the weaker label; scoring provenance
    would call that a miss."""
    hit, why = module.flagged(
        "inflated_strength",
        _edge(strength=Strength.DIRECT),
        _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.CONDITIONAL),
    )
    assert hit, "a verifier that refused the inflation was scored as missing it"
    assert "conditional" in why and "direct" in why


def test_agreeing_with_an_inflated_strength_is_a_miss():
    hit, _ = module.flagged(
        "inflated_strength",
        _edge(strength=Strength.DIRECT),
        _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.DIRECT),
    )
    assert not hit


def test_a_stronger_label_than_claimed_is_not_a_detection():
    """Only a weaker label means the inflation was refused. Returning something
    stronger is a different error and must not be counted as a catch."""
    hit, _ = module.flagged(
        "inflated_strength",
        _edge(strength=Strength.CONDITIONAL),
        _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.DIRECT),
    )
    assert not hit


def test_an_inflated_item_without_a_strength_is_not_a_detection():
    hit, why = module.flagged(
        "inflated_strength",
        _edge(strength=Strength.DIRECT),
        _result(VerifyVerdict.UNSUPPORTED, Provenance.MODEL_INFERRED, None),
    )
    assert not hit and "no weaker strength" in why


def test_a_clean_control_the_verifier_sources_is_not_a_false_alarm():
    hit, _ = module.flagged(
        "control",
        _edge(),
        _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.CONDITIONAL),
    )
    assert not hit


def test_a_clean_control_the_verifier_rejects_is_a_false_alarm():
    hit, _ = module.flagged(
        "control", _edge(), _result(VerifyVerdict.UNSUPPORTED, Provenance.MODEL_INFERRED)
    )
    assert hit


def test_strength_disagreement_on_a_control_is_not_counted_as_a_false_alarm():
    """Calling a conditional edge correlational is a different error from
    rejecting a sound citation, and the proposal's false-alarm rate is the
    second. It is reported, separately."""
    edge = _edge(strength=Strength.CONDITIONAL)
    result = _result(VerifyVerdict.SUPPORTED, Provenance.SOURCE_ASSERTED, Strength.CORRELATIONAL)
    hit, _ = module.flagged("control", edge, result)
    assert not hit
    assert module.strength_disagreement(edge, result)


def test_summarise_separates_errors_from_misses():
    """An unparseable judgment is not a miss. Counting it as one would make a
    flaky parser look like a permissive verifier."""
    rows = [
        {"item_id": "a", "kind": "reversed_relation", "flagged": True, "verdict": "contradicted"},
        {"item_id": "b", "kind": "reversed_relation", "flagged": False, "verdict": "supported"},
        {"item_id": "c", "kind": "reversed_relation", "error": "unparseable judgment"},
    ]
    summary = module.summarise(rows)["reversed_relation"]
    assert summary["total"] == 3
    assert summary["scored"] == 2
    assert summary["errors"] == 1
    assert summary["rate"] == 0.5


def test_the_report_leads_with_the_semantic_number(monkeypatch):
    summary = {
        "reversed_relation": {
            "total": 23,
            "scored": 23,
            "flagged": 18,
            "errors": 0,
            "rate": 0.783,
            "strength_disagreements": 0,
            "verdicts": {},
        },
        "inflated_strength": {
            "total": 15,
            "scored": 15,
            "flagged": 9,
            "errors": 0,
            "rate": 0.6,
            "strength_disagreements": 0,
            "verdicts": {},
        },
        "control": {
            "total": 23,
            "scored": 23,
            "flagged": 1,
            "errors": 0,
            "rate": 0.043,
            "strength_disagreements": 3,
            "verdicts": {},
        },
    }
    text = module.render(summary)
    assert "27 of 38 semantic corruptions caught" in text
    assert "0 of 38" in text, "the rules-arm baseline must sit beside it"
    assert "False-alarm rate on the 23 clean controls: 0.043" in text
    assert "Strength disagreements on controls" in text


@pytest.mark.parametrize("kind", list(module.SEMANTIC))
def test_the_semantic_families_are_the_ones_the_rules_cannot_see(kind):
    from eval.challenge import CORRUPTIONS

    assert kind in CORRUPTIONS


def test_runner_uses_date_cutoff_and_records_model_calls(tmp_path, monkeypatch, graph, passages):
    edge = graph.edges[0]
    passage = next(p for p in passages if p.passage_id == edge.evidence_passage_id)
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(passage.model_dump_json() + "\n", encoding="utf-8")
    items = tmp_path / "items.jsonl"
    items.write_text(
        json.dumps(
            {
                "item_id": "control",
                "query_id": graph.query_id,
                "passage_id": passage.passage_id,
                "edge": edge.model_dump(mode="json"),
                "as_of": str(graph.as_of),
                "proposed_corruption": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    reply = Completion(
        json.dumps(
            {
                "verdict": "supported",
                "direction": edge.direction,
                "strength": edge.strength,
                "reason": "test fixture",
            }
        ),
        "mock",
        "mlx",
        20,
        10,
        1.0,
    )
    monkeypatch.setattr(
        module,
        "MLXGenerator",
        lambda *args, **kwargs: SimpleNamespace(generate=lambda *a, **kw: reply),
    )
    monkeypatch.setattr(module, "model_identity", lambda _: {})
    monkeypatch.setattr(module, "runtime_identity", dict)
    output = tmp_path / "run"
    args = [
        "--corpus",
        str(corpus),
        "--items",
        str(items),
        "--revision",
        "test",
        "--output",
        str(output),
        "--report",
        str(tmp_path / "report.md"),
        "--resume",
    ]
    assert module.main(args) == 0
    row = json.loads((output / "results.jsonl").read_text(encoding="utf-8"))
    assert row["flagged"] is False
    log = iter_run_log(output / row["log_file"])
    assert len(log) == 1 and log[0].query_id == "control" and log[0].json_valid
    assert module.main(args) == 0
    with pytest.raises(SystemExit):
        module.main([*args, "--revision", "changed"])
    with pytest.raises(SystemExit):
        module.main(args[:-1])
    assert len((output / "results.jsonl").read_text(encoding="utf-8").splitlines()) == 1
