"""A6/A11 regressions, especially no future evidence or future-dependent scoring."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from retrieval import Aliases, BM25Retriever
from schema import load_ontology

ALIASES = Path(__file__).parents[2] / "data" / "aliases.yaml"


def test_aliases_cover_the_closed_ontology():
    aliases = Aliases.load(ALIASES)
    assert set(aliases.mapping) == set(load_ontology().ids())
    assert aliases.mentions("A weaker rupee lifted jet fuel costs.", "INR_USD")
    assert aliases.mentions("A weaker rupee lifted jet fuel costs.", "ATF_PRICE")
    assert not aliases.mentions("A recipe for growth", "CPI_HEADLINE")
    with pytest.raises(ValueError, match="unknown"):
        Aliases({"FAKE_VAR": ["fake"]})


def test_alias_expansion_is_optional_and_bidirectional(passages):
    retriever = BM25Retriever(passages, aliases=Aliases.load(ALIASES))
    assert retriever.search("INR_USD", as_of=date(2026, 9, 30))
    assert retriever.search("INR_USD", as_of=date(2026, 9, 30), expand_aliases=False) == []
    assert "inr" in retriever.aliases.expand("rupee")


def test_all_query_terms_at_every_cutoff_exclude_future_documents(passages):
    retriever = BM25Retriever(passages, aliases=Aliases.load(ALIASES))
    queries = ["Brent rupee inflation", "INR_USD", "", "shipping", "bond liquidity"]
    queries.extend(p.text for p in passages)
    for day in sorted({p.published_at.date() for p in passages}):
        for cutoff in (day - timedelta(days=1), day):
            for query in queries:
                if not query:
                    continue
                hits = retriever.search(query, as_of=cutoff, k=50)
                assert all(h.passage.published_at.date() <= cutoff for h in hits)


def test_future_documents_cannot_change_scores_or_ranking(passages):
    cutoff = date(2026, 3, 20)
    visible = [p for p in passages if p.visible_at(cutoff)]
    before = BM25Retriever(visible)
    after = BM25Retriever(passages)
    assert before.search("rupee oil import inflation", as_of=cutoff) == after.search(
        "rupee oil import inflation", as_of=cutoff
    )
    assert after.search("Brent", as_of=date(2026, 2, 28)) == []


def test_date_filter_precedes_top_k_and_cutoff_is_inclusive(passages):
    retriever = BM25Retriever(passages)
    cutoff = date(2026, 3, 12)
    hits = retriever.search("Brent", as_of=cutoff, k=1)
    assert len(hits) == 1
    assert hits[0].passage.published_at.date() == cutoff
    assert retriever.search("borrowing liquidity", as_of=cutoff) == []


def test_source_and_both_variable_filters(passages):
    retriever = BM25Retriever(passages, aliases=Aliases.load(ALIASES))
    hits = retriever.search("inflation", as_of=date(2026, 9, 30), source_kind="official")
    assert hits and all(h.passage.source_kind.value == "official" for h in hits)
    hits = retriever.search(
        "Brent", as_of=date(2026, 9, 30), must_mention=["BRENT", "INDIAN_BASKET"]
    )
    assert hits
    # The shared verifier alias table also treats 'crude' as a Brent mention.
    # Requiring a literal 'Brent' would discard the handed-over surface forms.
    assert all("Indian basket" in h.passage.text for h in hits)
    assert all("Brent" in h.passage.text or "crude" in h.passage.text for h in hits)
    with pytest.raises(ValueError, match="unknown variable"):
        retriever.search("oil", as_of=date(2026, 9, 30), must_mention=["FAKE_VAR"])


def test_serialisation_and_stable_tie_breaking(passages, tmp_path):
    retriever = BM25Retriever(passages)
    path = tmp_path / "passages.jsonl"
    retriever.save(path)
    loaded = BM25Retriever.from_jsonl(path)
    expected = retriever.search("Brent", as_of=date(2026, 3, 20))
    assert loaded.search("Brent", as_of=date(2026, 3, 20)) == expected
    assert (
        BM25Retriever(list(reversed(passages))).search("Brent", as_of=date(2026, 3, 20)) == expected
    )
    with pytest.raises(ValueError, match="unique"):
        BM25Retriever([passages[0], passages[0]])


def test_search_arguments_are_validated_even_on_empty_corpus():
    retriever = BM25Retriever([])
    for kwargs in ({"query": ""}, {"query": "x", "k": 51}, {"query": "x", "source_kind": "wrong"}):
        with pytest.raises(ValueError):
            retriever.search(as_of=date(2026, 3, 20), **kwargs)
