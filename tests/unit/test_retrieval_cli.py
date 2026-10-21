"""Exercise selectable retrieval and pilot commands without downloading models."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

from retrieval import Aliases, BM25Retriever
from retrieval.__main__ import main as search_main
from retrieval.dense import DenseRetriever
from retrieval.factory import build_retriever
from retrieval.pilot_runner import main as pilot_main

ALIASES = Path(__file__).parents[2] / "data/aliases.yaml"


class StubEmbedder:
    model_id = "offline-test-only"

    def __init__(self, **kwargs):
        pass

    def encode(self, texts):
        return [[1.0, float("rupee" in text.casefold())] for text in texts]


def test_default_factory_never_constructs_dense_model(passages, monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("BM25 must not load embedding models")

    monkeypatch.setattr("retrieval.factory.BGEEmbedder", forbidden)
    retriever = build_retriever(passages, aliases=Aliases.load(ALIASES))
    assert isinstance(retriever, BM25Retriever)
    assert retriever.search("rupee", as_of=date(2026, 3, 20))


def test_cli_keeps_date_filter_and_returns_valid_json(passages, tmp_path, monkeypatch, capsys):
    corpus = tmp_path / "corpus.jsonl"
    BM25Retriever(passages).save(corpus)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "retrieval",
            "rupee",
            "--corpus",
            str(corpus),
            "--aliases",
            str(ALIASES),
            "--as-of",
            "2026-03-12",
        ],
    )
    search_main()
    output = json.loads(capsys.readouterr().out)
    assert output["passages"]
    assert len(output["passages"]) == len(output["scores"])
    assert all(p["published_at"][:10] <= "2026-03-12" for p in output["passages"])


def test_dense_cache_cannot_silently_use_another_corpus(passages, tmp_path, monkeypatch):
    monkeypatch.setattr("retrieval.factory.BGEEmbedder", StubEmbedder)
    index = tmp_path / "vectors.json"
    DenseRetriever(passages[:1], embedder=StubEmbedder()).save(index)
    with pytest.raises(ValueError, match="corpus snapshot"):
        build_retriever(passages, aliases=Aliases({}), config="bge_m3", dense_index=index)


def test_pilot_rejects_incomplete_pairs_before_loading_models(tmp_path, monkeypatch, capsys):
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "--pairs",
            str(pairs),
            "--output",
            str(tmp_path / "pilot.md"),
            "--embedding-revision",
            "test",
        ],
    )
    with pytest.raises(SystemExit) as error:
        pilot_main()
    assert error.value.code == 2
    assert "exactly 20" in capsys.readouterr().err


def test_smoke_pilot_records_inputs_without_claiming_research_decision(
    passages, tmp_path, monkeypatch
):
    monkeypatch.setattr("retrieval.factory.BGEEmbedder", StubEmbedder)
    corpus = tmp_path / "corpus.jsonl"
    BM25Retriever(passages).save(corpus)
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(
        json.dumps(
            {
                "query_id": "smoke",
                "query": "Brent",
                "as_of": "2026-09-30",
                "relevant_passage_ids": [passages[0].passage_id],
            }
        )
        + "\n"
    )
    report = tmp_path / "smoke.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "--pairs",
            str(pairs),
            "--corpus",
            str(corpus),
            "--aliases",
            str(ALIASES),
            "--output",
            str(report),
            "--embedding-revision",
            "test-only",
            "--smoke",
        ],
    )
    pilot_main()
    text = report.read_text()
    assert "SMOKE CHECK ONLY; no research decision" in text
    assert "Corpus SHA-256" in text and "Pair file SHA-256" in text
    assert all(name in text for name in ("bm25", "bm25_alias", "bge_m3", "hybrid_rrf"))
