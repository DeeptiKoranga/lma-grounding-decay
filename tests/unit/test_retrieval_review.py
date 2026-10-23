"""Review handoff must not leak ranks or accept stale/incomplete attestations."""

import json
import sys
from pathlib import Path

import pytest

from retrieval.bm25 import BM25Retriever
from retrieval.pilot import EvidenceQuery
from retrieval.pilot_runner import main as pilot_main
from retrieval.review import export_review, prepare_review, sha256, validate_receipt

ALIASES = Path(__file__).parents[2] / "data/aliases.yaml"


@pytest.fixture
def review_files(passages, tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    BM25Retriever(passages).save(corpus)
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(
        json.dumps(
            {
                "query_id": "q1",
                "query": "oil",
                "as_of": "2026-03-12",
                "relevant_passage_ids": [passages[0].passage_id],
            }
        )
        + "\n"
    )
    output = tmp_path / "review"
    summary = prepare_review(
        pairs=pairs, corpus=corpus, aliases=ALIASES, output=output, curator="Curator", pool_size=3
    )
    return corpus, pairs, output, summary


def complete_judgments(output):
    packet = json.loads((output / "packet.json").read_text())
    path = output / "judgments.json"
    judgments = json.loads(path.read_text())
    judgments.update(
        reviewer="Reviewer",
        reviewed_on="2026-10-23",
        independent_review=True,
        blinded_to_results=True,
    )
    for row in judgments["queries"]:
        row["suitable"] = True
    for row, candidate in zip(judgments["candidates"], packet["candidates"], strict=True):
        row["relevant"] = True
        row["evidence_span"] = candidate["passage"]["text"][:25]
    path.write_text(json.dumps(judgments))
    return judgments


def export(corpus, output, target):
    return export_review(
        packet_path=output / "packet.json",
        judgments_path=output / "judgments.json",
        corpus=corpus,
        output=target,
    )


def test_packet_is_deterministic_blind_and_date_visible(review_files, tmp_path):
    corpus, pairs, output, summary = review_files
    duplicate = tmp_path / "duplicate"
    assert (
        prepare_review(
            pairs=pairs,
            corpus=corpus,
            aliases=ALIASES,
            output=duplicate,
            curator="Curator",
            pool_size=3,
        )
        == summary
    )
    assert (output / "packet.json").read_bytes() == (duplicate / "packet.json").read_bytes()
    packet = json.loads((output / "packet.json").read_text())
    text = json.dumps(packet)
    assert all(word not in text for word in ('"score"', '"rank"', '"relevant_passage_ids"'))
    assert all(c["passage"]["published_at"][:10] <= "2026-03-12" for c in packet["candidates"])
    judgments = json.loads((output / "judgments.json").read_text())
    assert all(row["relevant"] is None for row in judgments["candidates"])
    assert judgments["reviewer"] == ""
    assert summary["as_of_months"] == {"2026-03": 1}
    with pytest.raises(FileExistsError):
        prepare_review(
            pairs=pairs, corpus=corpus, aliases=ALIASES, output=output, curator="Curator"
        )


def test_reviewed_pairs_and_receipt_round_trip(review_files, tmp_path):
    corpus, _, output, _ = review_files
    complete_judgments(output)
    target = tmp_path / "export"
    receipt = export(corpus, output, target)
    assert (
        validate_receipt(target / "receipt.json", pairs=target / "pairs.jsonl", corpus=corpus)
        == receipt
    )
    reviewed = EvidenceQuery.model_validate_json((target / "pairs.jsonl").read_text())
    assert len(reviewed.relevant_passage_ids) == receipt.relevant_passages
    assert receipt.judged_candidates == receipt.relevant_passages
    assert receipt.packet_sha256 == sha256(output / "packet.json")
    assert receipt.judgments_sha256 == sha256(output / "judgments.json")
    with pytest.raises(FileExistsError):
        export(corpus, output, target)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda j: j.update(reviewer=" curator "), "differ from the curator"),
        (lambda j: j.update(independent_review=False), "True"),
        (lambda j: j.update(blinded_to_results=False), "True"),
        (lambda j: j.update(reviewed_on=None), "date"),
        (lambda j: j["queries"][0].update(suitable=None), "independent acceptance"),
        (lambda j: j["queries"][0].update(suitable=False), "independent acceptance"),
        (lambda j: j["candidates"][0].update(relevant=None), "incomplete"),
        (lambda j: j["candidates"][0].update(evidence_span="invented evidence"), "verbatim"),
        (lambda j: j["candidates"][0].update(evidence_span="  "), "verbatim"),
        (lambda j: j["candidates"][0].update(relevant=False), "irrelevant candidates"),
        (lambda j: j["candidates"].pop(), "exactly the candidate pool"),
        (lambda j: j["candidates"].append(j["candidates"][0].copy()), "without duplicates"),
        (lambda j: j["queries"].append(j["queries"][0].copy()), "without duplicates"),
    ],
)
def test_export_rejects_incomplete_or_invalid_review_before_writing(
    review_files, tmp_path, change, message
):
    corpus, _, output, _ = review_files
    judgments = complete_judgments(output)
    change(judgments)
    (output / "judgments.json").write_text(json.dumps(judgments))
    with pytest.raises(ValueError, match=message):
        export(corpus, output, tmp_path / "export")
    assert not (tmp_path / "export").exists()


def test_export_requires_positive_for_every_query(review_files, tmp_path):
    corpus, _, output, _ = review_files
    judgments = complete_judgments(output)
    for row in judgments["candidates"]:
        row.update(relevant=False, evidence_span=None)
    (output / "judgments.json").write_text(json.dumps(judgments))
    with pytest.raises(ValueError, match="at least one"):
        export(corpus, output, tmp_path / "export")


@pytest.mark.parametrize("changed", ["packet", "corpus", "pairs"])
def test_stale_reviews_cannot_be_reused(review_files, tmp_path, changed):
    corpus, _, output, _ = review_files
    complete_judgments(output)
    target = tmp_path / "export"
    export(corpus, output, target)
    path = {"packet": output / "packet.json", "corpus": corpus, "pairs": target / "pairs.jsonl"}[
        changed
    ]
    path.write_bytes(path.read_bytes() + b"\n")
    if changed == "packet":
        with pytest.raises(ValueError, match="hash mismatch"):
            export(corpus, output, tmp_path / "another")
    else:
        with pytest.raises(ValueError, match="hashes"):
            validate_receipt(target / "receipt.json", pairs=target / "pairs.jsonl", corpus=corpus)


def test_extra_pool_is_blinded_validated_and_preserves_seed_positives(
    review_files, tmp_path, passages
):
    corpus, pairs, _, _ = review_files
    pool = tmp_path / "pool.jsonl"
    item = {
        "query_id": "q1",
        "query": "oil",
        "as_of": "2026-03-12",
        "passage_ids": [passages[1].passage_id],
    }
    pool.write_text(json.dumps(item) + "\n")
    target = tmp_path / "pooled"
    prepare_review(
        pairs=pairs,
        corpus=corpus,
        aliases=ALIASES,
        output=target,
        curator="Curator",
        pool_size=1,
        candidate_pool=pool,
    )
    packet = json.loads((target / "packet.json").read_text())
    assert {passages[0].passage_id, passages[1].passage_id} <= {
        c["passage"]["passage_id"] for c in packet["candidates"]
    }
    assert sha256(pool) in packet["pool_method"]
    for i, changes in enumerate(
        (
            {"query_id": "unknown"},
            {"as_of": "2026-03-13"},
            {"passage_ids": [passages[-1].passage_id]},
            {"passage_ids": ["absent"]},
        )
    ):
        pool.write_text(json.dumps({**item, **changes}) + "\n")
        with pytest.raises(ValueError):
            prepare_review(
                pairs=pairs,
                corpus=corpus,
                aliases=ALIASES,
                output=tmp_path / f"bad{i}",
                curator="Curator",
                candidate_pool=pool,
            )
        assert not (tmp_path / f"bad{i}").exists()


def test_twenty_unreviewed_pairs_fail_before_any_model_load(
    review_files, tmp_path, monkeypatch, capsys
):
    corpus, pairs, _, _ = review_files
    query = json.loads(pairs.read_text())
    pairs.write_text("".join(json.dumps({**query, "query_id": f"q{i}"}) + "\n" for i in range(20)))

    def forbidden(*args, **kwargs):
        pytest.fail("unreviewed research run must fail before model construction")

    monkeypatch.setattr("retrieval.pilot_runner.build_retriever", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "--pairs",
            str(pairs),
            "--corpus",
            str(corpus),
            "--output",
            str(tmp_path / "pilot.md"),
            "--embedding-revision",
            "test",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pilot_main()
    assert exc.value.code == 2
    assert "--review-receipt" in capsys.readouterr().err
    assert not (tmp_path / "pilot.md").exists()


def test_reviewed_twenty_pair_pilot_records_attestation_and_pool(
    review_files, tmp_path, monkeypatch
):
    corpus, pairs, _, _ = review_files
    query = json.loads(pairs.read_text())
    pairs.write_text("".join(json.dumps({**query, "query_id": f"q{i}"}) + "\n" for i in range(20)))
    output = tmp_path / "twenty"
    prepare_review(
        pairs=pairs, corpus=corpus, aliases=ALIASES, output=output, curator="Curator", pool_size=1
    )
    complete_judgments(output)
    reviewed = tmp_path / "export"
    export(corpus, output, reviewed)

    class StubEmbedder:
        model_id = "offline-review-test-only"

        def __init__(self, **kwargs):
            pass

        def encode(self, texts):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr("retrieval.factory.BGEEmbedder", StubEmbedder)
    report = tmp_path / "pilot.md"
    pool = tmp_path / "candidate-pool.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "--pairs",
            str(reviewed / "pairs.jsonl"),
            "--corpus",
            str(corpus),
            "--aliases",
            str(ALIASES),
            "--output",
            str(report),
            "--embedding-revision",
            "test",
            "--review-receipt",
            str(reviewed / "receipt.json"),
            "--candidate-output",
            str(pool),
        ],
    )
    pilot_main()
    text = report.read_text()
    assert "REVIEWED PILOT" in text and "attested by Reviewer" in text
    assert sha256(reviewed / "receipt.json") in text
    assert sha256(pool) in text
    assert len(pool.read_text().splitlines()) == 20


def test_receipt_metadata_must_match_reviewed_pairs(review_files, tmp_path):
    corpus, _, output, _ = review_files
    complete_judgments(output)
    target = tmp_path / "export"
    export(corpus, output, target)
    receipt_path = target / "receipt.json"
    original = json.loads(receipt_path.read_text())
    for change, message in (
        ({"query_ids": ["other"]}, "query ids"),
        (
            {
                "relevant_passages": original["relevant_passages"] + 1,
                "judged_candidates": original["judged_candidates"] + 1,
            },
            "positive count",
        ),
    ):
        receipt_path.write_text(json.dumps({**original, **change}))
        with pytest.raises(ValueError, match=message):
            validate_receipt(receipt_path, pairs=target / "pairs.jsonl", corpus=corpus)
