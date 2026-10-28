"""Rule 3 over a two-paragraph window (docs/decisions.md D-17).

Indian macro copy states a relation across a paragraph break constantly: the
first paragraph names the thing, the second says "the increase", "the move",
"the decision". Scoping the mention rule to the single cited paragraph (the
original D-14) rejects those edges, which under-labels `source_asserted` and
drives reference-edge recall down - the H2d guard - while flattering UER.

So rule 3 now looks in the cited paragraph *plus the one immediately before
it*. Rule 4 does not move: the quoted span must still be verbatim in the cited
passage. These tests pin both halves of that, and the direction and document
boundaries of the window.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from schema import Graph, Passage, VerifyVerdict
from verify import (
    MentionScope,
    RuleName,
    check_edge,
    check_variables_mentioned,
    preceding_window,
    screen_edge,
)

#: The fixture edge the original strict rule rejected: ATF_PRICE -> AIRLINE_COSTS,
#: where `mint-2026-03-16-atf#p1` says "the increase" and paragraph 0 names ATF.
CROSS_PARAGRAPH_EDGE = "e6"


def _passage(doc_id: str, para_idx: int, text: str, *, start: int = 0) -> Passage:
    """A synthetic paragraph. Offsets must agree with the text (Passage validates)."""
    return Passage(
        passage_id=f"{doc_id}#p{para_idx}",
        doc_id=doc_id,
        source="fixture",
        url=f"https://example.test/{doc_id}",
        title="synthetic",
        published_at=datetime.fromisoformat("2026-04-01T09:00:00+05:30"),
        text=text,
        para_idx=para_idx,
        char_start=start,
        char_end=start + len(text),
    )


@pytest.fixture(scope="module")
def three_paragraphs() -> list[Passage]:
    """One document, paragraphs 0-2, each naming a different variable."""
    texts = [
        "Brent crude climbed above $100 a barrel on Thursday.",
        "The Indian basket followed it higher through the week.",
        "Airline operating costs are expected to feel the move next quarter.",
    ]
    out, start = [], 0
    for idx, text in enumerate(texts):
        out.append(_passage("syn-2026-04-01-chain", idx, text, start=start))
        start += len(text) + 1
    return out


# ---------------------------------------------------------------------------
# The window itself
# ---------------------------------------------------------------------------


def test_the_window_is_the_cited_paragraph_and_the_one_before(three_paragraphs):
    window = preceding_window(three_paragraphs[2], three_paragraphs)
    assert [p.para_idx for p in window] == [1, 2]


def test_the_window_does_not_reach_forward(three_paragraphs):
    """Paragraph 2 may support paragraph 1's claim; the reverse is not evidence."""
    window = preceding_window(three_paragraphs[1], three_paragraphs)
    assert [p.para_idx for p in window] == [0, 1]
    assert three_paragraphs[2] not in window


def test_the_window_stops_at_one_paragraph_back(three_paragraphs):
    window = preceding_window(three_paragraphs[2], three_paragraphs)
    assert three_paragraphs[0] not in window


def test_the_first_paragraph_has_no_predecessor(three_paragraphs):
    assert preceding_window(three_paragraphs[0], three_paragraphs) == (three_paragraphs[0],)


def test_the_window_never_crosses_a_document_boundary(three_paragraphs, by_passage):
    """A paragraph from another document is not a predecessor, whatever its index."""
    other = by_passage["mint-2026-03-16-atf#p0"]
    window = preceding_window(three_paragraphs[1], [*three_paragraphs, other])
    assert other not in window
    assert {p.doc_id for p in window} == {"syn-2026-04-01-chain"}


# ---------------------------------------------------------------------------
# Rule 3 across the window
# ---------------------------------------------------------------------------


def test_both_variables_in_the_cited_paragraph_is_scope_cited(by_passage, aliases):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    match = check_variables_mentioned(passage, "BRENT", "INDIAN_BASKET", aliases).mention_match
    assert match.found
    assert match.scope is MentionScope.CITED
    assert match.src_passage_id == match.dst_passage_id == passage.passage_id


def test_a_variable_only_in_the_preceding_paragraph_still_counts(three_paragraphs, aliases):
    cited = three_paragraphs[1]
    outcome = check_variables_mentioned(
        cited, "BRENT", "INDIAN_BASKET", aliases, context=preceding_window(cited, three_paragraphs)
    )
    assert outcome.passed
    match = outcome.mention_match
    assert match.scope is MentionScope.WINDOW
    assert match.src_passage_id == "syn-2026-04-01-chain#p0"
    assert match.dst_passage_id == cited.passage_id


def test_without_a_window_the_strict_rule_still_applies(three_paragraphs, aliases):
    """No context supplied means no neighbouring paragraph was offered, so D-14 stands."""
    outcome = check_variables_mentioned(three_paragraphs[1], "BRENT", "INDIAN_BASKET", aliases)
    assert not outcome.passed
    assert "BRENT" in outcome.reason


def test_a_variable_two_paragraphs_back_is_out_of_reach(three_paragraphs, aliases):
    cited = three_paragraphs[2]
    outcome = check_variables_mentioned(
        cited, "BRENT", "AIRLINE_COSTS", aliases, context=preceding_window(cited, three_paragraphs)
    )
    assert not outcome.passed
    assert "BRENT" in outcome.reason


def test_the_failure_reason_says_the_window_was_searched(three_paragraphs, aliases):
    cited = three_paragraphs[2]
    outcome = check_variables_mentioned(
        cited, "BRENT", "AIRLINE_COSTS", aliases, context=preceding_window(cited, three_paragraphs)
    )
    assert "syn-2026-04-01-chain#p1" in outcome.reason


# ---------------------------------------------------------------------------
# Rule 4 does not move
# ---------------------------------------------------------------------------


def test_the_span_must_still_be_in_the_cited_passage(three_paragraphs, aliases, corpus_doc_ids):
    """A span lifted from the preceding paragraph fails, even though rule 3 passes."""
    from schema import Edge

    cited = three_paragraphs[1]
    edge = Edge(
        edge_id="syn1",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        provenance="source_asserted",
        strength="direct",
        hop=1,
        evidence_span="Brent crude climbed above $100 a barrel",  # that is paragraph 0
        evidence_doc_id=cited.doc_id,
        evidence_passage_id=cited.passage_id,
        evidence_published_at=cited.published_at,
    )
    report = check_edge(
        edge,
        cited,
        as_of=date(2026, 4, 30),
        corpus_doc_ids={*corpus_doc_ids, cited.doc_id},
        aliases=aliases,
        document=three_paragraphs,
    )
    assert report.outcome_for(RuleName.BOTH_VARIABLES_MENTIONED).passed
    assert report.rule_failures == [RuleName.SPAN_VERBATIM]
    assert not report.span_match.found


# ---------------------------------------------------------------------------
# The e6 case, end to end
# ---------------------------------------------------------------------------


def test_the_cross_paragraph_fixture_edge_now_clears_the_rules(
    cited, by_passage, aliases, corpus_doc_ids, graph: Graph
):
    edge = next(e for e in graph.edges if e.edge_id == CROSS_PARAGRAPH_EDGE)
    document = [by_passage[f"mint-2026-03-16-atf#p{i}"] for i in (0, 1)]
    cited_passage = by_passage["mint-2026-03-16-atf#p1"]

    report = check_edge(
        edge,
        cited_passage,
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
        document=document,
    )
    assert report.passed
    assert report.verdict is None  # eligible for B7, not yet supported
    assert report.mention_match.scope is MentionScope.WINDOW
    assert report.mention_match.src_passage_id == "mint-2026-03-16-atf#p0"
    assert report.span_match.found


def test_every_asserted_fixture_edge_clears_the_rules_with_its_document(
    cited, passages: list[Passage], aliases, graph: Graph, corpus_doc_ids
):
    """With the window, the fixture graph has no unexplained rule failure left."""
    failed = {}
    for edge, passage in cited:
        report = check_edge(
            edge,
            passage,
            as_of=graph.as_of,
            corpus_doc_ids=corpus_doc_ids,
            aliases=aliases,
            document=passages,
        )
        if not report.passed:
            failed[edge.edge_id] = report.rule_failures
    assert failed == {}


def test_screen_edge_passes_the_document_through(
    graph: Graph, passages: list[Passage], by_passage, aliases, corpus_doc_ids
):
    edge = next(e for e in graph.edges if e.edge_id == CROSS_PARAGRAPH_EDGE)
    screening = screen_edge(
        edge,
        [by_passage["mint-2026-03-16-atf#p1"]],
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
        document=passages,
    )
    assert screening.passed
    assert screening.verdict is None
    assert screening.rule_failures == []


def test_screen_edge_without_a_document_keeps_the_strict_result(
    graph: Graph, by_passage, aliases, corpus_doc_ids
):
    edge = next(e for e in graph.edges if e.edge_id == CROSS_PARAGRAPH_EDGE)
    screening = screen_edge(
        edge,
        [by_passage["mint-2026-03-16-atf#p1"]],
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert not screening.passed
    assert screening.verdict is VerifyVerdict.UNSUPPORTED
    assert screening.rule_failures == [RuleName.BOTH_VARIABLES_MENTIONED]
