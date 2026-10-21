"""Check hand-computed metrics and predeclared tolerance, without real labels."""

from datetime import date

import pytest

from retrieval.bm25 import Aliases, Hit
from retrieval.pilot import (
    CONFIG_ORDER,
    EvidenceQuery,
    RetrievalMetrics,
    evaluate,
    evaluate_configs,
    select_simplest,
)


class OrderedRetriever:
    def __init__(self, passages):
        self.passages = tuple(passages)
        self.aliases = Aliases({})

    def search(self, query, **kwargs):
        return [Hit(p, 1) for p in self.passages]


def test_metrics_against_hand_calculation(passages):
    retriever = OrderedRetriever(passages)
    query = EvidenceQuery(
        query_id="q1",
        query="oil",
        as_of=date(2026, 9, 30),
        relevant_passage_ids={passages[1].passage_id, passages[6].passage_id},
    )
    result = evaluate(retriever, [query])
    assert result == RetrievalMetrics(1, 0.5, 1.0, 0.5)


def test_gold_must_exist_and_be_date_visible(passages):
    retriever = OrderedRetriever(passages)
    kwargs = {"query_id": "q1", "query": "oil", "as_of": date(2026, 3, 1)}
    with pytest.raises(ValueError, match="absent"):
        evaluate(retriever, [EvidenceQuery(**kwargs, relevant_passage_ids={"missing"})])
    with pytest.raises(ValueError, match="postdates"):
        evaluate(
            retriever, [EvidenceQuery(**kwargs, relevant_passage_ids={passages[-1].passage_id})]
        )
    with pytest.raises(ValueError, match="nonempty"):
        evaluate(retriever, [])


def test_selects_simplest_within_inclusive_tolerance():
    scores = {
        "bm25": RetrievalMetrics(20, 0.7, 0.77, 0.7),
        "bm25_alias": RetrievalMetrics(20, 0.7, 0.79, 0.7),
        "bge_m3": RetrievalMetrics(20, 0.7, 0.8, 0.7),
        "hybrid_rrf": RetrievalMetrics(20, 0.7, 0.8, 0.7),
    }
    assert select_simplest(scores) == "bm25"
    scores["bm25"] = RetrievalMetrics(20, 0.7, 0.769, 0.7)
    assert select_simplest(scores) == "bm25_alias"
    del scores["bge_m3"]
    with pytest.raises(ValueError, match="exactly"):
        select_simplest(scores)


def test_pilot_compares_all_configurations_on_identical_corpus_and_queries(passages):
    retrievers = {name: OrderedRetriever(passages) for name in CONFIG_ORDER}
    queries = [
        EvidenceQuery(
            query_id="q1",
            query="oil",
            as_of=date(2026, 9, 30),
            relevant_passage_ids={passages[0].passage_id},
        )
    ]
    results = evaluate_configs(retrievers, queries)
    assert len(results) == 4
    assert len(set(results.values())) == 1
    retrievers["bge_m3"] = OrderedRetriever(passages[:2])
    with pytest.raises(ValueError, match="one corpus snapshot"):
        evaluate_configs(retrievers, queries)
