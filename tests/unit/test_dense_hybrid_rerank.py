"""Offline A7-A11 regressions: filtering precedes retrieval and model scoring."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from retrieval.bm25 import Aliases, BM25Retriever, Hit
from retrieval.dense import BGEEmbedder, DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import BGEReranker, RerankingRetriever

ALIASES = Path(__file__).parents[2] / "data" / "aliases.yaml"
CUTOFF = date(2026, 3, 20)


class ConstantEmbedder:
    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


class RecordingScorer:
    def __init__(self):
        self.calls = []

    def score(self, query, texts):
        self.calls.append((query, texts))
        return list(range(len(texts)))


def test_dense_filters_before_top_k_and_uses_stable_ties(passages):
    embedder = ConstantEmbedder()
    retriever = DenseRetriever(list(reversed(passages)), embedder=embedder)
    visible = sorted([p for p in passages if p.visible_at(CUTOFF)], key=lambda p: p.passage_id)
    assert retriever.search("oil", as_of=CUTOFF, k=1) == [Hit(visible[0], 1.0)]
    assert DenseRetriever(visible, embedder=embedder).search(
        "oil", as_of=CUTOFF
    ) == retriever.search("oil", as_of=CUTOFF)
    assert retriever.search("oil", as_of=date(2026, 2, 28)) == []


def test_dense_source_and_variable_filters(passages):
    aliases = Aliases.load(ALIASES)
    retriever = DenseRetriever(passages, embedder=ConstantEmbedder(), aliases=aliases)
    hits = retriever.search(
        "oil",
        as_of=date(2026, 9, 30),
        k=50,
        source_kind="official",
        must_mention=["CPI_HEADLINE"],
    )
    assert hits
    assert all(
        h.passage.source_kind.value == "official"
        and aliases.mentions(h.passage.text, "CPI_HEADLINE")
        for h in hits
    )
    with pytest.raises(ValueError, match="unknown variable"):
        DenseRetriever([], embedder=ConstantEmbedder()).search(
            "oil", as_of=CUTOFF, must_mention=["FAKE_VAR"]
        )


@pytest.mark.parametrize("vectors", [[], [[1]], [[0, 0]], [[float("nan"), 1]], [[float("inf"), 0]]])
def test_dense_rejects_bad_embeddings(passages, vectors):
    with pytest.raises(ValueError):
        DenseRetriever(passages[:2], embedder=ConstantEmbedder(), vectors=vectors)


def test_dense_rejects_bad_query_vector(passages):
    embedder = ConstantEmbedder()
    retriever = DenseRetriever(passages[:1], embedder=embedder)
    embedder.encode = lambda texts: [[1, 2, 3]]
    with pytest.raises(ValueError, match="dimension"):
        retriever.search("oil", as_of=CUTOFF)


def test_dense_persistence_does_not_reembed_corpus(passages, tmp_path):
    embedder = ConstantEmbedder()
    retriever = DenseRetriever(passages, embedder=embedder)
    path = tmp_path / "dense.json"
    retriever.save(path)
    other_embedder = ConstantEmbedder()
    loaded = DenseRetriever.load(path, embedder=other_embedder)
    assert other_embedder.calls == []
    assert loaded.search("oil", as_of=CUTOFF) == retriever.search("oil", as_of=CUTOFF)
    assert other_embedder.calls == [["oil"]]
    with pytest.raises(ValueError, match="model/revision"):
        DenseRetriever.load(path, embedder=other_embedder, embedding_id="different-model")


def test_faiss_index_contains_only_eligible_rows(passages, monkeypatch):
    import sys

    added = []
    thread_limits = []

    class FakeFlatIndex:
        def __init__(self, dimension):
            assert dimension == 2

        def add(self, rows):
            self.rows = rows
            added.extend(rows)

        def search(self, queries, k):
            assert k == len(self.rows)
            assert queries == [(1.0, 0.0)]
            return [[1.0] * k], [list(reversed(range(k)))]

    monkeypatch.setitem(
        sys.modules,
        "faiss",
        SimpleNamespace(IndexFlatIP=FakeFlatIndex, omp_set_num_threads=thread_limits.append),
    )
    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace(asarray=lambda rows, dtype: rows))
    retriever = DenseRetriever(passages, embedder=ConstantEmbedder(), backend="faiss")
    hits = retriever.search("oil", as_of=CUTOFF, source_kind="official", k=1)
    eligible = [p for p in passages if p.visible_at(CUTOFF) and p.source_kind.value == "official"]
    assert len(added) == len(eligible)
    assert thread_limits == [1]
    assert hits == [Hit(sorted(eligible, key=lambda p: p.passage_id)[0], 1.0)]


def test_bge_adapters_do_not_load_models_at_construction():
    assert BGEEmbedder()._model is None
    assert BGEReranker()._model is None


def test_rrf_matches_formula_and_rejects_mismatched_snapshots(passages):
    lexical = BM25Retriever(passages)
    dense = DenseRetriever(passages, embedder=ConstantEmbedder())
    retriever = HybridRetriever(lexical, dense)
    expected = {}
    for backend in (lexical, dense):
        for rank, hit in enumerate(backend.search("oil", as_of=CUTOFF, k=50), 1):
            pid = hit.passage.passage_id
            expected[pid] = expected.get(pid, 0) + 1 / (60 + rank)
    hits = retriever.search("oil", as_of=CUTOFF, k=50)
    assert {h.passage.passage_id: h.score for h in hits} == expected
    assert all(h.passage.visible_at(CUTOFF) for h in hits)
    with pytest.raises(ValueError, match="same corpus"):
        HybridRetriever(lexical, DenseRetriever(passages[:1], embedder=ConstantEmbedder()))


def test_reranker_sees_only_eligible_candidates(passages):
    base = DenseRetriever(passages, embedder=ConstantEmbedder(), aliases=Aliases.load(ALIASES))
    scorer = RecordingScorer()
    retriever = RerankingRetriever(base, scorer=scorer)
    hits = retriever.search("oil", as_of=CUTOFF, source_kind="official", k=1)
    assert hits and all(h.passage.visible_at(CUTOFF) for h in hits)
    expected = base.search("oil", as_of=CUTOFF, source_kind="official", k=50)
    assert scorer.calls == [("oil", [h.passage.title + "\n" + h.passage.text for h in expected])]
    assert hits[0].passage == expected[-1].passage


@pytest.mark.parametrize("bad_scores", [[], [float("nan")], [float("inf")]])
def test_reranker_rejects_invalid_model_output(passages, bad_scores):
    base = DenseRetriever(passages[:1], embedder=ConstantEmbedder())
    scorer = RecordingScorer()
    scorer.score = lambda query, texts: bad_scores
    with pytest.raises(ValueError, match="finite score"):
        RerankingRetriever(base, scorer=scorer).search("oil", as_of=CUTOFF)


def test_wrappers_defend_against_unfiltered_backends(passages):
    base = DenseRetriever(passages, embedder=ConstantEmbedder())
    base.search = lambda *args, **kwargs: [Hit(p, 1.0) for p in reversed(passages)]
    scorer = RecordingScorer()
    reranked = RerankingRetriever(base, scorer=scorer).search("oil", as_of=CUTOFF, k=50)
    assert reranked and all(h.passage.visible_at(CUTOFF) for h in reranked)
    assert len(scorer.calls[0][1]) == sum(p.visible_at(CUTOFF) for p in passages)
    fused = HybridRetriever(BM25Retriever(passages), base).search("oil", as_of=CUTOFF, k=50)
    assert fused and all(h.passage.visible_at(CUTOFF) for h in fused)


def test_wrappers_reject_out_of_corpus_backend_passages(passages):
    base = DenseRetriever(passages, embedder=ConstantEmbedder())
    base.search = lambda *args, **kwargs: [
        Hit(passages[0].model_copy(update={"text": "tampered"}), 1)
    ]
    with pytest.raises(ValueError, match="outside"):
        RerankingRetriever(base, scorer=RecordingScorer()).search("oil", as_of=CUTOFF)


def test_hybrid_rejects_nonfinite_backend_scores(passages):
    base = DenseRetriever(passages, embedder=ConstantEmbedder())
    base.search = lambda *args, **kwargs: [Hit(passages[0], float("nan"))]
    with pytest.raises(ValueError, match="non-finite"):
        HybridRetriever(BM25Retriever(passages), base).search("oil", as_of=CUTOFF)


def test_all_wrappers_validate_empty_corpus_arguments():
    dense = DenseRetriever([], embedder=ConstantEmbedder())
    wrappers = [
        dense,
        HybridRetriever(BM25Retriever([]), dense),
        RerankingRetriever(dense, scorer=RecordingScorer()),
    ]
    for retriever in wrappers:
        for args in (
            {"query": ""},
            {"query": "oil", "k": 51},
            {"query": "oil", "source_kind": "fake"},
        ):
            with pytest.raises(ValueError):
                retriever.search(as_of=CUTOFF, **args)
