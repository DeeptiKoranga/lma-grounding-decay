"""Generate challenge candidates from gold, without certifying corruptions (B9, #20).

A corruption is applied mechanically, so *that a corruption was applied* is
ground truth: we reversed the relation, we moved the date. Whether the original
edge was right is a different question, and this module never answers it -
every row leaves `human_reviewed` false and `expected_supported` null.

That split matters when the numbers are read (#40):

* **Corruption-detection rate**, over corrupted rows, is sound even on
  un-adjudicated gold. The corruption is known by construction.
* **False-alarm rate**, over the clean controls, inherits whatever is wrong
  with the gold set. A control is only clean if the gold edge was right.

Size
----
The original spec (#20) asked for 100 corruptions plus 25 controls against
gates of 25 eligible seeds and 20 hedged ones. D-18 and D-19 cut the query set
from 30 to 8, so `eval.gold.MAX_EDGES` of 6 over four dev queries caps the gold
set at 24 edges and those gates became unreachable by construction - see
`reports/b9_feasibility_20261028.md`. D-21 rescoped the task: take every
corruption the gold set supports, and record the per-type counts so no rate is
ever quoted without its denominator. The floors below are what remains of the
original gates - small enough to be reachable, large enough that the result is
not noise.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import Passage

from .references import digest, inspect, validate

__all__ = ["CORRUPTIONS", "MIN_INFLATABLE_SEEDS", "MIN_SEEDS", "build"]

#: The five corruption families from the proposal and issue #20.
CORRUPTIONS: tuple[str, ...] = (
    "reversed_relation",
    "inflated_strength",
    "unsupported_intermediate",
    "wrong_date",
    "wrong_target",
)

#: Below this many eligible seeds the exercise is noise rather than a weak
#: result, so it refuses rather than producing a set nobody should quote.
#: Rescoped from 25 by D-21; the original was written against a 30-query design.
MIN_SEEDS = 12

#: Strength inflation needs hedged links to inflate. Rescoped from 20.
MIN_INFLATABLE_SEEDS = 5


def _seeds(graphs, passages):
    out = []
    for graph in graphs.values():
        for edge in graph.edges:
            passage = passages.get(edge.evidence_passage_id)
            if (
                edge.is_asserted
                and edge.strength != "correlational"
                and passage
                and passage.visible_at(graph.as_of)
                and edge.evidence_span in passage.text
            ):
                out.append((graph, edge, passage))
    return out


def _corrupt(kind, graph, edge, passage):
    """Apply one corruption. Returns (edge payload, as_of) or None if this
    seed cannot carry this corruption."""
    data = edge.model_dump(mode="json")
    as_of = str(graph.as_of)

    if kind == "reversed_relation":
        data["src_var"], data["dst_var"] = data["dst_var"], data["src_var"]
        source_move = next(
            (node.direction for node in graph.nodes if node.var == edge.src_var), None
        )
        if source_move is None:
            return None
        data["direction"] = str(source_move)
    elif kind == "inflated_strength":
        if edge.strength != "conditional":
            return None
        data["strength"] = "direct"
    elif kind == "unsupported_intermediate":
        data["src_var"] = "GOLD_IMPORTS" if edge.src_var != "GOLD_IMPORTS" else "EXPORTS"
    elif kind == "wrong_target":
        data["dst_var"] = "GST_COLLECTIONS" if edge.src_var != "GST_COLLECTIONS" else "IIP"
    elif kind == "wrong_date":
        published = passage.published_at.date()
        as_of = str(published.fromordinal(published.toordinal() - 1))
    else:  # pragma: no cover - CORRUPTIONS is closed
        raise ValueError(f"unknown corruption {kind!r}")
    return data, as_of


def build(*, gold: Path, corpus: Path, output: Path, allow_unreviewed: bool = False):
    passages = {
        p.passage_id: p
        for line in corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }

    if allow_unreviewed:
        # The gold graphs exist but nobody has signed for them. The set is still
        # worth building - the corruptions are ground truth either way - but
        # every row says so, and the false-alarm denominator is not trustworthy.
        graphs, _ = inspect(gold, corpus)
        receipt_hash, adjudicated = None, False
    else:
        graphs, receipt_hash = validate(
            references=gold, corpus=corpus, expected_corpus_sha256=digest(corpus)
        )
        adjudicated = True

    seeds = _seeds(graphs, passages)
    if len(seeds) < MIN_SEEDS:
        raise ValueError(
            f"challenge generation needs at least {MIN_SEEDS} eligible causal gold edges, "
            f"found {len(seeds)}"
        )
    inflatable = [seed for seed in seeds if seed[1].strength == "conditional"]
    if len(inflatable) < MIN_INFLATABLE_SEEDS:
        raise ValueError(
            f"strength-inflation corruptions need at least {MIN_INFLATABLE_SEEDS} hedged "
            f"gold links, found {len(inflatable)}"
        )

    def row(item_id, graph, data, passage, as_of, kind):
        return {
            "item_id": item_id,
            "query_id": graph.query_id,
            "as_of": as_of,
            "edge": data,
            "passage_id": passage.passage_id,
            "proposed_corruption": kind,
            "human_reviewed": False,
            "expected_supported": None,
            "gold_adjudicated": adjudicated,
            "reference_review_receipt_sha256": receipt_hash,
        }

    rows = [
        row(
            f"control-{i:02d}", graph, edge.model_dump(mode="json"), passage, str(graph.as_of), None
        )
        for i, (graph, edge, passage) in enumerate(seeds)
    ]
    counts = {"control": len(rows)}
    for kind in CORRUPTIONS:
        made = 0
        for graph, edge, passage in seeds:
            corrupted = _corrupt(kind, graph, edge, passage)
            if corrupted is None:
                continue
            data, as_of = corrupted
            rows.append(row(f"{kind}-{made:02d}", graph, data, passage, as_of, kind))
            made += 1
        counts[kind] = made

    with output.open("x") as stream:
        stream.write("".join(json.dumps(r) + "\n" for r in rows))

    manifest = {
        "items": len(rows),
        "counts_by_kind": counts,
        "gold_adjudicated": adjudicated,
        "reference_review_receipt_sha256": receipt_hash,
        "corpus_sha256": digest(corpus),
        "status": (
            "challenge candidates; independent review is required before accepting "
            "corruption labels"
        ),
        "reading": (
            "Corruption-detection rate is sound on un-adjudicated gold because the "
            "corruption is applied mechanically. The false-alarm rate over controls is "
            "only as good as the gold edges. Quote every rate with its denominator from "
            "counts_by_kind; the per-type counts are uneven by construction (D-21)."
        ),
    }
    output.with_name(output.stem + "_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-unreviewed",
        action="store_true",
        help="build from gold that has no signed review receipt; every row is marked",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                gold=args.gold,
                corpus=args.corpus,
                output=args.output,
                allow_unreviewed=args.allow_unreviewed,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
