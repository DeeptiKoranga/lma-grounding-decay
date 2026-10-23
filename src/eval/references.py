"""Hash-bound human review receipts for source-backed reference graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from schema import Graph, Passage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_sha256: dict[str, str]
    reviewer: str = ""
    reviewed_on: date | None = None
    independent_review: bool = False
    all_relations_and_strengths_reviewed: bool = False


def inspect(references: Path, corpus: Path):
    passages = {
        p.passage_id: p
        for line in corpus.read_text().splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }
    graphs, hashes = {}, {}
    for path in sorted(references.glob("*.json")):
        if path.name == "review_receipt.json":
            continue
        graph = Graph.model_validate_json(path.read_text())
        if path.stem != graph.query_id or graph.query_id in graphs or not graph.edges:
            raise ValueError("reference files must contain unique, nonempty query graphs")
        for edge in graph.edges:
            passage = passages.get(edge.evidence_passage_id)
            if (
                not edge.is_asserted
                or passage is None
                or passage.doc_id != edge.evidence_doc_id
                or passage.published_at != edge.evidence_published_at
                or not passage.visible_at(graph.as_of)
                or edge.evidence_span not in passage.text
            ):
                raise ValueError("reference edges require exact eligible trusted source citations")
        graphs[graph.query_id] = graph
        hashes[path.name] = digest(path)
    if not graphs:
        raise ValueError("no source-backed reference graphs found")
    return graphs, hashes


def prepare(*, references: Path, corpus: Path):
    graphs, hashes = inspect(references, corpus)
    review = ReferenceReview(corpus_sha256=digest(corpus), reference_sha256=hashes)
    with (references / "review_receipt.json").open("x") as stream:
        stream.write(review.model_dump_json(indent=2) + "\n")
    return {"graphs": len(graphs), "status": "pending independent reference-graph review"}


def validate(*, references: Path, corpus: Path, expected_corpus_sha256: str):
    review = ReferenceReview.model_validate_json((references / "review_receipt.json").read_text())
    if (
        not review.reviewer.strip()
        or review.reviewed_on is None
        or not review.independent_review
        or not review.all_relations_and_strengths_reviewed
    ):
        raise ValueError("complete independent reference-review attestation is required")
    if review.corpus_sha256 != digest(corpus) or review.corpus_sha256 != expected_corpus_sha256:
        raise ValueError("reference/support corpus hash mismatch")
    graphs, hashes = inspect(references, corpus)
    if hashes != review.reference_sha256:
        raise ValueError("reference graphs changed after their review receipt was prepared")
    return graphs, digest(references / "review_receipt.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    args = parser.parse_args()
    print(json.dumps(prepare(references=args.references, corpus=args.corpus), indent=2))


if __name__ == "__main__":
    main()
