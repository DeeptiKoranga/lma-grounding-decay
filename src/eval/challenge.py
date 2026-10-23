"""Generate challenge candidates from reviewed gold, without certifying corruptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import Passage

from .references import digest, validate


def build(*, gold: Path, corpus: Path, output: Path):
    passages = {
        p.passage_id: p
        for line in corpus.read_text().splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }
    graphs, receipt_hash = validate(
        references=gold, corpus=corpus, expected_corpus_sha256=digest(corpus)
    )
    seeds = []
    for graph in graphs.values():
        for edge in graph.edges:
            p = passages.get(edge.evidence_passage_id)
            if (
                edge.is_asserted
                and edge.strength != "correlational"
                and p
                and p.visible_at(graph.as_of)
                and edge.evidence_span in p.text
            ):
                seeds.append((graph, edge, p))
    if len(seeds) < 25:
        raise ValueError(
            "challenge generation requires at least 25 eligible reviewed causal gold edges"
        )
    inflatable = [seed for seed in seeds if seed[1].strength == "conditional"]
    if len(inflatable) < 20:
        raise ValueError(
            "twenty distinct hedged gold links are required for strength-inflation corruptions"
        )
    rows = []
    for i, (graph, edge, passage) in enumerate(seeds[:25]):
        rows.append(
            {
                "item_id": f"control-{i:02d}",
                "query_id": graph.query_id,
                "as_of": str(graph.as_of),
                "edge": edge.model_dump(mode="json"),
                "passage_id": passage.passage_id,
                "proposed_corruption": None,
                "human_reviewed": False,
                "expected_supported": None,
                "reference_review_receipt_sha256": receipt_hash,
            }
        )
    for kind in (
        "reversed_relation",
        "inflated_strength",
        "unsupported_intermediate",
        "wrong_date",
        "wrong_target",
    ):
        pool = inflatable if kind == "inflated_strength" else seeds
        for i, (graph, edge, passage) in enumerate(pool[:20]):
            data = edge.model_dump(mode="json")
            as_of = str(graph.as_of)
            if kind == "reversed_relation":
                data["src_var"], data["dst_var"] = data["dst_var"], data["src_var"]
                data["direction"] = str(
                    next(node.direction for node in graph.nodes if node.var == edge.src_var)
                )
            elif kind == "inflated_strength":
                data["strength"] = "direct"
            elif kind == "unsupported_intermediate":
                data["src_var"] = "GOLD_IMPORTS" if edge.src_var != "GOLD_IMPORTS" else "EXPORTS"
            elif kind == "wrong_target":
                data["dst_var"] = "GST_COLLECTIONS" if edge.src_var != "GST_COLLECTIONS" else "IIP"
            else:
                as_of = str(
                    passage.published_at.date().fromordinal(
                        passage.published_at.date().toordinal() - 1
                    )
                )
            rows.append(
                {
                    "item_id": f"{kind}-{i:02d}",
                    "query_id": graph.query_id,
                    "as_of": as_of,
                    "edge": data,
                    "passage_id": passage.passage_id,
                    "proposed_corruption": kind,
                    "human_reviewed": False,
                    "expected_supported": None,
                    "reference_review_receipt_sha256": receipt_hash,
                }
            )
    with output.open("x") as stream:
        stream.write("".join(json.dumps(row) + "\n" for row in rows))
    return {
        "items": len(rows),
        "status": "challenge candidates; independent review is required before accepting corruption labels",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(gold=args.gold, corpus=args.corpus, output=args.output), indent=2))


if __name__ == "__main__":
    main()
