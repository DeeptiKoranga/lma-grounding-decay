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


def test_original_news_reparse_restores_visible_lead_from_verified_raw(
    tmp_path, prepare, monkeypatch
):
    import sys
    from types import SimpleNamespace

    from corpus import parse_html

    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **kw: None))
    body = "Oil costs increased and put pressure on the rupee. " * 5
    lead = "Mumbai: " + body.strip()
    url = "https://economictimes.indiatimes.com/verified-original"
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-04-02",
        "articleBody": lead + " " + body.strip(),
    }
    html = f'<meta property="og:title" content="Crude and rupee"><script type="application/ld+json">{json.dumps(record)}</script><div class="artText">{lead}<br></div><article><p>{body}</p></article>'
    parsed = parse_html(html, source="economic_times", url=url)
    old = Document.model_validate({**parsed.model_dump(), "text": body.strip()})
    active = tmp_path / "active"
    freeze_corpus([old], active, version="old")
    raw = tmp_path / "raw" / "economic_times"
    raw.mkdir(parents=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    payload = html.encode()
    (raw / f"{key}.html").write_bytes(payload)
    (raw / f"{key}.meta.json").write_text(
        json.dumps(
            {
                "accepted": True,
                "url": url,
                "source": "economic_times",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    )
    extra = tmp_path / "extra"
    extra.mkdir()
    result = prepare(
        frozen=active,
        extra_raw=extra,
        output=tmp_path / "candidate",
        report=tmp_path / "audit.json",
        reparse_raw=raw.parent,
        version="test-v3",
    )
    assert result["reparsed_original_news"] == 1
    assert result["restored_original_paragraphs"] == 1
    updated = json.loads((tmp_path / "candidate/snapshot/documents.jsonl").read_text())
    assert updated["text"].startswith(lead + "\n\n")
