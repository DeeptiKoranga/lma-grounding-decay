"""Human correction gate for the prose baselines' mechanically extracted graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from corpus.bindings import recorded_corpus_sha256, require_run_corpus
from schema import Graph, Passage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(runs: Path, output: Path, *, corpus: Path | None = None):
    if corpus is not None:
        require_run_corpus(runs, corpus)
    passages = (
        {
            p.passage_id: p
            for line in corpus.read_text(encoding="utf-8").splitlines()
            if line.strip()
            if (p := Passage.model_validate_json(line))
        }
        if corpus is not None
        else {}
    )
    items = []
    for path in sorted(runs.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("prose_answer") is None:
            continue
        ids = set(re.findall(r"\b[A-Za-z0-9_.:-]+#p\d+\b", payload["prose_answer"]))
        ids.update(
            edge["evidence_passage_id"]
            for edge in [*payload["graph"]["edges"], *payload.get("raw_candidates", [])]
            if edge.get("evidence_passage_id")
        )
        items.append(
            {
                "source_path": str(path.resolve()),
                "source_sha256": digest(path),
                "prose_answer": payload["prose_answer"],
                "corrected_graph": payload["graph"],
                "established_edge_ids": payload["established_edge_ids"],
                "cited_passages": [
                    passages[pid].model_dump(mode="json") for pid in sorted(ids & passages.keys())
                ],
                "unresolved_passage_ids": sorted(ids - passages.keys()),
                "correction_complete": False,
            }
        )
    if not items:
        raise ValueError("no prose baseline artifacts found")
    packet = {
        "reviewer": "",
        "reviewed_on": None,
        "human_correction_attestation": False,
        "corpus_sha256": digest(corpus) if corpus is not None else None,
        "instructions": "Correct all omitted/added/mislabelled edges against the actual prose answer. Preserve its hedging, cited passage identities and substantive mistakes. If prose cites a passage without a quotation, correct the extractor's quotation using that same attached trusted passage. If the prose has no citation, remove citations added by the extractor. Never substitute a new source or improve the answer's claims. Established means cited or unhedged. Unresolved passage IDs are not valid evidence.",
        "items": items,
    }
    with output.open("x") as stream:
        stream.write(json.dumps(packet, indent=2) + "\n")
    return {"baseline_items": len(items), "status": "pending human correction of prose extraction"}


def export(*, runs: Path, corrections: Path, output: Path):
    review = json.loads(corrections.read_text(encoding="utf-8"))
    expected_corpus = recorded_corpus_sha256(runs)
    if expected_corpus is not None and review.get("corpus_sha256") != expected_corpus:
        raise ValueError("correction packet corpus differs from source run provenance")
    reviewer = review.get("reviewer", "").strip()
    if (
        not reviewer
        or review.get("human_correction_attestation") is not True
        or not review.get("reviewed_on")
    ):
        raise ValueError("human correction identity/date/attestation required")
    if date.fromisoformat(review["reviewed_on"]) > date.today():
        raise ValueError("correction review date cannot be in the future")
    paths = {
        str(path.resolve()): path
        for path in runs.glob("*/*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("prose_answer") is not None
    }
    items = {row["source_path"]: row for row in review["items"]}
    if not paths or len(items) != len(review["items"]) or set(items) != set(paths):
        raise ValueError("corrections must cover exactly all prose baseline artifacts")
    corrected = {}
    for address, item in items.items():
        if (
            item["correction_complete"] is not True
            or digest(paths[address]) != item["source_sha256"]
        ):
            raise ValueError("incomplete or stale prose correction")
        original = json.loads(paths[address].read_text(encoding="utf-8"))
        old, new = Graph.model_validate(original["graph"]), Graph.model_validate(
            item["corrected_graph"]
        )
        if (old.query_id, old.as_of, old.anchor, old.condition) != (
            new.query_id,
            new.as_of,
            new.anchor,
            new.condition,
        ):
            raise ValueError("correction cannot change query identity, cutoff, anchor or condition")
        established = set(item["established_edge_ids"])
        if not established <= {edge.edge_id for edge in new.edges}:
            raise ValueError("corrected established ids must exist in corrected graph")
        corrected[address] = {
            **original,
            "graph": new.model_dump(mode="json"),
            "established_edge_ids": sorted(established),
            "baseline_correction_receipt": {
                "reviewer": reviewer,
                "reviewed_on": review["reviewed_on"],
                "human_correction_attestation": True,
                "source_artifact_sha256": item["source_sha256"],
                "corrections_sha256": digest(corrections),
            },
        }
    output.mkdir(parents=True, exist_ok=False)
    for path in sorted(runs.glob("*/*.json")):
        target = output / path.relative_to(runs)
        target.parent.mkdir(exist_ok=True)
        target.write_text(
            json.dumps(
                corrected.get(str(path.resolve()), json.loads(path.read_text(encoding="utf-8"))),
                indent=2,
            )
            + "\n"
        )
    receipt = {
        "corpus_sha256": review.get("corpus_sha256"),
        "reviewer": reviewer,
        "reviewed_on": review["reviewed_on"],
        "items": len(corrected),
        "corrections_sha256": digest(corrections),
        "status": "human-corrected extraction; support judgments still required",
    }
    (output / "prose_correction_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "export"])
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--corrections", type=Path)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (
        prepare(args.runs, args.output, corpus=args.corpus)
        if args.command == "prepare"
        else export(runs=args.runs, corrections=args.corrections, output=args.output)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
