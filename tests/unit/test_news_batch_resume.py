"""A bounded acquisition restart must progress past complete cached articles."""

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("missing_payload", [False, True])
def test_batch_resume_fills_attempt_budget_after_cached_articles(
    tmp_path, monkeypatch, missing_payload
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    batch = importlib.import_module("scripts.fetch.news_batch")
    output = tmp_path / "economic_times"
    output.mkdir()
    urls = [f"https://economictimes.indiatimes.com/crude-oil-story-{i}" for i in range(5)]
    ranked = batch.select_candidates(urls, limit=len(urls), seed="lma-corpus-v1-3")
    (output / "archive-2026-03-urls.jsonl").write_text(
        "".join(json.dumps({"url": url}) + "\n" for url in urls)
    )
    for index, url in enumerate(ranked[:2]):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        (output / f"{key}.meta.json").write_text("{}")
        if not (missing_payload and index == 1):
            (output / f"{key}.html").write_text("cached source")
    client = SimpleNamespace(requests=0, max_requests=100, get=lambda _: None)
    monkeypatch.setattr(batch, "Client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        batch,
        "parse_feed",
        lambda _: (["https://economictimes.indiatimes.com/sitemap-2026-03.xml"], []),
    )
    attempted = []

    def collect(client, candidates, directory, *, max_articles):
        assert directory == output and len(candidates) == max_articles
        attempted.extend(candidates)
        return {"downloaded": len(candidates)}

    monkeypatch.setattr(batch, "collect", collect)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "news_batch",
            "--source",
            "economic_times",
            "--raw",
            str(tmp_path),
            "--per-month",
            "2",
            "--months",
            "3",
        ],
    )
    batch.main()
    assert attempted == (ranked[1:3] if missing_payload else ranked[2:4])
    summary = json.loads((output / "batch_collection.json").read_text())
    assert summary["months"][0]["selected"] == 2
