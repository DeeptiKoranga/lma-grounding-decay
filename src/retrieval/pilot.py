"""A8/A9: passage-level retrieval metrics and the predeclared selection rule.

This module evaluates supplied, independently annotated query/evidence pairs.
It never invents gold labels or treats fixture scores as experimental results.
MRR is truncated at the same 50-candidate pool used by reranking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .filters import Retriever, checked_hits, validate_query

CONFIG_ORDER = ("bm25", "bm25_alias", "bge_m3", "hybrid_rrf")


class EvidenceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    as_of: date
    relevant_passage_ids: frozenset[str] = Field(min_length=1)


@dataclass(frozen=True)
class RetrievalMetrics:
    queries: int
    recall_at_5: float
    recall_at_10: float
    mrr_at_50: float


class PlainBM25:
    """Expose the no-alias configuration with the same search interface."""

    def __init__(self, retriever):
        self.retriever = retriever
        self.passages, self.aliases = retriever.passages, retriever.aliases

    def search(self, *args, **kwargs):
        return self.retriever.search(*args, **kwargs, expand_aliases=False)


def evaluate(retriever: Retriever, queries: list[EvidenceQuery]) -> RetrievalMetrics:
    if not queries or len({q.query_id for q in queries}) != len(queries):
        raise ValueError("pilot queries must be nonempty with unique query ids")
    corpus = {p.passage_id: p for p in retriever.passages}
    recall5, recall10, rr = [], [], []
    for query in queries:
        missing = query.relevant_passage_ids - corpus.keys()
        if missing:
            raise ValueError(f"gold passage ids are absent from corpus: {sorted(missing)}")
        if any(not corpus[pid].visible_at(query.as_of) for pid in query.relevant_passage_ids):
            raise ValueError(f"gold evidence postdates as-of for query {query.query_id}")
        args = validate_query(
            query.query,
            as_of=query.as_of,
            k=50,
            source_kind="any",
            must_mention=[],
            aliases=retriever.aliases,
        )
        hits = checked_hits(
            retriever.search(query.query, as_of=query.as_of, k=50),
            corpus,
            args,
            retriever.aliases,
        )[:50]
        ids = [h.passage.passage_id for h in hits]
        relevant = query.relevant_passage_ids
        recall5.append(len(set(ids[:5]) & relevant) / len(relevant))
        recall10.append(len(set(ids[:10]) & relevant) / len(relevant))
        rr.append(next((1 / rank for rank, pid in enumerate(ids, 1) if pid in relevant), 0))
    count = len(queries)
    return RetrievalMetrics(
        count,
        math.fsum(recall5) / count,
        math.fsum(recall10) / count,
        math.fsum(rr) / count,
    )


def select_simplest(
    metrics: dict[str, RetrievalMetrics],
    *,
    tolerance: float = 0.03,
    order: tuple[str, ...] = CONFIG_ORDER,
) -> str:
    """Require all four first-stage configs; reranking is a separate comparison."""
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 1:
        raise ValueError("selection tolerance must be finite and between 0 and 1")
    if not order or len(set(order)) != len(order) or set(metrics) != set(order):
        raise ValueError("provide exactly the declared retrieval configurations")
    counts = {row.queries for row in metrics.values()}
    if len(counts) != 1 or next(iter(counts)) < 1:
        raise ValueError("all configurations must evaluate the same nonempty query count")
    if any(
        not math.isfinite(value) or not 0 <= value <= 1
        for row in metrics.values()
        for value in (row.recall_at_5, row.recall_at_10, row.mrr_at_50)
    ):
        raise ValueError("retrieval metrics must be finite and between 0 and 1")
    best = max(row.recall_at_10 for row in metrics.values())
    return next(name for name in order if best - metrics[name].recall_at_10 <= tolerance + 1e-12)


def evaluate_configs(
    retrievers: dict[str, Retriever], queries: list[EvidenceQuery]
) -> dict[str, RetrievalMetrics]:
    """Compare all four configurations using exactly the same evidence/corpus.

    A smoke check may use fewer pairs; the project pilot requires 20 real pairs
    and must be labelled pending until those independent annotations exist.
    """
    if set(retrievers) != set(CONFIG_ORDER):
        raise ValueError("pilot requires all four declared retrieval configurations")
    snapshots = [{p.passage_id: p for p in retriever.passages} for retriever in retrievers.values()]
    if any(snapshot != snapshots[0] for snapshot in snapshots[1:]):
        raise ValueError("pilot configurations must share one corpus snapshot")
    return {name: evaluate(retrievers[name], queries) for name in CONFIG_ORDER}
