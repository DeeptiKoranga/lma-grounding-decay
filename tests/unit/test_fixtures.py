"""Every fixture must validate, and must keep the properties the other tracks rely on.

Track B builds the extractor and verifier against these files and Track C builds
the agent loop against them, both before the real corpus exists. A fixture that
quietly stops matching the schema would take two people's work down with it.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from itertools import pairwise

from schema import (
    CORPUS_END,
    CORPUS_START,
    Graph,
    Passage,
    Provenance,
    SourceKind,
    Strength,
    parse_run_log_line,
    variable_ids,
)

CUES = ("due to", "because of", "amid", "could", "upside risk", "driven by")


# --- passages -------------------------------------------------------------


def test_there_are_twenty_fixture_passages(passages: list[Passage]):
    assert len(passages) == 20


def test_every_passage_validates(raw_passages: list[dict]):
    for row in raw_passages:
        Passage.model_validate(row)


def test_passage_ids_are_unique(passages: list[Passage]):
    ids = [p.passage_id for p in passages]
    assert len(set(ids)) == len(ids)


def test_offsets_index_into_the_document_text(passages: list[Passage], documents: dict[str, str]):
    """The property the whole verbatim-span check rests on."""
    for passage in passages:
        doc_text = documents[passage.doc_id]
        assert doc_text[passage.char_start : passage.char_end] == passage.text, passage.passage_id


def test_paragraphs_of_a_document_do_not_overlap(passages: list[Passage]):
    by_doc: dict[str, list[Passage]] = {}
    for passage in passages:
        by_doc.setdefault(passage.doc_id, []).append(passage)
    for doc_id, members in by_doc.items():
        members.sort(key=lambda p: p.para_idx)
        for earlier, later in pairwise(members):
            assert earlier.char_end <= later.char_start, doc_id


def test_passages_span_march_to_september_2026(passages: list[Passage]):
    months = {(p.published_at.year, p.published_at.month) for p in passages}
    assert months == {(2026, m) for m in range(3, 10)}
    for passage in passages:
        assert CORPUS_START <= passage.published_at.date() <= CORPUS_END


def test_passages_cover_news_and_official_sources(passages: list[Passage]):
    kinds = {p.source_kind for p in passages}
    assert kinds == {SourceKind.NEWS, SourceKind.OFFICIAL}
    sources = {p.source for p in passages}
    assert {"businessline", "economic_times", "business_standard", "mint"} <= sources
    assert {"rbi", "mospi", "ppac"} <= sources


def test_most_passages_carry_a_causal_or_hedging_cue(passages: list[Passage]):
    with_cue = [p for p in passages if any(cue in p.text for cue in CUES)]
    assert len(with_cue) >= 14, "the fixtures exist to exercise cue detection"


def test_the_three_named_cues_all_appear(passages: list[Passage]):
    text = " ".join(p.text for p in passages)
    for cue in ("due to", "amid", "could"):
        assert cue in text


def test_fixtures_are_marked_synthetic(passages: list[Passage]):
    assert all(p.licence_note and "synthetic" in p.licence_note for p in passages)


# --- graph ----------------------------------------------------------------


def test_fixture_graph_validates(raw_graph: dict):
    Graph.model_validate(raw_graph)


def test_fixture_graph_has_a_four_hop_chain(graph: Graph):
    rupee = next(p for p in graph.paths if p.path_id == "p-rupee")
    assert rupee.depth == 4
    assert max(e.hop for e in graph.edges) == 4


def test_fixture_graph_mixes_both_provenance_labels(graph: Graph):
    counts = Counter(e.provenance for e in graph.edges)
    assert counts[Provenance.SOURCE_ASSERTED] >= 1
    assert counts[Provenance.MODEL_INFERRED] >= 1


def test_the_four_hop_chain_mixes_provenance(graph: Graph):
    by_id = {e.edge_id: e for e in graph.edges}
    rupee = next(p for p in graph.paths if p.path_id == "p-rupee")
    labels = {by_id[e].provenance for e in rupee.edge_ids}
    assert labels == {Provenance.SOURCE_ASSERTED, Provenance.MODEL_INFERRED}
    assert not rupee.fully_sourced


def test_the_airline_chain_is_fully_sourced(graph: Graph):
    airline = next(p for p in graph.paths if p.path_id == "p-airline")
    assert airline.fully_sourced
    assert airline.weakest_strength is Strength.CORRELATIONAL


def test_all_three_strength_labels_appear(graph: Graph):
    assert {e.strength for e in graph.edges} == set(Strength)


def test_every_hop_slice_has_at_least_one_edge(graph: Graph):
    for hop in (1, 2, 3):
        assert graph.edges_at_hop(hop), f"no edges at hop {hop}"


def test_graph_variables_are_all_in_the_ontology(graph: Graph):
    known = set(variable_ids())
    assert {n.var for n in graph.nodes} <= known
    for edge in graph.edges:
        assert {edge.src_var, edge.dst_var} <= known


def test_every_asserted_edge_quotes_a_real_fixture_passage(graph: Graph, passages: list[Passage]):
    """An asserted edge must be checkable word for word against the corpus (B6)."""
    by_id = {p.passage_id: p for p in passages}
    asserted = graph.established_edges()
    assert asserted
    for edge in asserted:
        assert edge.evidence_passage_id in by_id, edge.edge_id
        passage = by_id[edge.evidence_passage_id]
        assert passage.contains(edge.evidence_span), edge.edge_id
        assert passage.doc_id == edge.evidence_doc_id
        assert passage.visible_at(graph.as_of), edge.edge_id


def test_no_evidence_is_dated_after_the_as_of_date(graph: Graph):
    assert graph.as_of == date(2026, 3, 20)
    for edge in graph.edges:
        if edge.evidence_published_at is not None:
            assert edge.evidence_published_at.date() <= graph.as_of


def test_model_inferred_edges_carry_no_span(graph: Graph):
    for edge in graph.edges:
        if edge.provenance is Provenance.MODEL_INFERRED:
            assert edge.evidence_span is None


# --- run log --------------------------------------------------------------


def test_every_run_log_line_validates(raw_run_log: list[dict]):
    for number, row in enumerate(raw_run_log, start=1):
        try:
            parse_run_log_line(row)
        except Exception as exc:
            raise AssertionError(f"run_log.jsonl line {number}: {exc}") from exc


def test_run_log_round_trips_line_by_line(run_log, raw_run_log):
    for parsed, raw in zip(run_log, raw_run_log, strict=True):
        again = parse_run_log_line(parsed.model_dump_json())
        assert again == parsed
        assert again.query_id == raw["query_id"]


def test_run_log_is_one_run_of_one_query(run_log):
    assert {line.run_id for line in run_log} == {"run-fixture-0001"}
    assert {line.query_id for line in run_log} == {"q-dev-001"}


def test_run_log_covers_model_calls_tool_calls_and_a_stop(run_log):
    events = Counter(line.event for line in run_log)
    assert events["model_call"] >= 3
    assert events["tool_call"] >= 5
    assert events["tool_result"] == events["tool_call"]
    assert events["stop"] == 1
    assert events["state"] >= 1


def test_run_log_stays_inside_the_tool_budget(run_log):
    calls = [line for line in run_log if line.event == "tool_call"]
    assert len(calls) <= 12
    stop = next(line for line in run_log if line.event == "stop")
    assert stop.calls_used == len(calls)


def test_run_log_budget_counts_down(run_log):
    remaining = [line.budget_remaining for line in run_log if line.event == "tool_call"]
    assert remaining == sorted(remaining, reverse=True)


def test_run_log_steps_do_not_go_backwards(run_log):
    steps = [line.step for line in run_log]
    assert steps == sorted(steps)


def test_run_log_records_at_least_one_tool_fault(run_log):
    failures = [line for line in run_log if line.event == "tool_result" and not line.result.ok]
    assert failures, "the fixture should exercise the empty-result path"
    assert failures[0].result.error.kind == "empty_result"


def test_every_tool_result_answers_a_tool_call(run_log):
    issued = {line.call.call_id for line in run_log if line.event == "tool_call"}
    answered = {line.result.call_id for line in run_log if line.event == "tool_result"}
    assert answered == issued


def test_passages_returned_by_search_are_valid_passages(raw_run_log: list[dict]):
    for row in raw_run_log:
        if row.get("event") == "tool_result" and row["result"]["tool"] == "search_corpus":
            for payload in row["result"].get("passages", []):
                Passage.model_validate(payload)


def test_fixture_files_are_newline_terminated(fixture_dir):
    for path in sorted(fixture_dir.glob("*")):
        assert path.read_text(encoding="utf-8").endswith("\n"), path.name


def test_documents_json_covers_every_passage_document(
    passages: list[Passage], documents: dict[str, str]
):
    assert {p.doc_id for p in passages} == set(documents)
    assert len(documents) == 13


def test_fixture_jsonl_files_are_one_object_per_line(fixture_dir):
    for name in ("passages.jsonl", "run_log.jsonl"):
        for line in (fixture_dir / name).read_text(encoding="utf-8").splitlines():
            assert isinstance(json.loads(line), dict)
