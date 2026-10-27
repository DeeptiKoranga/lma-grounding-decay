"""B4 - the gold-graph validator.

Tested against synthetic graphs, because the corpus payload is not in git. The
point of these is that the validator rejects the ways a gold standard goes
quietly wrong: an inferred edge smuggled in, a missing span, evidence dated
after the as-of cutoff, or a graph that never touches its own anchor.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from eval.gold import (
    MAX_EDGES,
    MIN_EDGES,
    missing_gold_graphs,
    validate_gold_graph,
)
from schema import Anchor, Edge, Graph, GraphNode

DEV_QUERIES = ["dev-oil-why", "dev-oil-effects", "dev-rupee-why", "dev-rupee-effects"]


def _edge(n: int, src: str, dst: str, **over) -> Edge:
    fields = {
        "edge_id": f"g{n}",
        "src_var": src,
        "dst_var": dst,
        "direction": "up",
        "provenance": "source_asserted",
        "strength": "direct",
        "hop": 1,
        "evidence_span": "crude costs fed straight through to the import bill",
        "evidence_doc_id": "et-2026-04-02-oil",
        "evidence_passage_id": "et-2026-04-02-oil#p0",
        "evidence_published_at": datetime.fromisoformat("2026-04-02T10:00:00+05:30"),
    }
    fields.update(over)
    return Edge(**fields)


def _graph(edges: list[Edge], *, as_of: date = date(2026, 4, 8)) -> Graph:
    variables = {"BRENT"} | {e.src_var for e in edges} | {e.dst_var for e in edges}
    return Graph(
        query_id="dev-oil-why",
        anchor=Anchor(
            var="BRENT",
            direction="up",
            event="Brent crude at or above $100 a barrel",
            event_date=date(2026, 4, 1),
            confirmed_by_series=True,
            series_id="brent_usd_bbl",
        ),
        as_of=as_of,
        nodes=[
            GraphNode(var=v, direction="up", is_anchor=(v == "BRENT")) for v in sorted(variables)
        ],
        edges=edges,
    )


def _four_good_edges() -> list[Edge]:
    chain = [
        ("BRENT", "IMPORT_BILL"),
        ("IMPORT_BILL", "INR_USD"),
        ("INR_USD", "IMPORTED_INFLATION"),
        ("BRENT", "FUEL_PRICES"),
    ]
    return [
        _edge(i, src, dst, hop=1 if src == "BRENT" else i) for i, (src, dst) in enumerate(chain, 1)
    ]


# ---------------------------------------------------------------------------
# A good graph passes
# ---------------------------------------------------------------------------


def test_a_well_formed_gold_graph_has_no_issues():
    report = validate_gold_graph(_graph(_four_good_edges()))
    assert report.ok
    assert report.edge_count == 4
    assert report.corpus_checked is False  # structure only


# ---------------------------------------------------------------------------
# The ways a gold standard goes wrong
# ---------------------------------------------------------------------------


def test_a_model_inferred_edge_is_rejected():
    """Gold records what a source states. An inferred edge is the thing under test."""
    edges = _four_good_edges()
    edges[2] = _edge(
        3,
        "INR_USD",
        "IMPORTED_INFLATION",
        hop=3,
        provenance="model_inferred",
        evidence_span=None,
        evidence_doc_id=None,
        evidence_passage_id=None,
        evidence_published_at=None,
    )
    report = validate_gold_graph(_graph(edges))
    assert not report.ok
    assert any("source_asserted" in i.problem for i in report.issues)


def test_the_schema_itself_refuses_evidence_published_after_the_as_of_date():
    """The strongest guarantee: such a graph cannot be constructed at all."""
    edges = _four_good_edges()
    edges[0] = _edge(
        1,
        "BRENT",
        "IMPORT_BILL",
        evidence_published_at=datetime.fromisoformat("2026-04-20T10:00:00+05:30"),
    )
    with pytest.raises(ValidationError, match="after the as-of date"):
        _graph(edges, as_of=date(2026, 4, 8))


def test_the_validator_catches_a_late_citation_that_skipped_validation():
    """`model_construct` bypasses the schema, so the validator still checks it."""
    edges = _four_good_edges()
    edges[0] = _edge(
        1,
        "BRENT",
        "IMPORT_BILL",
        evidence_published_at=datetime.fromisoformat("2026-04-20T10:00:00+05:30"),
    )
    good = _graph(_four_good_edges(), as_of=date(2026, 4, 8))
    unchecked = Graph.model_construct(**{**good.__dict__, "edges": edges})
    report = validate_gold_graph(unchecked)
    assert not report.ok
    assert any("after the as-of date" in i.problem for i in report.issues)


@pytest.mark.parametrize("count", [0, 1, 3, 7, 9])
def test_the_edge_count_must_sit_in_the_reviewed_range(count):
    edges = [
        _edge(i, "BRENT", "IMPORT_BILL" if i % 2 else "FUEL_PRICES", hop=1) for i in range(count)
    ]
    # Keep ids unique and avoid duplicate node pairs tripping other validators.
    edges = [
        _edge(i, "BRENT", v, hop=1)
        for i, v in enumerate(
            [
                "IMPORT_BILL",
                "FUEL_PRICES",
                "INR_USD",
                "CPI_HEADLINE",
                "NIFTY50",
                "GSEC_10Y",
                "EXPORTS",
                "WPI",
                "IIP",
            ][:count],
            1,
        )
    ]
    report = validate_gold_graph(_graph(edges)) if edges else None
    if report is None:
        pytest.skip("an empty graph is rejected by the Graph model itself")
    assert report.ok is (MIN_EDGES <= count <= MAX_EDGES)


def test_a_graph_that_never_touches_its_anchor_is_rejected():
    edges = [
        _edge(1, "CPI_HEADLINE", "REPO_RATE", hop=1),
        _edge(2, "REPO_RATE", "GSEC_10Y", hop=2),
        _edge(3, "GSEC_10Y", "LENDING_RATES", hop=3),
        _edge(4, "LENDING_RATES", "CREDIT_GROWTH", hop=4),
    ]
    report = validate_gold_graph(_graph(edges))
    assert not report.ok
    assert any("does not answer its query" in i.problem for i in report.issues)


def test_a_mislabelled_graph_is_caught():
    report = validate_gold_graph(_graph(_four_good_edges()), expect_query_id="dev-rupee-why")
    assert not report.ok
    assert any("was loaded for" in i.problem for i in report.issues)


# ---------------------------------------------------------------------------
# B4 completion
# ---------------------------------------------------------------------------


def test_b4_is_not_done_yet_and_says_so():
    """Fails the day all four gold graphs land, which is the signal to close #15."""
    missing = missing_gold_graphs(DEV_QUERIES)
    assert set(missing) <= set(DEV_QUERIES)
    if not missing:
        pytest.fail(
            "all four dev gold graphs exist - remove this test, close #15, "
            "and run scripts/check_gold_graphs.py --require against the corpus"
        )
