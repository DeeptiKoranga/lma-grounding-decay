"""Construct one retrieval configuration without loading unused heavy backends."""

from pathlib import Path

from schema import Passage

from .bm25 import Aliases, BM25Retriever
from .checkpoint import embed_checkpointed
from .dense import BGEEmbedder, DenseRetriever
from .hybrid import HybridRetriever
from .pilot import CONFIG_ORDER, PlainBM25
from .rerank import BGEReranker, RerankingRetriever


def build_retriever(
    passages: list[Passage],
    *,
    aliases: Aliases,
    config: str = "bm25_alias",
    rerank: bool = False,
    device: str = "cpu",
    local_files_only: bool = False,
    embedding_model: str = "BAAI/bge-m3",
    embedding_revision: str | None = None,
    reranker_model: str = "BAAI/bge-reranker-v2-m3",
    reranker_revision: str | None = None,
    dense_backend: str = "exact",
    dense_index: Path | None = None,
    embedding_checkpoint: Path | None = None,
    checkpoint_every: int = 100,
    embedding_batch_size: int = 2,
    reranker_batch_size: int = 1,
    max_length: int = 1024,
):
    if config not in CONFIG_ORDER:
        raise ValueError(f"unknown retrieval configuration: {config}")
    lexical = BM25Retriever(passages, aliases=aliases)
    if config == "bm25":
        result = PlainBM25(lexical)
    elif config == "bm25_alias":
        result = lexical
    else:
        embedder = BGEEmbedder(
            model=embedding_model,
            device=device,
            revision=embedding_revision,
            local_files_only=local_files_only,
            batch_size=embedding_batch_size,
            max_length=max_length,
        )
        if dense_index is not None and dense_index.exists():
            dense = DenseRetriever.load(
                dense_index,
                embedder=embedder,
                aliases=aliases,
                backend=dense_backend,
            )
            if {p.passage_id: p for p in dense.passages} != {p.passage_id: p for p in passages}:
                raise ValueError("saved dense index does not match the selected corpus snapshot")
        else:
            vectors = (
                embed_checkpointed(
                    passages,
                    embedder=embedder,
                    path=embedding_checkpoint,
                    checkpoint_every=checkpoint_every,
                )
                if embedding_checkpoint is not None
                else None
            )
            dense = DenseRetriever(
                passages,
                embedder=embedder,
                aliases=aliases,
                backend=dense_backend,
                vectors=vectors,
            )
            if dense_index is not None:
                dense_index.parent.mkdir(parents=True, exist_ok=True)
                dense.save(dense_index)
        result = dense if config == "bge_m3" else HybridRetriever(lexical, dense)
    if rerank:
        result = RerankingRetriever(
            result,
            scorer=BGEReranker(
                model=reranker_model,
                device=device,
                revision=reranker_revision,
                local_files_only=local_files_only,
                batch_size=reranker_batch_size,
                max_length=max_length,
            ),
        )
    return result
