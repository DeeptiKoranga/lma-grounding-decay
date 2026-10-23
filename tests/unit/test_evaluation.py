"""Independent-label requirements, denominator behavior and query-paired statistics."""

import json
from pathlib import Path

import pytest

from eval.metrics import SupportJudgment, aggregate, recall_guard, score_graph
from eval.review import evaluate, prepare
from eval.safety import inspect_graph, screen_text
from eval.stats import paired_bootstrap, predeclared_contrasts
from schema import Graph

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def graph():
    return Graph.model_validate_json((FIXTURES / "graph_brent_hormuz.json").read_text())


def labels(graph):
    return {
        edge.edge_id: SupportJudgment(
            edge.edge_id not in {"e3", "e4"},
            "conditional" if edge.edge_id == "e2" else edge.strength,
        )
        for edge in graph.edges
    }


def test_uer_excludes_inferred_edges_and_strength_excludes_unsupported(graph):
    scored = score_graph(
        graph, established={"e1", "e2", "e3"}, judgments=labels(graph), reference=graph
    )
    assert scored["overall"]["uer"] == pytest.approx(1 / 3)
    assert scored["overall"]["strength_inflation"] == 0.5
    assert scored["overall"]["reference_edge_recall"] == pytest.approx(2 / 9)
    assert scored["3+"]["uer"] == 1
    assert scored["3+"]["strength_inflation"] is None


def test_abstention_does_not_become_zero_uer_or_pass_recall_guard(graph):
    scored = score_graph(graph, established=set(), judgments=labels(graph), reference=graph)
    assert scored["overall"]["uer"] is None
    assert scored["overall"]["reference_edge_recall"] == 0
    full = score_graph(graph, established={"e1"}, judgments=labels(graph))
    summary = aggregate([full, scored])
    assert summary["overall"]["uer"]["mean"] == 0
    assert summary["overall"]["uer"]["queries_without_denominator"] == 1


@pytest.mark.parametrize("m_recall,passed", [(0.0, False), (0.4, True), (None, None)])
def test_reference_recall_guard_counts_abstention_and_never_passes_missing_data(m_recall, passed):
    scores = {
        "B1": {"q": {"overall": {"reference_edge_recall": 0.5}}},
        "M": {"q": {"overall": {"reference_edge_recall": m_recall}}},
    }
    result = recall_guard(scores)
    assert result["passes_descriptively"] is passed
    if m_recall is None:
        assert result["M_minus_B1"] is None and result["paired_queries"] == 0
    else:
        assert result["M_minus_B1"] == pytest.approx(m_recall - 0.5)
    scores["M"] = {}
    assert recall_guard(scores)["passes_descriptively"] is None


def test_missing_judgments_cannot_default_to_supported(graph):
    with pytest.raises(ValueError, match="exactly"):
        score_graph(graph, established={"e1"}, judgments={})
    with pytest.raises(ValueError, match="strength"):
        SupportJudgment(True)


def test_paired_bootstrap_preserves_query_pairing_and_reports_missing_denominators():
    result = paired_bootstrap({"a": 1.0, "b": None}, {"a": 0.5, "b": 0.0}, samples=100)
    assert result["estimate"] == 0.5 and result["ci95"] == [0.5, 0.5]
    assert result["paired_queries"] == 1 and result["excluded_queries"] == ["b"]
    assert paired_bootstrap({"a": None}, {"a": None}, samples=100)["estimate"] is None
    with pytest.raises(ValueError):
        paired_bootstrap({"a": 1}, {"b": 1})
    with pytest.raises(ValueError):
        paired_bootstrap({"a": float("nan")}, {"a": 0})


def test_only_the_declared_primary_and_secondary_contrasts_are_generated(graph):
    scored = score_graph(graph, established={"e1", "e3"}, judgments=labels(graph))
    contrasts = predeclared_contrasts({"B1": {"q": scored}, "M": {"q": scored}}, samples=100)
    assert set(contrasts) == {"B1_deep_minus_shallow", "M_minus_B1_overall"}
    assert contrasts["M_minus_B1_overall"]["estimate"] == 0
    with pytest.raises(ValueError):
        predeclared_contrasts({"B1": {"q": scored}, "M": {"q": scored}}, metric="recall")


def test_support_packet_is_blind_and_cannot_score_blank_or_tampered_reviews(graph, tmp_path):
    runs = tmp_path / "runs" / "M"
    runs.mkdir(parents=True)
    artifact = runs / "query.json"
    artifact.write_text(
        json.dumps(
            {
                "graph": graph.model_dump(mode="json"),
                "established_edge_ids": [e.edge_id for e in graph.edges if e.is_asserted],
            }
        )
    )
    review = tmp_path / "review"
    result = prepare(runs=runs.parent, corpus=FIXTURES / "passages.jsonl", output=review)
    assert result["edge_items"] == 9
    packet = json.loads((review / "packet.json").read_text())
    assert not any(
        "condition" in item or "provenance" in item or "model" in item for item in packet["items"]
    )
    with pytest.raises(ValueError, match="attestation"):
        evaluate(review_dir=review)
    judgments = json.loads((review / "judgments.json").read_text())
    judgments.update(
        reviewer="Fixture reviewer",
        reviewed_on="2026-10-23",
        independent_review=True,
        blinded_to_condition=True,
    )
    for row in judgments["judgments"]:
        row.update(supported=False)
    (review / "judgments.json").write_text(json.dumps(judgments))
    scored = evaluate(review_dir=review)
    assert scored["aggregate"]["M"]["overall"]["uer"]["mean"] == 1
    mapping = review / "private_mapping.json"
    mapping.write_text(mapping.read_text() + "\n")
    with pytest.raises(ValueError, match="mapping hash"):
        evaluate(review_dir=review)


def test_source_identity_and_future_dates_are_checked_against_trusted_records(graph, passages):
    assert inspect_graph(graph, passages)["passed"]
    edge = graph.edges[0]
    edge.evidence_published_at = None
    failures = inspect_graph(graph, passages)["failures"]
    assert {"edge_id": edge.edge_id, "kind": "citation_date_mismatch"} in failures
    assert screen_text("You should buy this stock; I predict it will rise")["advice_flag"]
    assert screen_text("You should buy this stock; I predict it will rise")["own_forecast_flag"]
