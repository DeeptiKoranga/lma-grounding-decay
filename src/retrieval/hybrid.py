"""A7: reciprocal rank fusion over a shared, date-filtered corpus snapshot."""

from __future__ import annotations

import math
from collections import defaultdict

from .bm25 import Hit
from .filters import Retriever, checked_hits, validate_query


class HybridRetriever:
    def __init__(self, lexical: Retriever, dense: Retriever, *, rank_constant: float = 60):
        if not math.isfinite(rank_constant) or rank_constant <= 0:
            raise ValueError("RRF rank constant must be finite and positive")
        corpus = {p.passage_id: p for p in lexical.passages}
        if corpus != {p.passage_id: p for p in dense.passages}:
            raise ValueError("hybrid retrievers must use the same corpus snapshot")
        if lexical.aliases.mapping != dense.aliases.mapping:
            raise ValueError("hybrid retrievers must use the same variable aliases")
        self.lexical, self.dense = lexical, dense
        self.passages, self.aliases = lexical.passages, lexical.aliases
        self._corpus, self.rank_constant = corpus, rank_constant

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None) -> list[Hit]:
        args = validate_query(
            query,
            as_of=as_of,
            k=k,
            source_kind=source_kind,
            must_mention=must_mention,
            aliases=self.aliases,
        )
        scores = defaultdict(float)
        for retriever in (self.lexical, self.dense):
            hits = checked_hits(
                retriever.search(
                    args.query,
                    as_of=args.as_of,
                    k=50,
                    source_kind=args.source_kind,
                    must_mention=args.must_mention,
                ),
                self._corpus,
                args,
                self.aliases,
            )
            for rank, hit in enumerate(hits[:50], start=1):
                scores[hit.passage.passage_id] += 1 / (self.rank_constant + rank)
        ranked = sorted(scores, key=lambda pid: (-scores[pid], pid))
        return [Hit(self._corpus[pid], scores[pid]) for pid in ranked[: args.k]]
