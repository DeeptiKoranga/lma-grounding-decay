"""Embedding restarts must reuse only identical model settings and passage text."""

import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest

from retrieval.bm25 import BM25Retriever
from retrieval.checkpoint import embed_checkpointed
from retrieval.dense import BGEEmbedder, DenseRetriever
from retrieval.pilot_runner import CachedCandidates
from retrieval.rerank import BGEReranker


class Embedder:
    model_id = "offline"
    revision = "test"
    max_length = 1024

    def __init__(self, fail_on_call=None):
        self.calls = []
        self.fail_on_call = fail_on_call

    def encode(self, texts):
        self.calls.append(texts)
        if len(self.calls) == self.fail_on_call:
            raise RuntimeError("interrupted")
        return [[1.0, 0.0] for text in texts]


def test_checkpoint_resumes_after_completed_blocks_and_reorders_safely(passages, tmp_path):
    path = tmp_path / "vectors.jsonl"
    first = Embedder(fail_on_call=2)
    with pytest.raises(RuntimeError, match="interrupted"):
        embed_checkpointed(passages[:4], embedder=first, path=path, checkpoint_every=2)
    assert len(json.loads(path.read_text())["entries"]) == 2
    resumed = Embedder()
    result = embed_checkpointed(passages[:4], embedder=resumed, path=path, checkpoint_every=2)
    assert result == [(1.0, 0.0)] * 4
    assert resumed.calls == [[p.title + "\n" + p.text for p in passages[2:4]]]
    unchanged = Embedder()
    assert embed_checkpointed(list(reversed(passages[:4])), embedder=unchanged, path=path) == result
    assert unchanged.calls == []


def test_checkpoint_reembeds_only_changed_or_new_passages(passages, tmp_path):
    path = tmp_path / "vectors.jsonl"
    embed_checkpointed(passages[:2], embedder=Embedder(), path=path)
    changed = passages[0].model_copy(update={"title": "Changed title"})
    fresh = Embedder()
    embed_checkpointed([changed, passages[1], passages[2]], embedder=fresh, path=path)
    assert fresh.calls == [
        [changed.title + "\n" + changed.text, passages[2].title + "\n" + passages[2].text]
    ]


def test_checkpoint_rejects_changed_truncation_or_invalid_vectors(passages, tmp_path):
    path = tmp_path / "vectors.jsonl"
    embed_checkpointed(passages[:1], embedder=Embedder(), path=path)
    changed = Embedder()
    changed.max_length = 512
    with pytest.raises(ValueError, match="preprocessing mismatch"):
        embed_checkpointed(passages[:1], embedder=changed, path=path)
    raw = json.loads(path.read_text())
    raw["entries"][0]["vector"] = [0, 0]
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="nonzero"):
        embed_checkpointed(passages[:1], embedder=Embedder(), path=path)


def test_checkpoint_reuses_identical_inputs_after_paragraph_ids_change(passages, tmp_path):
    path = tmp_path / "vectors.json"
    embed_checkpointed(passages[:2], embedder=Embedder(), path=path)
    shifted = [
        p.model_copy(update={"passage_id": f"shifted#{i}"}) for i, p in enumerate(passages[:2])
    ]
    resumed = Embedder()
    assert embed_checkpointed(shifted, embedder=resumed, path=path) == [(1.0, 0.0)] * 2
    assert resumed.calls == []
    assert {p.passage_id for p in shifted} <= {
        row["passage_id"] for row in json.loads(path.read_text())["entries"]
    }


def test_dense_v1_cache_rejected(passages, tmp_path):
    path = tmp_path / "old.jsonl"
    path.write_text(json.dumps({"version": 1}))
    with pytest.raises(ValueError, match="version"):
        DenseRetriever.load(path, embedder=Embedder())


def test_bge_adapter_sets_token_limit_and_bounds_query_cache(monkeypatch):
    constructed, calls = [], []

    class Model:
        def __init__(self, *args, **kwargs):
            constructed.append(kwargs)

        def encode(self, texts, **kwargs):
            assert self.max_seq_length == 512
            assert kwargs["batch_size"] == 2
            calls.append(texts)
            return [[1.0, 0.0] for text in texts]

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=Model)
    )
    adapter = BGEEmbedder(device="mps", batch_size=2, max_length=512, local_files_only=True)
    assert adapter.encode([]) == []
    assert adapter.encode(["q0"]) == adapter.encode(["q0"])
    assert calls == [["q0"]]
    for i in range(1, 130):
        adapter.encode([f"q{i}"])
    assert len(adapter._query_cache) == 128
    assert "q0" not in adapter._query_cache
    assert constructed[0]["device"] == "mps"
    # Avoid importing/releasing actual accelerators in an offline adapter test.
    monkeypatch.setattr("retrieval.dense.release_accelerator_memory", lambda: None)
    adapter.unload()
    assert adapter._model is None
    adapter.encode(["q129"])
    assert len(constructed) == 1


def test_reranker_constructor_receives_token_and_batch_limits(monkeypatch):
    constructed = []

    class Result(list):
        def tolist(self):
            return list(self)

    class Model:
        def __init__(self, *args, **kwargs):
            constructed.append(kwargs)

        def predict(self, pairs, **kwargs):
            assert kwargs["batch_size"] == 1
            return Result([1.0] * len(pairs))

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=Model))
    scorer = BGEReranker(device="mps", batch_size=1, max_length=512)
    assert scorer.score("query", ["passage"]) == [1.0]
    assert constructed[0]["max_length"] == 512
    monkeypatch.setattr("retrieval.rerank.release_accelerator_memory", lambda: None)
    scorer.unload()
    assert scorer._model is None


def test_cached_candidates_prevents_model_reloading_after_detach(passages):
    cached = CachedCandidates(BM25Retriever(passages))
    expected = cached.search("oil", as_of=date(2026, 3, 20), k=50)
    cached.detach()
    assert cached.search("oil", as_of=date(2026, 3, 20), k=3) == expected[:3]
    with pytest.raises(ValueError, match="uncached"):
        cached.search("new query", as_of=date(2026, 3, 20))
