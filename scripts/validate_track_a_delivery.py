"""Check final development-delivery bindings without creating research acceptance."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from corpus import Document
from retrieval.review import Judgments, read_queries
from schema import Passage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(output):
    snapshot = Path("data/processed")
    build = json.loads(Path("reports/corpus_v7_build_20261026.json").read_text())
    assert digest(snapshot / "articles.jsonl") == build["candidate_corpus_sha256"]
    archive = snapshot / "corpus-v7-narrative-development.zip"
    assert digest(archive) == build["candidate_archive_sha256"]
    with ZipFile(archive) as zipped:
        for name in ["articles.jsonl", "documents.jsonl", "duplicates.jsonl"]:
            assert zipped.read(name) == (snapshot / name).read_bytes()
    documents = [
        Document.model_validate_json(s)
        for s in (snapshot / "documents.jsonl").read_text().splitlines()
    ]
    parents = {d.doc_id: d for d in documents}
    passages = [
        Passage.model_validate_json(s)
        for s in (snapshot / "articles.jsonl").read_text().splitlines()
    ]
    assert len(parents) == len(documents) == 1156
    assert len(passages) == 16472
    assert all(parents[p.doc_id].text[p.char_start : p.char_end] == p.text for p in passages)
    index = json.loads(Path("reports/corpus_v7_index_20261026.json").read_text())
    assert index["corpus_sha256"] == build["candidate_corpus_sha256"]
    assert digest(Path(index["index"])) == index["index_sha256"]
    assert index["all_passages_match_snapshot"]

    delivery = Path("data/interim/track_a_review_delivery_v7_20261026")
    packet_path = delivery / "02_relevance/packet.json"
    packet = json.loads(packet_path.read_text())
    review = json.loads(Path("reports/retriever_v7_full_review_20261026.json").read_text())
    assert review["packet_sha256"] == digest(packet_path)
    assert review["corpus_sha256"] == packet["corpus_sha256"] == build["candidate_corpus_sha256"]
    assert review["independent_human_review"] is False and review["research_acceptance"] is False
    candidates = {
        (c["query_id"], c["passage"]["passage_id"]): c["passage"] for c in packet["candidates"]
    }
    assert len(candidates) == len(packet["candidates"])
    rows = {(r["query_id"], r["passage_id"]): r for r in review["items"]}
    assert len(rows) == len(review["items"]) and rows.keys() == candidates.keys()
    cutoffs = {q["query_id"]: q["as_of"] for q in packet["queries"]}
    positives = {qid: set() for qid in cutoffs}
    for key, row in rows.items():
        passage = candidates[key]
        assert row["text_sha256"] == hashlib.sha256(passage["text"].encode()).hexdigest()
        assert passage["published_at"][:10] <= cutoffs[key[0]]
        assert row["decision"] in {"relevant", "irrelevant"}
        if row["decision"] == "relevant":
            assert (
                0 <= row["evidence_char_start"] < row["evidence_char_end"] <= len(passage["text"])
            )
            positives[key[0]].add(key[1])
        else:
            assert row["evidence_char_start"] is None and row["evidence_char_end"] is None
    pairs = read_queries(Path("reports/retriever_v7_pairs_20261026.jsonl"))
    assert len(pairs) == len(cutoffs) == 20
    assert all(set(q.relevant_passage_ids) == positives[q.query_id] for q in pairs)
    counts = dict(Counter(row["decision"] for row in rows.values()))
    assert counts == review["counts"]

    manifest = json.loads(Path("reports/track_a_reviewer_delivery_v7_20261026.json").read_text())
    for row in manifest["files"]:
        assert digest(delivery / row["path"]) == row["sha256"]
    human = Judgments.model_validate_json((delivery / "02_relevance/judgments.json").read_text())
    assert human.reviewer == "" and human.reviewed_on is None
    assert not human.independent_review and not human.blinded_to_results
    assert all(q.suitable is None for q in human.queries)
    assert all(c.relevant is None and c.evidence_span is None for c in human.candidates)
    previous = json.loads(Path("reports/track_a_reviewer_delivery.json").read_text())
    for row in previous["files"]:
        assert digest(Path(previous["directory"]) / row["path"]) == row["sha256"]
    series = json.loads(Path("reports/track_a_series_scope_20261026.json").read_text())
    for row in series["series"]:
        assert digest(Path("data/series") / (row["series_id"] + ".csv")) == row["canonical_sha256"]
        assert (
            digest(Path("data/series/retrospective_20261025") / (row["series_id"] + ".csv"))
            == row["retrospective_sha256"]
        )
    selection = json.loads(Path("reports/track_a_retrieval_selection_20261026.json").read_text())
    assert selection["corpus_sha256"] == build["candidate_corpus_sha256"]
    assert selection["pairs_sha256"] == digest(Path("reports/retriever_v7_pairs_20261026.jsonl"))
    result = {
        "checked_on": "2026-10-26",
        "status": "development-delivery integrity passed; research acceptance pending",
        "corpus_sha256": build["candidate_corpus_sha256"],
        "archive_sha256": build["candidate_archive_sha256"],
        "documents": len(documents),
        "passages": len(passages),
        "pooled_judgments": len(rows),
        "judgment_counts": counts,
        "all_offsets_exact": True,
        "all_positive_spans_valid": True,
        "all_review_candidates_date_eligible": True,
        "all_index_bytes_verified": True,
        "new_review_workspace_files_verified": len(manifest["files"]),
        "old_review_workspace_files_unchanged": len(previous["files"]),
        "human_judgments_and_attestations_blank": True,
        "canonical_observations": series["canonical_total"],
        "retrospective_observations": series["retrospective_total"],
        "series_bytes_unchanged": True,
        "research_acceptance": False,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    validate(parser.parse_args().output)
