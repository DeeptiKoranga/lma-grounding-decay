"""Snapshot reproducibility and deduplication use only synthetic local documents."""

import hashlib
import json
from datetime import datetime
from zipfile import ZipFile

import pytest

from corpus.dedup import deduplicate
from corpus.documents import Document
from corpus.freeze import freeze_corpus, load_documents
from schema import Passage, SourceKind

LEDE = (
    "Brent crude rose after supply disruptions in the Middle East raised shipping costs. "
    "India imports most of its oil and higher prices could widen the trade deficit. "
    "The rupee fell as importers sought dollars and markets assessed inflation risks."
)


def document(doc_id="mint-a", **changes):
    values = {
        "doc_id": doc_id,
        "source": "mint",
        "source_kind": SourceKind.NEWS,
        "url": f"https://www.livemint.com/{doc_id}",
        "published_at": datetime.fromisoformat("2026-03-12T10:00:00+05:30"),
        "title": "Oil supply disruption weighs on India's rupee",
        "text": LEDE + "\n\nAnalysts assessed the outlook.",
        "licence_note": "Test corpus; synthetic text.",
    }
    values.update(changes)
    return Document(**values)


def test_exact_text_duplicate_is_removed_even_with_different_headline():
    first = document()
    second = document("mint-b", title="A different syndicated headline")
    result = deduplicate([second, first])
    assert result.documents == (first,)
    assert result.duplicates[0].removed_doc_id == second.doc_id
    assert result.duplicates[0].retained_doc_id == first.doc_id
    assert result.duplicates[0].method == "exact-text"


def test_minhash_near_duplicate_verifies_similarity_and_keeps_distinct_article():
    original = document()
    near = document("mint-b", text=LEDE.replace("rose", "climbed") + "\n\nNew body paragraph.")
    distinct = document(
        "rbi-a",
        source="rbi",
        source_kind=SourceKind.OFFICIAL,
        title="Monetary policy committee announces decision",
        text="The monetary policy committee decided to keep the policy repo rate unchanged.",
    )
    result = deduplicate([near, distinct, original])
    assert {doc.doc_id for doc in result.documents} == {original.doc_id, distinct.doc_id}
    assert len(result.duplicates) == 1
    assert result.duplicates[0].method == "title-lede-minhash"
    assert 0.85 <= result.duplicates[0].similarity < 1
    assert deduplicate([original, distinct, near]) == result


def test_duplicate_ids_and_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError, match="duplicate document ids"):
        deduplicate([document(), document()])
    for threshold in (0, -1, 1.1, float("nan")):
        with pytest.raises(ValueError, match="threshold"):
            deduplicate([document()], threshold=threshold)


def test_minhash_collision_cannot_remove_unrelated_copy(monkeypatch):
    monkeypatch.setattr("corpus.dedup.minhash", lambda _: (0,) * 128)
    original = document()
    distinct = document(
        "rbi-a",
        title="Monetary policy committee announces decision",
        text="The monetary policy committee decided to keep the policy repo rate unchanged.",
    )
    result = deduplicate([original, distinct])
    assert len(result.documents) == 2
    assert not result.duplicates


def test_representative_uses_actual_timestamp_across_timezones():
    later = document("mint-a", published_at=datetime.fromisoformat("2026-03-12T10:00:00+00:00"))
    earlier = document("mint-b", published_at=datetime.fromisoformat("2026-03-12T11:00:00+05:30"))
    result = deduplicate([later, earlier])
    assert result.documents == (earlier,)


def test_snapshot_reproducible_archive_manifest_and_exact_offsets(tmp_path):
    original = document()
    duplicate = document("mint-b")
    official = document(
        "rbi-a",
        source="rbi",
        source_kind=SourceKind.OFFICIAL,
        title="RBI statement",
        text="The central bank retained the policy rate.\n\nIt assessed the inflation outlook.",
        published_at=datetime.fromisoformat("2026-04-08T12:00:00+05:30"),
    )
    one = freeze_corpus([official, original, duplicate], tmp_path / "one")
    two = freeze_corpus([duplicate, original, official], tmp_path / "two")
    assert one.archive_sha256 == two.archive_sha256
    assert one.provisional
    assert (one.documents, one.passages, one.duplicates) == (2, 4, 1)
    assert (one.news_documents, one.official_documents) == (1, 1)
    manifest = one.manifest.read_text()
    assert "PROVISIONAL" in manifest
    assert "899 news, 59 official" in manifest
    assert "| mint | 1 | 0 |" in manifest
    assert "| rbi | 0 | 1 |" in manifest
    assert "Test corpus; synthetic text." in manifest
    assert one.manifest.read_bytes() == two.manifest.read_bytes()
    archive_path = tmp_path / "one" / "corpus-v1.zip"
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == one.archive_sha256
    with ZipFile(archive_path) as archive:
        assert sorted(archive.namelist()) == [
            "articles.jsonl",
            "documents.jsonl",
            "duplicates.jsonl",
        ]
        docs = {
            row["doc_id"]: row
            for row in map(json.loads, archive.read("documents.jsonl").decode().splitlines())
        }
        for line in archive.read("articles.jsonl").decode().splitlines():
            passage = Passage.model_validate_json(line)
            assert (
                docs[passage.doc_id]["text"][passage.char_start : passage.char_end] == passage.text
            )
        audit = json.loads(archive.read("duplicates.jsonl"))
        assert audit["removed_doc_id"] == duplicate.doc_id


def test_empty_corpus_is_provisional_and_does_not_claim_completed_collection(tmp_path):
    result = freeze_corpus([], tmp_path)
    assert result.provisional
    assert result.documents == result.passages == result.duplicates == 0
    assert "No documents collected" in result.manifest.read_text()
    assert "900 news, 60 official" in result.manifest.read_text()


def test_existing_snapshot_requires_explicit_overwrite(tmp_path):
    first = freeze_corpus([document()], tmp_path)
    with pytest.raises(FileExistsError, match="snapshot exists"):
        freeze_corpus([], tmp_path)
    assert first.manifest.read_text().count("Retained: 1 documents") == 1
    second = freeze_corpus([], tmp_path, overwrite=True)
    assert second.documents == 0


def test_input_errors_report_location_before_writing_any_snapshot(tmp_path):
    source = tmp_path / "bad.jsonl"
    source.write_text(document().model_dump_json() + "\n{}\n")
    with pytest.raises(ValueError, match=r"bad.jsonl:2: invalid document"):
        load_documents(source)
    with pytest.raises(ValueError, match="version"):
        freeze_corpus([document()], tmp_path / "output", version="../bad")
    assert not (tmp_path / "output").exists()
