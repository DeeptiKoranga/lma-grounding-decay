"""Fixture-only checks of sample review gates; these are not human judgments."""

import hashlib
import json
from datetime import date, datetime, timedelta

import pytest

from corpus import Document
from corpus.freeze import freeze_corpus
from corpus.review import SCOPE, digest, export, prepare


@pytest.fixture
def sample_review(tmp_path):
    docs = [
        Document(
            doc_id=f"source-{i}",
            source="source",
            url=f"https://example.org/{i}",
            title=f"Fixture article {i}",
            published_at=datetime.fromisoformat("2026-04-02T12:00:00+05:30"),
            text=f"Source paragraph {i} about oil and the rupee.",
            licence_note="Fixture only.",
        )
        for i in range(2)
    ]
    snapshot = tmp_path / "snapshot"
    freeze_corpus(docs, snapshot, version="fixture")
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "snapshot_sha256": digest(snapshot / "articles.jsonl"),
                "items": [
                    {
                        "doc_id": d.doc_id,
                        "source": d.source,
                        "url": d.url,
                        "text_sha256": hashlib.sha256(d.text.encode()).hexdigest(),
                    }
                    for d in docs
                ],
            }
        )
    )
    directory = tmp_path / "packet"
    prepare(snapshot=snapshot, sample=sample, curator="Fixture Curator", output=directory)
    return snapshot, sample, directory


def completed_fixture(directory):
    data = json.loads((directory / "judgments.json").read_text())
    data.update(
        reviewer="Fixture Independent Reviewer",
        reviewed_on=date.today().isoformat(),
        independent_review=True,
        accepted=True,
    )
    for row in data["items"]:
        row.update(
            extraction_accepted=True, publication_version_accepted=True, source_terms_reviewed=True
        )
    return data


def test_preparation_is_blank_and_does_not_change_originals(sample_review, tmp_path):
    snapshot, _, directory = sample_review
    before = digest(snapshot / "articles.jsonl")
    data = json.loads((directory / "judgments.json").read_text())
    assert data["reviewer"] == "" and not data["independent_review"] and not data["accepted"]
    assert all(row["extraction_accepted"] is None for row in data["items"])
    output = tmp_path / "no-receipt"
    with pytest.raises(ValueError, match="reviewer"):
        export(
            snapshot=snapshot,
            packet_path=directory / "packet.json",
            judgments_path=directory / "judgments.json",
            output=output,
        )
    assert not output.exists()
    assert digest(snapshot / "articles.jsonl") == before


def test_valid_fixture_receipt_is_bound_and_sample_limited(sample_review, tmp_path):
    snapshot, _, directory = sample_review
    (directory / "judgments.json").write_text(json.dumps(completed_fixture(directory)))
    receipt = export(
        snapshot=snapshot,
        packet_path=directory / "packet.json",
        judgments_path=directory / "judgments.json",
        output=tmp_path / "receipt",
    )
    assert receipt["items"] == 2 and receipt["scope"] == SCOPE
    assert receipt["corpus_sha256"] == digest(snapshot / "articles.jsonl")
    assert receipt["judgments_sha256"] == digest(directory / "judgments.json")
    with pytest.raises(FileExistsError):
        export(
            snapshot=snapshot,
            packet_path=directory / "packet.json",
            judgments_path=directory / "judgments.json",
            output=tmp_path / "receipt",
        )


@pytest.mark.parametrize(
    "fault",
    [
        "curator",
        "no_independence",
        "future_date",
        "missing",
        "duplicate",
        "rejected",
        "terms",
        "text_hash",
        "corpus",
        "parents",
        "packet",
    ],
)
def test_incomplete_stale_or_nonindependent_reviews_fail_before_output(
    sample_review, tmp_path, fault
):
    snapshot, _, directory = sample_review
    data = completed_fixture(directory)
    if fault == "curator":
        data["reviewer"] = "  FIXTURE   CURATOR "
    elif fault == "no_independence":
        data["independent_review"] = False
    elif fault == "future_date":
        data["reviewed_on"] = (date.today() + timedelta(days=1)).isoformat()
    elif fault == "missing":
        data["items"].pop()
    elif fault == "duplicate":
        data["items"].append(data["items"][0])
    elif fault == "rejected":
        data["items"][0]["extraction_accepted"] = False
    elif fault == "terms":
        data["items"][0]["source_terms_reviewed"] = None
    elif fault == "text_hash":
        data["items"][0]["text_sha256"] = "0" * 64
    elif fault == "corpus":
        with (snapshot / "articles.jsonl").open("a") as file:
            file.write("\n")
    elif fault == "parents":
        with (snapshot / "documents.jsonl").open("a") as file:
            file.write("\n")
    elif fault == "packet":
        with (directory / "packet.json").open("a") as file:
            file.write("\n")
    (directory / "judgments.json").write_text(json.dumps(data))
    output = tmp_path / "refused"
    with pytest.raises(ValueError):
        export(
            snapshot=snapshot,
            packet_path=directory / "packet.json",
            judgments_path=directory / "judgments.json",
            output=output,
        )
    assert not output.exists()


def test_changed_sample_is_not_silently_reused(sample_review, tmp_path):
    snapshot, sample, _ = sample_review
    data = json.loads(sample.read_text())
    data["items"][0]["text_sha256"] = "0" * 64
    sample.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="text hash"):
        prepare(
            snapshot=snapshot, sample=sample, curator="Fixture Curator", output=tmp_path / "changed"
        )
    assert not (tmp_path / "changed").exists()
