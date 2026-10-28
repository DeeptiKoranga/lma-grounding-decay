"""Validate the recorded Codex review against its unchanged source packets.

This checks identity, coverage, dates and evidence offsets, not the correctness
or independence of judgments. It cannot create a human acceptance receipt.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(report_path, delivery, snapshot):
    review = json.loads(report_path.read_text())
    assert review["reviewer"] == "Codex"
    assert review["independent_human_review"] is False
    assert review["blinded_to_previous_results"] is False
    assert review["research_acceptance"] is False
    assert review["human_receipt_created"] is False
    assert digest(snapshot / "articles.jsonl") == review["corpus_sha256"]
    assert digest(snapshot / "documents.jsonl") == review["corpus"]["documents_sha256"]

    cpath, rpath = delivery / "01_corpus/packet.json", delivery / "02_relevance/packet.json"
    assert digest(cpath) == review["corpus"]["packet_sha256"]
    assert digest(rpath) == review["relevance"]["packet_sha256"]
    corpus_packet, retrieval_packet = json.loads(cpath.read_text()), json.loads(rpath.read_text())
    assert (
        corpus_packet["corpus_sha256"]
        == retrieval_packet["corpus_sha256"]
        == review["corpus_sha256"]
    )
    originals = json.loads((delivery / "01_corpus/source_records.json").read_text())
    by_document = {row["doc_id"]: row for row in originals}
    assert len(by_document) == len(originals)
    for row, item in zip(review["corpus"]["items"], corpus_packet["items"], strict=True):
        doc = item["document"]
        assert row["doc_id"] == doc["doc_id"]
        assert row["published_at"] == doc["published_at"]
        assert row["text_sha256"] == hashlib.sha256(doc["text"].encode()).hexdigest()
        original = by_document[doc["doc_id"]]
        assert original["raw_sha256"] == row["raw_sha256"]
        assert digest(delivery / "01_corpus" / original["path"]) == row["raw_sha256"]
        assert row["source_terms_cleared"] is False
    assert len(review["corpus"]["items"]) == review["corpus"]["items_reviewed"] == 73
    assert (
        dict(Counter(row["disposition"] for row in review["corpus"]["items"]))
        == review["corpus"]["counts"]
    )

    candidates = {}
    for item in retrieval_packet["candidates"]:
        key = (item["query_id"], item["passage"]["passage_id"])
        assert key not in candidates
        candidates[key] = item["passage"]
    seen, counts, queries = set(), Counter(), set()
    for recorded, query in zip(
        review["relevance"]["queries"], retrieval_packet["queries"], strict=True
    ):
        assert recorded["query"] == query
        qid = query["query_id"]
        assert qid not in queries
        queries.add(qid)
        per_query = Counter()
        expected = [key for key in candidates if key[0] == qid]
        assert len(expected) == len(recorded["items"])
        for index, row in enumerate(recorded["items"]):
            key = (qid, row["passage_id"])
            assert row["item_index"] == index and key == expected[index] and key not in seen
            seen.add(key)
            passage = candidates[key]
            assert row["text_sha256"] == hashlib.sha256(passage["text"].encode()).hexdigest()
            assert datetime.fromisoformat(passage["published_at"]).date() <= date.fromisoformat(
                query["as_of"]
            )
            label = row["decision"]
            assert label in {"relevant", "irrelevant", "uncertain"}
            start, end = row["evidence_char_start"], row["evidence_char_end"]
            if label == "relevant":
                assert isinstance(start, int) and isinstance(end, int)
                assert 0 <= start < end <= len(passage["text"])
            else:
                assert start is None and end is None
            if label == "uncertain":
                assert row["note"].strip()
            per_query[label] += 1
        assert per_query["relevant"] > 0 and dict(per_query) == recorded["counts"]
        counts.update(per_query)
    assert seen == set(candidates) and len(queries) == 20
    assert len(seen) == review["relevance"]["passages_reviewed"] == 2062
    assert dict(counts) == review["relevance"]["counts"]
    assert review["relevance"]["uncertain_is_negative"] is False
    seeds = json.loads(Path("reports/retriever_seed_audit_20261025.json").read_text())
    decisions = {
        (query["query"]["query_id"], row["passage_id"]): row["decision"]
        for query in review["relevance"]["queries"]
        for row in query["items"]
    }
    assert len(seeds["records"]) == 43
    assert all(
        decisions[row["query_id"], row["passage_id"]] == row["decision"] for row in seeds["records"]
    )

    candidate = Path(review["repairs"]["candidate"])
    assert digest(candidate / "articles.jsonl") == review["repairs"]["candidate_corpus_sha256"]
    archive = candidate / "corpus-v4-source-review-candidate.zip"
    assert digest(archive) == review["repairs"]["candidate_archive_sha256"]

    manifest = json.loads(Path("reports/track_a_reviewer_delivery.json").read_text())
    for row in manifest["files"]:
        assert digest(delivery / row["path"]) == row["sha256"]
    return {
        "review_sha256": digest(report_path),
        "corpus_samples_verified": 73,
        "queries_verified": len(queries),
        "pooled_judgments_verified": len(seen),
        "counts": dict(counts),
        "all_positive_evidence_offsets_valid": True,
        "all_candidates_date_eligible": True,
        "all_43_seed_decisions_agree_with_prior_audit": True,
        "repair_candidate_hashes_verified": True,
        "review_delivery_files_unchanged": len(manifest["files"]),
        "human_records_changed": False,
        "active_corpus_unchanged": True,
        "research_acceptance": False,
        "source_files_sha256": {
            name: digest(Path(name))
            for name in (
                "src/corpus/parser.py",
                "src/corpus/quality.py",
                "scripts/apply_source_review.py",
                "scripts/validate_source_review.py",
                "tests/unit/test_corpus_pipeline.py",
                "tests/unit/test_corpus_quality.py",
            )
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review", type=Path, default=Path("reports/track_a_source_review_20261025.json")
    )
    parser.add_argument(
        "--delivery", type=Path, default=Path("data/interim/track_a_review_delivery_20261023")
    )
    parser.add_argument("--snapshot", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.review, args.delivery, args.snapshot)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
