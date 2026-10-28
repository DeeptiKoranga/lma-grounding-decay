"""Integration regressions for resumable collection and the shared alias handover."""

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus.__main__ import main as rebuild
from retrieval import Aliases


def test_alias_loader_accepts_verifier_and_legacy_formats(tmp_path):
    path = tmp_path / "aliases.yaml"
    path.write_text(
        "aliases:\n  INR_USD:\n    surface_forms: [rupee]\n    expand_for_bm25: false\n"
    )
    aliases = Aliases.load(path)
    assert aliases.mentions("The rupee weakened.", "INR_USD")
    assert aliases.expand("rupee") == ["rupee"]
    path.write_text("variables:\n  INR_USD: [rupee]\n")
    assert "inr" in Aliases.load(path).expand("rupee")


@pytest.mark.parametrize("payload", ["[]", "aliases: []", "aliases: {INR_USD: {}}"])
def test_invalid_alias_tables_fail_clearly(tmp_path, payload):
    path = tmp_path / "aliases.yaml"
    path.write_text(payload)
    with pytest.raises(ValueError):
        Aliases.load(path)


@pytest.mark.parametrize("metadata", [{}, [], {"sha256": "wrong"}])
def test_corrupt_cache_does_not_abort_collection(tmp_path, monkeypatch, metadata):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    from scripts.fetch.collect import collect
    from scripts.fetch.sources import SOURCES

    url = "https://www.livemint.com/rupee"
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    (tmp_path / f"{key}.meta.json").write_text(json.dumps(metadata))
    (tmp_path / f"{key}.html").write_bytes(b"cached")
    client = SimpleNamespace(source=SOURCES["mint"], get=lambda url: pytest.fail("cache hit"))
    counts = collect(client, [url], tmp_path, max_articles=1)
    assert counts["rejected"] == 1
    event = json.loads((tmp_path / "collection_log.jsonl").read_text())
    assert event["status"] == "rejected"


def test_rebuild_logs_non_object_cache_metadata(tmp_path, monkeypatch):
    raw = tmp_path / "raw" / "mint"
    raw.mkdir(parents=True)
    (raw / "bad.meta.json").write_text("[]")
    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["corpus", "--raw", str(raw.parent), "--output", str(output)])
    rebuild()
    assert "JSON object" in (output / "parse_errors.jsonl").read_text()
    assert (output / "documents.jsonl").read_text() == ""
