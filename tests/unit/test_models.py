"""Round-trips and invariants for Passage, Edge, Graph and the path labelling."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from schema import (
    CORPUS_END,
    CORPUS_START,
    Anchor,
    Direction,
    Edge,
    Graph,
    GraphNode,
    Passage,
    Path,
    Provenance,
    Strength,
    strength_rank,
    weakest,
)

MARCH = datetime.fromisoformat("2026-03-12T18:40:00+05:30")


def make_passage(**overrides) -> Passage:
    text = "The Indian basket rose to $98.4 a barrel due to the surge in Brent."
    fields = {
        "passage_id": "doc-1#p0",
        "doc_id": "doc-1",
        "source": "businessline",
        "published_at": MARCH,
        "title": "Brent crosses $100",
        "text": text,
        "para_idx": 0,
        "char_start": 0,
        "char_end": len(text),
    }
    fields.update(overrides)
    return Passage(**fields)


def make_edge(**overrides) -> Edge:
    fields = {
        "edge_id": "e1",
        "src_var": "BRENT",
        "dst_var": "INDIAN_BASKET",
        "direction": "up",
        "provenance": "source_asserted",
        "strength": "direct",
        "hop": 1,
        "evidence_span": "due to the surge in Brent",
        "evidence_doc_id": "doc-1",
    }
    fields.update(overrides)
    return Edge(**fields)


# --- round trips ----------------------------------------------------------


def test_passage_round_trips_through_json():
    passage = make_passage()
    assert Passage.model_validate_json(passage.model_dump_json()) == passage


def test_edge_round_trips_through_json():
    edge = make_edge()
    assert Edge.model_validate_json(edge.model_dump_json()) == edge


def test_graph_round_trips_through_json(graph: Graph):
    assert Graph.model_validate_json(graph.model_dump_json()) == graph


# --- Passage invariants ---------------------------------------------------


def test_offsets_must_match_the_text_length():
    with pytest.raises(ValidationError, match="verbatim-span checking"):
        make_passage(char_end=10)


def test_char_end_must_follow_char_start():
    with pytest.raises(ValidationError, match="must be greater than"):
        make_passage(char_start=50, char_end=20)


@pytest.mark.parametrize(
    "published",
    ["2026-02-28T10:00:00+05:30", "2026-10-01T10:00:00+05:30"],
)
def test_passages_outside_the_frozen_window_are_rejected(published: str):
    with pytest.raises(ValidationError, match="outside the frozen"):
        make_passage(published_at=datetime.fromisoformat(published))


def test_corpus_window_matches_the_proposal():
    assert (date(2026, 3, 1), date(2026, 9, 30)) == (CORPUS_START, CORPUS_END)


def test_as_of_filter_is_inclusive_of_the_publication_day():
    passage = make_passage()
    assert passage.visible_at(date(2026, 3, 12))
    assert passage.visible_at(date(2026, 3, 13))
    assert not passage.visible_at(date(2026, 3, 11))


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_passage(sentiment="bullish")


# --- Edge invariants ------------------------------------------------------


def test_source_asserted_edge_without_an_evidence_span_is_rejected():
    """The single most important schema rule: an asserted edge carries its quote."""
    with pytest.raises(ValidationError) as excinfo:
        make_edge(evidence_span=None)
    message = str(excinfo.value)
    assert "source_asserted" in message
    assert "evidence_span" in message


def test_source_asserted_edge_without_an_evidence_doc_is_rejected():
    with pytest.raises(ValidationError, match="evidence_doc_id"):
        make_edge(evidence_doc_id=None)


def test_source_asserted_edge_missing_both_names_both():
    with pytest.raises(ValidationError, match="evidence_span and evidence_doc_id"):
        make_edge(evidence_span=None, evidence_doc_id=None)


def test_model_inferred_edge_may_not_carry_an_evidence_span():
    with pytest.raises(ValidationError, match="candidate_evidence"):
        make_edge(provenance="model_inferred")


def test_model_inferred_edge_needs_no_evidence():
    edge = make_edge(provenance="model_inferred", evidence_span=None, evidence_doc_id=None)
    assert not edge.is_asserted


def test_a_rejected_passage_can_be_kept_as_candidate_evidence():
    edge = make_edge(
        provenance="model_inferred",
        evidence_span=None,
        evidence_doc_id=None,
        candidate_evidence=[
            {
                "passage_id": "doc-9#p2",
                "doc_id": "doc-9",
                "span": "the rupee weakened amid dollar demand",
                "verdict": "unsupported",
                "reason": "passage does not mention IMPORT_BILL",
            }
        ],
    )
    assert edge.candidate_evidence[0].verdict == "unsupported"
    assert edge.evidence_span is None


def test_variables_must_come_from_the_closed_ontology():
    with pytest.raises(ValidationError, match="closed ontology"):
        make_edge(dst_var="CRUDE_VIBES")


def test_self_loops_are_rejected():
    with pytest.raises(ValidationError, match="to itself"):
        make_edge(dst_var="BRENT")


def test_direction_must_be_allowed_for_the_destination_variable():
    # AIRLINE_COSTS is a latent construct: sources describe it rising or easing,
    # never holding steady, so `stable` is not in its allowed set.
    with pytest.raises(ValidationError, match="not allowed for AIRLINE_COSTS"):
        make_edge(
            src_var="ATF_PRICE",
            dst_var="AIRLINE_COSTS",
            direction="stable",
            hop=2,
        )


def test_hop_must_be_positive():
    with pytest.raises(ValidationError):
        make_edge(hop=0)


# --- strength ordering ----------------------------------------------------


def test_strength_order_is_direct_strongest():
    assert strength_rank(Strength.DIRECT) < strength_rank(Strength.CONDITIONAL)
    assert strength_rank(Strength.CONDITIONAL) < strength_rank(Strength.CORRELATIONAL)


def test_minimum_aggregation_takes_the_weakest_hop():
    assert weakest([Strength.DIRECT, Strength.CORRELATIONAL]) is Strength.CORRELATIONAL
    assert weakest([Strength.DIRECT, Strength.CONDITIONAL]) is Strength.CONDITIONAL
    assert weakest([Strength.DIRECT]) is Strength.DIRECT


def test_minimum_aggregation_needs_at_least_one_hop():
    with pytest.raises(ValueError, match="at least one"):
        weakest([])


# --- Graph invariants -----------------------------------------------------


def two_node_graph(**overrides) -> Graph:
    fields = {
        "query_id": "q-test",
        "anchor": Anchor(
            var="BRENT",
            direction="up",
            event="Brent crossed $100",
            event_date=date(2026, 3, 12),
        ),
        "as_of": date(2026, 3, 20),
        "nodes": [
            GraphNode(var="BRENT", direction="up", is_anchor=True),
            GraphNode(var="INDIAN_BASKET", direction="up"),
        ],
        "edges": [make_edge()],
    }
    fields.update(overrides)
    return Graph(**fields)


def test_minimal_graph_validates():
    assert two_node_graph().edges[0].hop == 1


def test_graph_needs_exactly_one_anchor_node():
    with pytest.raises(ValidationError, match="exactly one node flagged is_anchor"):
        two_node_graph(
            nodes=[
                GraphNode(var="BRENT", direction="up"),
                GraphNode(var="INDIAN_BASKET", direction="up"),
            ]
        )


def test_edges_must_reference_nodes_in_the_graph():
    with pytest.raises(ValidationError, match="not in the graph"):
        two_node_graph(
            edges=[make_edge(edge_id="e9", src_var="BRENT", dst_var="ATF_PRICE")],
        )


def test_duplicate_edge_ids_are_rejected():
    with pytest.raises(ValidationError, match="duplicate edge ids"):
        two_node_graph(edges=[make_edge(), make_edge()])


def test_hop_must_equal_distance_from_the_anchor():
    with pytest.raises(ValidationError, match="so it is hop 1"):
        two_node_graph(edges=[make_edge(hop=3)])


def test_evidence_published_after_the_as_of_date_is_rejected():
    # This is the schema-level half of the as-of guarantee (A11).
    with pytest.raises(ValidationError, match="after the as-of date"):
        two_node_graph(
            edges=[
                make_edge(evidence_published_at=datetime.fromisoformat("2026-03-25T10:00:00+05:30"))
            ]
        )


def test_path_weakest_strength_must_match_minimum_aggregation(graph: Graph):
    payload = graph.model_dump(mode="json")
    rupee = next(p for p in payload["paths"] if p["path_id"] == "p-rupee")
    rupee["weakest_strength"] = "direct"
    with pytest.raises(ValidationError, match="minimum aggregation"):
        Graph.model_validate(payload)


def test_path_fully_sourced_must_match_its_edges(graph: Graph):
    payload = graph.model_dump(mode="json")
    rupee = next(p for p in payload["paths"] if p["path_id"] == "p-rupee")
    rupee["fully_sourced"] = True
    with pytest.raises(ValidationError, match="model_inferred"):
        Graph.model_validate(payload)


def test_a_broken_path_is_rejected(graph: Graph):
    payload = graph.model_dump(mode="json")
    rupee = next(p for p in payload["paths"] if p["path_id"] == "p-rupee")
    rupee["edge_ids"] = ["e1", "e5", "e3", "e4"]
    with pytest.raises(ValidationError, match="is broken"):
        Graph.model_validate(payload)


def test_a_path_must_start_at_the_anchor(graph: Graph):
    payload = graph.model_dump(mode="json")
    payload["paths"] = [
        {
            "path_id": "p-orphan",
            "edge_ids": ["e6", "e7"],
            "weakest_strength": "correlational",
            "fully_sourced": True,
            "depth": 2,
        }
    ]
    with pytest.raises(ValidationError, match="not at the anchor"):
        Graph.model_validate(payload)


def test_path_depth_must_match_its_edge_count():
    with pytest.raises(ValidationError, match="says depth"):
        Path(
            path_id="p1",
            edge_ids=["e1", "e2"],
            weakest_strength=Strength.DIRECT,
            fully_sourced=True,
            depth=3,
        )


def test_edges_at_hop_treats_three_as_three_or_deeper(graph: Graph):
    deep = graph.edges_at_hop(3)
    assert {e.edge_id for e in deep} == {"e3", "e4", "e7"}
    assert all(e.hop >= 3 for e in deep)


def test_established_edges_are_the_asserted_ones(graph: Graph):
    established = {e.edge_id for e in graph.established_edges()}
    assert established == {"e1", "e2", "e5", "e6", "e7", "e8", "e9"}
    assert all(e.provenance is Provenance.SOURCE_ASSERTED for e in graph.established_edges())


def test_direction_enum_is_the_closed_three():
    assert {d.value for d in Direction} == {"up", "down", "stable"}
