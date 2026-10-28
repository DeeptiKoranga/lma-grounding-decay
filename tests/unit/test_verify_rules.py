"""B6 - the four deterministic pre-checks, each passing and failing on its own.

Everything here runs against `tests/fixtures/`: 20 synthetic passages, 13
documents and the Figure 1 graph. No model, no network, no real corpus.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from schema import Edge, Graph, Passage, VerifyVerdict, parse_tool_result
from verify import (
    RULE_ORDER,
    AliasTable,
    RuleName,
    RuleOutcome,
    SpanMatchKind,
    check_claim,
    check_edge,
    check_in_corpus,
    check_on_or_before_as_of,
    check_span_verbatim,
    check_variables_mentioned,
    load_aliases,
    screen_edge,
)

#: e6 (ATF_PRICE -> AIRLINE_COSTS) states its relation across a paragraph break:
#: the cited passage says "the increase", and ATF_PRICE is named in the previous
#: paragraph. It was first read as a fixture inconsistency; D-17 concluded it is
#: the normal shape of the copy and widened rule 3 to a two-paragraph window.
#: The tests below pin the strict path, taken when no `document` is supplied.
#: The widened path lives in test_verify_mention_window.py.
CROSS_PARAGRAPH_EDGE = "e6"


@pytest.fixture(scope="module")
def aliases() -> AliasTable:
    return load_aliases()


@pytest.fixture(scope="module")
def by_passage(passages: list[Passage]) -> dict[str, Passage]:
    return {p.passage_id: p for p in passages}


@pytest.fixture(scope="module")
def corpus_doc_ids(passages: list[Passage]) -> frozenset[str]:
    """Stands in for the frozen-corpus manifest (A4)."""
    return frozenset(p.doc_id for p in passages)


@pytest.fixture(scope="module")
def cited(graph: Graph, by_passage: dict[str, Passage]) -> list[tuple[Edge, Passage]]:
    """Every source-asserted fixture edge paired with the passage it quotes."""
    return [
        (edge, by_passage[edge.evidence_passage_id])
        for edge in graph.edges
        if edge.is_asserted and edge.evidence_passage_id
    ]


def one(edge_id: str, pairs: list[tuple[Edge, Passage]]) -> tuple[Edge, Passage]:
    return next(pair for pair in pairs if pair[0].edge_id == edge_id)


# ---------------------------------------------------------------------------
# Shape of the result
# ---------------------------------------------------------------------------


def test_every_rule_is_reported_even_when_an_earlier_one_fails(cited, aliases: AliasTable):
    """The layer never short-circuits: the caller always sees all four verdicts."""
    edge, passage = one("e1", cited)
    report = check_edge(
        edge,
        passage,
        as_of=date(2026, 3, 1),  # before publication, so rule 2 fails
        corpus_doc_ids=frozenset(),  # empty manifest, so rule 1 fails too
        aliases=aliases,
    )
    assert [outcome.rule for outcome in report.outcomes] == list(RULE_ORDER)
    assert report.rule_failures == [
        RuleName.IN_CORPUS,
        RuleName.ON_OR_BEFORE_AS_OF,
    ]
    assert report.outcome_for(RuleName.SPAN_VERBATIM).passed
    assert report.outcome_for(RuleName.BOTH_VARIABLES_MENTIONED).passed


def test_a_clean_report_carries_no_verdict(cited, aliases, corpus_doc_ids):
    """Passing the rules means eligible for B7, never `supported`."""
    edge, passage = one("e1", cited)
    report = check_edge(
        edge, passage, as_of=date(2026, 3, 20), corpus_doc_ids=corpus_doc_ids, aliases=aliases
    )
    assert report.passed
    assert report.failures == ()
    assert report.verdict is None
    assert report.reason() is None


def test_rule_failures_fit_the_verify_edge_tool_result(cited, aliases, corpus_doc_ids):
    """C3 puts these strings straight into `ToolResult.rule_failures`."""
    edge, passage = one("e1", cited)
    report = check_edge(
        edge,
        passage,
        as_of=date(2026, 3, 11),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    result = parse_tool_result(
        {
            "call_id": "c1",
            "tool": "verify_edge",
            "ok": True,
            "edge_id": report.edge_id,
            "verdict": report.verdict,
            "rule_failures": report.rule_failures,
        }
    )
    assert result.verdict is VerifyVerdict.AFTER_AS_OF
    assert result.rule_failures == ["on_or_before_as_of"]


def test_an_outcome_cannot_fail_without_a_reason():
    with pytest.raises(ValueError, match="without a reason"):
        RuleOutcome(rule=RuleName.IN_CORPUS, passed=False)
    with pytest.raises(ValueError, match="carries a failure reason"):
        RuleOutcome(rule=RuleName.IN_CORPUS, passed=True, reason="no")


# ---------------------------------------------------------------------------
# Rule 1 - in corpus
# ---------------------------------------------------------------------------


def test_in_corpus_passes_for_a_fixture_document(by_passage, corpus_doc_ids):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    assert check_in_corpus(passage, corpus_doc_ids).passed


def test_in_corpus_fails_for_a_document_outside_the_manifest(by_passage, corpus_doc_ids):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    outcome = check_in_corpus(passage, corpus_doc_ids - {passage.doc_id})
    assert not outcome.passed
    assert passage.doc_id in outcome.reason


def test_out_of_corpus_fails_on_its_own(cited, aliases, corpus_doc_ids):
    edge, passage = one("e2", cited)
    report = check_edge(
        edge,
        passage,
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids - {passage.doc_id},
        aliases=aliases,
    )
    assert report.rule_failures == [RuleName.IN_CORPUS]
    assert report.verdict is VerifyVerdict.OUT_OF_CORPUS


# ---------------------------------------------------------------------------
# Rule 2 - published on or before the as-of date (inclusive)
# ---------------------------------------------------------------------------


def test_as_of_on_the_publication_date_is_admissible(by_passage):
    """The proposal's as-of filter is inclusive: the day itself counts."""
    passage = by_passage["rbi-2026-03-18-mpc-minutes#p0"]
    assert check_on_or_before_as_of(passage, date(2026, 3, 18)).passed


def test_as_of_the_day_after_publication_is_admissible(by_passage):
    passage = by_passage["rbi-2026-03-18-mpc-minutes#p0"]
    assert check_on_or_before_as_of(passage, date(2026, 3, 19)).passed


def test_as_of_the_day_before_publication_is_not(by_passage):
    passage = by_passage["rbi-2026-03-18-mpc-minutes#p0"]
    outcome = check_on_or_before_as_of(passage, date(2026, 3, 17))
    assert not outcome.passed
    assert "2026-03-18" in outcome.reason and "2026-03-17" in outcome.reason


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_the_boundary_holds_for_every_fixture_passage(passages: list[Passage], offset: int):
    for passage in passages:
        as_of = passage.published_at.date() + timedelta(days=offset)
        assert check_on_or_before_as_of(passage, as_of).passed is (offset >= 0)


def test_after_as_of_fails_on_its_own(cited, aliases, corpus_doc_ids):
    edge, passage = one("e8", cited)
    report = check_edge(
        edge,
        passage,
        as_of=passage.published_at.date() - timedelta(days=1),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert report.rule_failures == [RuleName.ON_OR_BEFORE_AS_OF]
    assert report.verdict is VerifyVerdict.AFTER_AS_OF


def test_out_of_corpus_outranks_after_as_of(cited, aliases, corpus_doc_ids):
    """A leak is reported as a leak, whichever other rule also failed."""
    edge, passage = one("e8", cited)
    report = check_edge(
        edge,
        passage,
        as_of=date(2026, 3, 1),
        corpus_doc_ids=corpus_doc_ids - {passage.doc_id},
        aliases=aliases,
    )
    assert report.rule_failures == [RuleName.IN_CORPUS, RuleName.ON_OR_BEFORE_AS_OF]
    assert report.verdict is VerifyVerdict.OUT_OF_CORPUS


# ---------------------------------------------------------------------------
# Rule 3 - both variables mentioned
# ---------------------------------------------------------------------------


def test_both_variables_mentioned_passes(by_passage, aliases):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    assert check_variables_mentioned(passage, "BRENT", "INDIAN_BASKET", aliases).passed


def test_a_missing_variable_is_named_in_the_reason(by_passage, aliases):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    outcome = check_variables_mentioned(passage, "BRENT", "GSEC_10Y", aliases)
    assert not outcome.passed
    assert "GSEC_10Y" in outcome.reason
    assert "BRENT" in outcome.reason  # says what it *did* find, for failure analysis


def test_an_alias_only_mention_is_enough(by_passage, aliases):
    """The ontology id never appears in copy; "the rupee" is all there is."""
    passage = by_passage["et-2026-04-08-rupee88#p0"]
    assert "INR_USD" not in passage.text
    assert aliases.first_mention("INR_USD", passage.text) == "the rupee"
    # ...and "the dollar" is not the dollar index, so DXY is genuinely absent.
    assert not aliases.mentions("DXY", passage.text)
    assert not check_variables_mentioned(passage, "INR_USD", "DXY", aliases).passed


def test_both_aliases_only_still_passes(by_passage, aliases):
    passage = by_passage["bl-2026-05-20-rupee-record#p0"]
    assert "INR_USD" not in passage.text and "DXY" not in passage.text
    assert check_variables_mentioned(passage, "DXY", "INR_USD", aliases).passed


def test_variables_in_different_paragraphs_of_one_document_fail(cited, aliases, corpus_doc_ids):
    """With no `document`, rule 3 stays scoped to the single passage (D-17).

    `mint-2026-03-16-atf` names ATF in paragraph 0 and airline costs in
    paragraph 1. A caller that offers neither neighbour gets the strict result,
    so the ATF_PRICE -> AIRLINE_COSTS edge fails here. Pass the document and it
    clears the rules with `scope: window` - see test_verify_mention_window.py.
    """
    edge, cited_passage = one(CROSS_PARAGRAPH_EDGE, cited)
    assert edge.src_var == "ATF_PRICE" and edge.dst_var == "AIRLINE_COSTS"

    report = check_edge(
        edge, cited_passage, as_of=date(2026, 3, 20), corpus_doc_ids=corpus_doc_ids, aliases=aliases
    )
    assert report.rule_failures == [RuleName.BOTH_VARIABLES_MENTIONED]
    assert report.verdict is VerifyVerdict.UNSUPPORTED
    # The span itself is genuinely in the passage, so only rule 3 failed.
    assert report.span_match.found


def test_the_other_paragraph_of_that_document_fails_the_same_way(
    by_passage, aliases, corpus_doc_ids, graph: Graph
):
    edge = next(e for e in graph.edges if e.edge_id == CROSS_PARAGRAPH_EDGE)
    paragraph_zero = by_passage["mint-2026-03-16-atf#p0"]
    assert aliases.mentions("ATF_PRICE", paragraph_zero.text)
    assert not aliases.mentions("AIRLINE_COSTS", paragraph_zero.text)

    screening = screen_edge(
        edge,
        [paragraph_zero, by_passage["mint-2026-03-16-atf#p1"]],
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert not screening.passed
    assert screening.verdict is VerifyVerdict.UNSUPPORTED
    assert screening.rule_failures == [RuleName.BOTH_VARIABLES_MENTIONED]


# ---------------------------------------------------------------------------
# Rule 4 - the span is in the passage, word for word
# ---------------------------------------------------------------------------


def test_an_exact_span_reports_document_offsets(by_passage, documents: dict[str, str]):
    passage = by_passage["bs-2026-03-13-importbill#p0"]
    span = "India's monthly import bill is expected to widen"
    match = check_span_verbatim(passage, span)
    assert match.found and match.kind is SpanMatchKind.EXACT
    assert documents[passage.doc_id][match.char_start : match.char_end] == span


def test_every_fixture_edge_span_is_exactly_where_it_says_it_is(cited, documents):
    for edge, passage in cited:
        match = check_span_verbatim(passage, edge.evidence_span)
        assert match.found and match.kind is SpanMatchKind.EXACT, edge.edge_id
        assert (
            documents[passage.doc_id][match.char_start : match.char_end] == edge.evidence_span
        ), edge.edge_id


@pytest.mark.parametrize(
    "rewrite",
    [
        pytest.param(lambda s: s.replace(" ", "  ", 1), id="double-space"),
        pytest.param(lambda s: s.replace(" ", "\n", 1), id="line-break"),
        pytest.param(lambda s: s.replace(" ", "\u00a0", 1), id="non-breaking-space"),
        pytest.param(lambda s: f"  {s}\n", id="padded"),
    ],
)
def test_a_span_differing_only_by_whitespace_still_matches(by_passage, rewrite):
    passage = by_passage["rbi-2026-03-18-mpc-minutes#p1"]
    span = "the Committee may have to consider further tightening"
    assert check_span_verbatim(passage, span).kind is SpanMatchKind.EXACT

    match = check_span_verbatim(passage, rewrite(span))
    assert match.found
    assert match.kind is SpanMatchKind.NORMALISED
    # Collapsing whitespace moves every later character, so no offset is claimed.
    assert match.char_start is None and match.char_end is None


def test_a_span_differing_only_by_a_curly_apostrophe_still_matches(by_passage):
    passage = by_passage["mint-2026-03-16-atf#p1"]
    span = "about 40 per cent of an Indian carrier's operating cost"
    assert check_span_verbatim(passage, span).kind is SpanMatchKind.EXACT
    curly = span.replace("'", "\u2019")
    assert check_span_verbatim(passage, curly).kind is SpanMatchKind.NORMALISED


@pytest.mark.parametrize(
    ("span", "why"),
    [
        (
            "the Committee will have to consider further tightening",
            "hedging: 'may' is not 'will'",
        ),
        (
            "the Committee could have to consider further tightening",
            "hedging: 'may' is not 'could'",
        ),
        (
            "the committee may have to consider further tightening",
            "casing is not normalised away",
        ),
        (
            "the Committee may have to consider tightening",
            "words dropped from the middle",
        ),
        (
            "the Committee may have to consider further tightening of policy",
            "words added at the end",
        ),
    ],
)
def test_a_span_that_changes_meaning_fails(by_passage, span: str, why: str):
    passage = by_passage["rbi-2026-03-18-mpc-minutes#p1"]
    match = check_span_verbatim(passage, span)
    assert not match.found, why
    assert passage.passage_id in match.reason


def test_a_hedging_change_fails_on_its_own(graph: Graph, by_passage, aliases, corpus_doc_ids):
    """ "may" -> "will" is the whole difference between conditional and direct."""
    edge = next(e for e in graph.edges if e.edge_id == "e9")
    passage = by_passage[edge.evidence_passage_id]
    inflated = edge.evidence_span.replace("may have to consider", "will have to consider")
    assert inflated != edge.evidence_span

    report = check_edge(
        edge,
        passage,
        as_of=graph.as_of,
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
        span=inflated,
    )
    assert report.rule_failures == [RuleName.SPAN_VERBATIM]
    assert report.verdict is VerifyVerdict.UNSUPPORTED


def test_a_number_change_fails(by_passage):
    passage = by_passage["bl-2026-03-12-brent100#p1"]
    assert check_span_verbatim(passage, "rose to $98.4 a barrel").found
    assert not check_span_verbatim(passage, "rose to $89.4 a barrel").found


def test_a_model_inferred_edge_has_nothing_to_match(
    graph: Graph, by_passage, aliases, corpus_doc_ids
):
    edge = next(e for e in graph.edges if e.edge_id == "e3")
    assert edge.evidence_span is None
    report = check_edge(
        edge,
        by_passage["bs-2026-03-13-importbill#p0"],
        as_of=graph.as_of,
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert RuleName.SPAN_VERBATIM in [RuleName(name) for name in report.rule_failures]
    assert "nothing to match" in report.outcome_for(RuleName.SPAN_VERBATIM).reason


@pytest.mark.parametrize("span", [None, "", "   ", "\n"])
def test_an_empty_span_is_not_a_match(by_passage, span):
    match = check_span_verbatim(by_passage["mint-2026-08-07-trade#p0"], span)
    assert not match.found
    assert "nothing to match" in match.reason


# ---------------------------------------------------------------------------
# The whole layer, on the fixture graph
# ---------------------------------------------------------------------------


def test_the_fixture_graphs_asserted_edges_clear_the_rules(
    cited, aliases, graph: Graph, corpus_doc_ids
):
    failed = {}
    for edge, passage in cited:
        report = check_edge(
            edge, passage, as_of=graph.as_of, corpus_doc_ids=corpus_doc_ids, aliases=aliases
        )
        if not report.passed:
            failed[edge.edge_id] = report.rule_failures
    assert failed == {CROSS_PARAGRAPH_EDGE: [RuleName.BOTH_VARIABLES_MENTIONED]}


def test_screen_edge_finds_the_one_eligible_passage(
    graph: Graph, passages: list[Passage], aliases, corpus_doc_ids
):
    edge = next(e for e in graph.edges if e.edge_id == "e1")
    screening = screen_edge(
        edge,
        passages,
        as_of=graph.as_of,
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert screening.passed
    assert [report.passage_id for report in screening.eligible] == [edge.evidence_passage_id]
    assert screening.verdict is None
    assert screening.rule_failures == []


def test_screen_edge_over_nothing_is_unsupported(graph: Graph, aliases, corpus_doc_ids):
    edge = next(e for e in graph.edges if e.edge_id == "e1")
    screening = screen_edge(
        edge, [], as_of=graph.as_of, corpus_doc_ids=corpus_doc_ids, aliases=aliases
    )
    assert not screening.passed
    assert screening.best is None
    assert screening.verdict is VerifyVerdict.UNSUPPORTED


def test_screen_edge_reports_the_passage_that_got_furthest(
    graph: Graph, by_passage, aliases, corpus_doc_ids
):
    edge = next(e for e in graph.edges if e.edge_id == "e1")
    out_of_corpus = by_passage["mint-2026-08-07-trade#p0"]
    near_miss = by_passage[edge.evidence_passage_id]

    screening = screen_edge(
        edge,
        [out_of_corpus, near_miss],
        as_of=graph.as_of,
        corpus_doc_ids=corpus_doc_ids - {near_miss.doc_id, out_of_corpus.doc_id},
        aliases=aliases,
    )
    assert not screening.passed
    # Both failed rule 1; the near miss failed only that, so it is reported.
    assert screening.best.passage_id == near_miss.passage_id
    assert screening.verdict is VerifyVerdict.OUT_OF_CORPUS


def test_check_claim_needs_no_edge(by_passage, aliases, corpus_doc_ids):
    """B5 and B9 hold a candidate relation before it is a schema object."""
    report = check_claim(
        "BRENT",
        "INDIAN_BASKET",
        "The Indian basket of crude rose to $98.4 a barrel due to the surge in Brent",
        by_passage["bl-2026-03-12-brent100#p1"],
        as_of=date(2026, 3, 20),
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
    )
    assert report.edge_id is None
    assert report.passed


def test_aliases_default_to_the_shipped_table(by_passage, corpus_doc_ids):
    """Omitting `aliases` loads `data/aliases.yaml` itself."""
    report = check_claim(
        "DXY",
        "INR_USD",
        "The rupee touched a record low of 96.90 to the dollar",
        by_passage["bl-2026-05-20-rupee-record#p0"],
        as_of=date(2026, 5, 20),
        corpus_doc_ids=corpus_doc_ids,
    )
    assert report.passed
