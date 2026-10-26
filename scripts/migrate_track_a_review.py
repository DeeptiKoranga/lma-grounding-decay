"""Migrate development judgments by source identity and unchanged evidence text.

Six explicitly rechecked CPI headline/table-prefix records map to the complete
narrative paragraphs containing the same measures. No human receipt is created.
"""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from corpus.parser import _body_key

CPI_RECHECKED = {
    "mospi-06aa3b9c37ec2bad5137#p7": "mospi-06aa3b9c37ec2bad5137#p0",
    "mospi-06aa3b9c37ec2bad5137#p8": "mospi-06aa3b9c37ec2bad5137#p1",
    "mospi-06aa3b9c37ec2bad5137#p24": "mospi-06aa3b9c37ec2bad5137#p1",
    "mospi-5cc04c551825955916a3#p6": "mospi-5cc04c551825955916a3#p0",
    "mospi-5cc04c551825955916a3#p7": "mospi-5cc04c551825955916a3#p1",
    "mospi-5cc04c551825955916a3#p23": "mospi-5cc04c551825955916a3#p1",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(text):
    return _body_key(re.sub(r"^(?:A\. National Level Indices\s*)?[•]\s*", "", text))


def migrate(corpus, output, report):
    if output.exists() or report.exists():
        raise ValueError("preserve existing review exports")
    review_path = Path("reports/track_a_source_review_20261025.json")
    packet_path = Path("data/interim/retrieval_review_temporal_v4/packet.json")
    review, packet = json.loads(review_path.read_text()), json.loads(packet_path.read_text())
    assert digest(packet_path) == review["relevance"]["packet_sha256"]
    old = {
        (row["query_id"], row["passage"]["passage_id"]): row["passage"]
        for row in packet["candidates"]
    }
    new = list(map(json.loads, corpus.read_text().splitlines()))
    by_id = {p["passage_id"]: p for p in new}
    by_doc = defaultdict(list)
    for passage in new:
        by_doc[passage["doc_id"]].append(passage)
    resolved = json.loads(Path("reports/relevance_adjudication_20261026.json").read_text())
    adjudicated = {(r["query_id"], r["passage_id"]): r["decision"] for r in resolved["items"]}
    records, pairs, retained_decisions = [], [], []
    for query in review["relevance"]["queries"]:
        q = query["query"]
        positives = set()
        for row in query["items"]:
            source = old[q["query_id"], row["passage_id"]]
            assert hashlib.sha256(source["text"].encode()).hexdigest() == row["text_sha256"]
            decision = adjudicated.get((q["query_id"], row["passage_id"]), row["decision"])
            matches = [p for p in by_doc[source["doc_id"]] if key(source["text"]) == key(p["text"])]
            method = "same full text; whitespace/format/quote and leading bullet normalization"
            if decision == "relevant" and not matches:
                matches = [
                    p for p in by_doc[source["doc_id"]] if key(source["text"]) in key(p["text"])
                ]
                method = "complete positive evidence retained inside a longer paragraph"
            if decision == "relevant" and not matches and row["passage_id"] in CPI_RECHECKED:
                matches = [by_id[CPI_RECHECKED[row["passage_id"]]]]
                method = "explicit CPI source recheck: same month/measure in complete narrative; table prefix or duplicate headline omitted"
            if decision == "relevant" and len(matches) != 1:
                raise ValueError(
                    f"positive needs source recheck: {q['query_id']} {row['passage_id']}"
                )
            if decision == "relevant":
                positives.add(matches[0]["passage_id"])
            for target in matches:
                assert target["published_at"][:10] <= q["as_of"]
                retained_decisions.append(
                    {
                        "query_id": q["query_id"],
                        "passage_id": target["passage_id"],
                        "text_sha256": hashlib.sha256(target["text"].encode()).hexdigest(),
                        "decision": decision,
                        "evidence_char_start": 0 if decision == "relevant" else None,
                        "evidence_char_end": (
                            len(target["text"]) if decision == "relevant" else None
                        ),
                        "source_passage_id": row["passage_id"],
                        "method": method,
                    }
                )
            records.append(
                {
                    "query_id": q["query_id"],
                    "old_passage_id": row["passage_id"],
                    "decision": decision,
                    "new_passage_ids": [p["passage_id"] for p in matches],
                    "method": (
                        method
                        if matches
                        else "not transferred: changed, removed or split text requires a new judgment"
                    ),
                }
            )
        assert positives
        pairs.append({**q, "relevant_passage_ids": sorted(positives)})
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in pairs)
    )
    result = {
        "reviewer": "Codex",
        "reviewed_on": "2026-10-26",
        "independent_human_review": False,
        "blinded_to_previous_results": False,
        "research_acceptance": False,
        "original_review_sha256": digest(review_path),
        "original_packet_sha256": digest(packet_path),
        "corpus_sha256": digest(corpus),
        "pairs_sha256": digest(output),
        "queries": len(pairs),
        "positive_pairs": sum(len(q["relevant_passage_ids"]) for q in pairs),
        "old_positive_items_accounted_for": sum(r["decision"] == "relevant" for r in records),
        "migration_counts": dict(Counter(r["method"] for r in records)),
        "scope": "Transferred judgments cover unchanged/rechecked evidence only. New or materially changed pooled candidates need separate review; no complete new-pool or independent acceptance is asserted.",
        "records": records,
        "transferred_judgments": retained_decisions,
    }
    assert result["old_positive_items_accounted_for"] == 182 and result["queries"] == 20
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"records", "transferred_judgments"}},
            indent=2,
        )
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--pairs", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    migrate(a.corpus, a.pairs, a.report)


if __name__ == "__main__":
    main()
