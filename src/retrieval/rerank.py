"""A9: optional cross-encoder reranking of 50 eligible first-stage candidates."""

from __future__ import annotations

import math
from typing import Protocol

from .bm25 import Hit
from .filters import Retriever, checked_hits, validate_query


class PairScorer(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class BGEReranker:
    """Lazy adapter; official usage: https://huggingface.co/BAAI/bge-reranker-v2-m3."""

    def __init__(
        self,
        model="BAAI/bge-reranker-v2-m3",
        *,
        device="cpu",
        batch_size=8,
        revision=None,
        local_files_only=False,
    ):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.model_name, self.device, self.batch_size = model, device, batch_size
        self.revision, self.local_files_only = revision, local_files_only
        self._model = None

    def score(self, query, texts):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError("BGE reranking requires sentence-transformers") from exc
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                revision=self.revision,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
        return self._model.predict(
            [(query, text) for text in texts],
            batch_size=self.batch_size,
            show_progress_bar=False,
        ).tolist()


class RerankingRetriever:
    def __init__(self, retriever: Retriever, *, scorer: PairScorer):
        self.retriever, self.scorer = retriever, scorer
        self.passages, self.aliases = retriever.passages, retriever.aliases
        self._corpus = {p.passage_id: p for p in self.passages}

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None) -> list[Hit]:
        args = validate_query(
            query,
            as_of=as_of,
            k=k,
            source_kind=source_kind,
            must_mention=must_mention,
            aliases=self.aliases,
        )
        hits = checked_hits(
            self.retriever.search(
                args.query,
                as_of=args.as_of,
                k=50,
                source_kind=args.source_kind,
                must_mention=args.must_mention,
            ),
            self._corpus,
            args,
            self.aliases,
        )[:50]
        if not hits:
            return []
        scores = [
            float(s)
            for s in self.scorer.score(
                args.query, [h.passage.title + "\n" + h.passage.text for h in hits]
            )
        ]
        if len(scores) != len(hits) or not all(math.isfinite(s) for s in scores):
            raise ValueError("reranker must return one finite score per candidate")
        ranked = sorted(
            zip(hits, scores, strict=True), key=lambda pair: (-pair[1], pair[0].passage.passage_id)
        )
        return [Hit(hit.passage, score) for hit, score in ranked[: args.k]]
