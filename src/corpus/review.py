"""Prepare and validate independent review of a fixed corpus extraction sample.

A receipt accepts only the sampled documents. It does not certify source balance,
exhaustive extraction quality, redistribution rights or downstream relevance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .documents import Document

SCOPE = "Independent review of the specified extraction sample; not exhaustive corpus or redistribution acceptance."


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_id: str
    text_sha256: str
    extraction_accepted: bool | None = None
    publication_version_accepted: bool | None = None
    source_terms_reviewed: bool | None = None
    notes: str = ""


class Judgments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    packet_sha256: str
    snapshot_sha256: str
    reviewer: str = ""
    reviewed_on: date | None = None
    independent_review: bool = False
    accepted: bool = False
    items: list[Item]


def documents(snapshot: Path) -> dict[str, Document]:
    rows = [
        Document.model_validate_json(line)
        for line in (snapshot / "documents.jsonl").read_text().splitlines()
        if line.strip()
    ]
    result = {doc.doc_id: doc for doc in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate corpus document identity")
    return result


def prepare(*, snapshot: Path, sample: Path, curator: str, output: Path) -> dict:
    if not curator.strip():
        raise ValueError("curator identity required")
    seed = json.loads(sample.read_text())
    corpus_hash = digest(snapshot / "articles.jsonl")
    if seed["snapshot_sha256"] != corpus_hash:
        raise ValueError("extraction sample belongs to a different corpus snapshot")
    parents = documents(snapshot)
    ids = [row["doc_id"] for row in seed["items"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("nonempty unique sample required")
    items = []
    for row in seed["items"]:
        doc = parents[row["doc_id"]]
        text_hash = hashlib.sha256(doc.text.encode()).hexdigest()
        if row["text_sha256"] != text_hash:
            raise ValueError("sample text hash differs from corpus document")
        if row["source"] != doc.source or row["url"] != doc.url:
            raise ValueError("sample source identity differs from corpus")
        items.append({"document": doc.model_dump(mode="json"), "text_sha256": text_hash})
    packet = {
        "version": 1,
        "kind": "corpus_extraction",
        "curator": curator.strip(),
        "corpus_sha256": corpus_hash,
        "documents_sha256": digest(snapshot / "documents.jsonl"),
        "sample_sha256": digest(sample),
        "scope": SCOPE,
        "items": items,
    }
    packet_text = dump(packet)
    blank = Judgments(
        packet_sha256=hashlib.sha256(packet_text.encode()).hexdigest(),
        snapshot_sha256=corpus_hash,
        items=[
            Item(doc_id=row["document"]["doc_id"], text_sha256=row["text_sha256"]) for row in items
        ],
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "packet.json").write_bytes(packet_text.encode("utf-8"))
    (output / "judgments.json").write_text(dump(blank.model_dump(mode="json")))
    return {
        "status": "pending independent sample review",
        "items": len(items),
        "corpus_sha256": corpus_hash,
        "packet_sha256": blank.packet_sha256,
    }


def export(*, snapshot: Path, packet_path: Path, judgments_path: Path, output: Path) -> dict:
    packet = json.loads(packet_path.read_text())
    review = Judgments.model_validate_json(judgments_path.read_text())
    if packet.get("version") != 1 or packet.get("kind") != "corpus_extraction":
        raise ValueError("unsupported corpus review packet")
    if review.packet_sha256 != digest(packet_path):
        raise ValueError("corpus packet hash mismatch")
    if (
        packet["corpus_sha256"] != digest(snapshot / "articles.jsonl")
        or review.snapshot_sha256 != packet["corpus_sha256"]
    ):
        raise ValueError("corpus snapshot hash mismatch")
    if packet["documents_sha256"] != digest(snapshot / "documents.jsonl"):
        raise ValueError("corpus parent document hash mismatch")
    if packet.get("scope") != SCOPE:
        raise ValueError("corpus review scope changed")

    def identity(value):
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    if not identity(review.reviewer) or identity(review.reviewer) == identity(packet["curator"]):
        raise ValueError("independent reviewer must be named and differ from curator")
    if (
        not review.independent_review
        or not review.accepted
        or review.reviewed_on is None
        or review.reviewed_on > date.today()
    ):
        raise ValueError(
            "reviewer's own completed acceptance/date/independence attestation required"
        )
    expected = {row["document"]["doc_id"]: row for row in packet["items"]}
    observed = {row.doc_id: row for row in review.items}
    if (
        not expected
        or len(expected) != len(packet["items"])
        or len(observed) != len(review.items)
        or expected.keys() != observed.keys()
    ):
        raise ValueError("review must cover exactly the packet sample, without duplicates")
    parents = documents(snapshot)
    for doc_id, source in expected.items():
        doc = parents[doc_id]
        if (
            source["document"] != doc.model_dump(mode="json")
            or source["text_sha256"] != hashlib.sha256(doc.text.encode()).hexdigest()
        ):
            raise ValueError("packet source differs from corpus parent")
        row = observed[doc_id]
        if row.text_sha256 != source["text_sha256"]:
            raise ValueError("judgment text hash mismatch")
        if not all(
            value is True
            for value in (
                row.extraction_accepted,
                row.publication_version_accepted,
                row.source_terms_reviewed,
            )
        ):
            raise ValueError(
                "every sampled extraction/version/terms check must be complete and accepted"
            )
    receipt = {
        "version": 1,
        "scope": SCOPE,
        "curator": packet["curator"],
        "reviewer": review.reviewer.strip(),
        "reviewed_on": review.reviewed_on.isoformat(),
        "independent_review": True,
        "accepted": True,
        "items": len(expected),
        "corpus_sha256": packet["corpus_sha256"],
        "documents_sha256": packet["documents_sha256"],
        "packet_sha256": digest(packet_path),
        "judgments_sha256": digest(judgments_path),
        "source_terms_note": "Reviewed terms do not grant redistribution permission.",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "receipt.json").write_text(dump(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--sample", type=Path, required=True)
    prepare_parser.add_argument("--curator", required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--packet", type=Path, required=True)
    export_parser.add_argument("--judgments", type=Path, required=True)
    for command in (prepare_parser, export_parser):
        command.add_argument("--snapshot", type=Path, default=Path("data/processed"))
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(
                snapshot=args.snapshot, sample=args.sample, curator=args.curator, output=args.output
            )
        else:
            result = export(
                snapshot=args.snapshot,
                packet_path=args.packet,
                judgments_path=args.judgments,
                output=args.output,
            )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(dump(result), end="")


if __name__ == "__main__":
    main()
