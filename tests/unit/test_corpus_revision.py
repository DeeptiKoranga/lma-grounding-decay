import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from corpus import Document
from corpus.freeze import freeze_corpus


@pytest.fixture
def prepare(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.prepare_corpus_revision").prepare


def test_candidate_keeps_active_snapshot_and_review_work_unchanged(tmp_path, prepare):
    original = tmp_path / "active"
    body = "Oil costs increased and put pressure on the rupee. " * 5
    doc = Document(
        doc_id="economic_times-example",
        source="economic_times",
        url="https://economictimes.indiatimes.com/example",
        title="Oil costs and currency",
        published_at=datetime.fromisoformat("2026-04-02T12:00:00+05:30"),
        text=body.strip() + "\n\nALSO READ | A later unrelated announcement\n\n" + body.strip(),
        licence_note="Research use; no redistribution permission assumed.",
    )
    freeze_corpus([doc], original, version="fixture")
    digest = hashlib.sha256((original / "articles.jsonl").read_bytes()).hexdigest()
    raw = tmp_path / "extra"
    raw.mkdir()
    output = tmp_path / "candidate"
    result = prepare(frozen=original, extra_raw=raw, output=output, report=tmp_path / "audit.json")
    assert result["removed_navigation_paragraphs"] == 1
    assert result["changed_original_documents"] == 1
    assert result["human_review_complete"] is False
    assert result["candidate_articles_sha256"] != digest
    assert hashlib.sha256((original / "articles.jsonl").read_bytes()).hexdigest() == digest
    judgments = json.loads((output / "extraction_judgments.json").read_text())
    assert judgments["reviewer"] == ""
    assert judgments["items"][0]["extraction_accepted"] is None
    with pytest.raises(ValueError, match="candidate output exists"):
        prepare(frozen=original, extra_raw=raw, output=output, report=tmp_path / "other.json")


def test_corrupt_new_source_is_excluded_before_parsing(tmp_path, prepare):
    original, raw = tmp_path / "active", tmp_path / "extra" / "mint"
    freeze_corpus([], original, version="fixture")
    raw.mkdir(parents=True)
    (raw / "bad.html").write_text("not the checksummed article")
    (raw / "bad.meta.json").write_text(
        json.dumps(
            {
                "url": "https://www.livemint.com/example",
                "source": "mint",
                "accepted": True,
                "sha256": "0" * 64,
            }
        )
    )
    result = prepare(
        frozen=original,
        extra_raw=raw.parent,
        output=tmp_path / "candidate",
        report=tmp_path / "audit.json",
    )
    assert result["documents"] == 0
    assert result["added"] == []
    assert result["excluded"][0]["reason"] == "raw source checksum mismatch"
