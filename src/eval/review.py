"""Create blinded edge-support packets; evaluate only complete recorded reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from corpus.bindings import require_run_corpus
from schema import Graph, Passage, Strength

from .metrics import SupportJudgment, aggregate, recall_guard, score_graph
from .references import validate as validate_references
from .stats import predeclared_contrasts


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Judgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    supported: bool | None = None
    evidence_strength: Strength | None = None
    notes: str = ""


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = ""
    reviewed_on: date | None = None
    blinded_to_condition: bool = False
    independent_review: bool = False
    judgments: list[Judgment]


def prepare(*, runs: Path, corpus: Path, output: Path):
    require_run_corpus(runs, corpus)
    passages = {
        p.passage_id: p
        for line in corpus.read_text().splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }
    items, mapping, artifacts = [], {}, {}
    for path in sorted(runs.glob("*/*.json")):
        payload = json.loads(path.read_text())
        if "graph" not in payload:
            continue
        graph = Graph.model_validate(payload["graph"])
        artifacts[str(path.resolve())] = digest(path)
        for edge in graph.edges:
            item_id = hashlib.sha256(f"{digest(path)}/{edge.edge_id}".encode()).hexdigest()[:24]
            passage = passages.get(edge.evidence_passage_id)
            items.append(
                {
                    "item_id": item_id,
                    "question_id": graph.query_id,
                    "as_of": str(graph.as_of),
                    "src_var": edge.src_var,
                    "dst_var": edge.dst_var,
                    "direction": str(edge.direction),
                    "evidence_span": edge.evidence_span,
                    "passage": passage.model_dump(mode="json") if passage else None,
                }
            )
            mapping[item_id] = {"artifact": str(path.resolve()), "edge_id": edge.edge_id}
    if not artifacts:
        raise ValueError("no completed graph artifacts found")
    items.sort(key=lambda row: row["item_id"])
    private_text = json.dumps({"mapping": mapping, "artifacts": artifacts}, indent=2) + "\n"
    packet = {
        "version": 1,
        "corpus_sha256": digest(corpus),
        "private_mapping_sha256": hashlib.sha256(private_text.encode()).hexdigest(),
        "items": items,
        "instructions": "Judge attached support, direction and evidence strength. No attached eligible source means unsupported. Conditions/model labels are hidden. Do not consult run outputs before reviewing.",
    }
    output.mkdir(parents=True, exist_ok=False)
    packet_path = output / "packet.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n")
    (output / "private_mapping.json").write_text(private_text)
    review = Review(
        packet_sha256=digest(packet_path),
        judgments=[Judgment(item_id=row["item_id"]) for row in items],
    )
    (output / "judgments.json").write_text(review.model_dump_json(indent=2) + "\n")
    return {
        "status": "pending independent support review",
        "graphs": len(artifacts),
        "edge_items": len(items),
        "packet_sha256": digest(packet_path),
    }


def evaluate(
    *,
    review_dir: Path,
    reference_dir: Path | None = None,
    corpus: Path = Path("data/processed/articles.jsonl"),
):
    packet_path = review_dir / "packet.json"
    packet = json.loads(packet_path.read_text())
    review = Review.model_validate_json((review_dir / "judgments.json").read_text())
    private = json.loads((review_dir / "private_mapping.json").read_text())
    if review.packet_sha256 != digest(packet_path):
        raise ValueError("support packet hash mismatch")
    if packet["private_mapping_sha256"] != digest(review_dir / "private_mapping.json"):
        raise ValueError("private support mapping hash mismatch")
    if (
        not review.reviewer.strip()
        or review.reviewed_on is None
        or not review.independent_review
        or not review.blinded_to_condition
    ):
        raise ValueError("complete independent blinded review attestation is required")
    judgments = {row.item_id: row for row in review.judgments}
    expected = {row["item_id"] for row in packet["items"]}
    if (
        len(judgments) != len(review.judgments)
        or set(judgments) != expected
        or set(private["mapping"]) != expected
    ):
        raise ValueError("support judgments must cover exactly the packet items")
    if any(row.supported is None for row in judgments.values()):
        raise ValueError("support judgments are incomplete")
    grouped = {path: {} for path in private["artifacts"]}
    for item_id, judgment in judgments.items():
        address = private["mapping"][item_id]
        grouped[address["artifact"]][address["edge_id"]] = SupportJudgment(
            judgment.supported, judgment.evidence_strength
        )
    references, reference_receipt_sha256 = {}, None
    if reference_dir is not None:
        references, reference_receipt_sha256 = validate_references(
            references=reference_dir,
            corpus=corpus,
            expected_corpus_sha256=packet["corpus_sha256"],
        )
    scores = {}
    for address, expected_hash in private["artifacts"].items():
        path = Path(address)
        if digest(path) != expected_hash:
            raise ValueError("run artifact changed after support review was prepared")
        payload = json.loads(path.read_text())
        graph = Graph.model_validate(payload["graph"])
        if payload.get("prose_answer") is not None:
            correction = payload.get("baseline_correction_receipt", {})
            if (
                not correction.get("reviewer")
                or not correction.get("reviewed_on")
                or correction.get("human_correction_attestation") is not True
            ):
                raise ValueError(
                    "prose baseline extraction requires completed human correction before support scoring"
                )
        reference = None
        if reference_dir is not None:
            reference = references.get(graph.query_id)
            if reference is None or (
                reference.as_of,
                reference.anchor.var,
                reference.anchor.direction,
                reference.anchor.event_date,
            ) != (graph.as_of, graph.anchor.var, graph.anchor.direction, graph.anchor.event_date):
                raise ValueError("reference graph query/cutoff/anchor mismatch")
        scores.setdefault(graph.condition, {})[graph.query_id] = score_graph(
            graph,
            established=set(payload["established_edge_ids"]),
            judgments=grouped[address],
            reference=reference,
        )
    return {
        "status": "reviewed development results; directional only",
        "reviewer": review.reviewer,
        "reviewed_on": str(review.reviewed_on),
        "judgments_sha256": digest(review_dir / "judgments.json"),
        "reference_review_receipt_sha256": reference_receipt_sha256,
        "per_query": scores,
        "aggregate": {key: aggregate(list(value.values())) for key, value in scores.items()},
        "contrasts": (
            {
                metric: predeclared_contrasts(scores, metric=metric)
                for metric in ("uer", "strength_inflation")
            }
            if {"B1", "M"} <= scores.keys()
            else None
        ),
        "recall_guard": recall_guard(scores),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--runs", type=Path, required=True)
    prep.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    prep.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--references", type=Path)
    score.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(runs=args.runs, corpus=args.corpus, output=args.output)
    else:
        result = evaluate(review_dir=args.review, reference_dir=args.references, corpus=args.corpus)
        with args.output.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(result if args.command == "prepare" else {"status": result["status"]}, indent=2)
    )


if __name__ == "__main__":
    main()
