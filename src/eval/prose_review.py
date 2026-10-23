"""Human correction gate for the prose baselines' mechanically extracted graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from schema import Graph


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(runs: Path, output: Path):
    items = []
    for path in sorted(runs.glob("*/*.json")):
        payload = json.loads(path.read_text())
        if payload.get("prose_answer") is None:
            continue
        items.append(
            {
                "source_path": str(path.resolve()),
                "source_sha256": digest(path),
                "prose_answer": payload["prose_answer"],
                "corrected_graph": payload["graph"],
                "established_edge_ids": payload["established_edge_ids"],
                "correction_complete": False,
            }
        )
    if not items:
        raise ValueError("no prose baseline artifacts found")
    packet = {
        "reviewer": "",
        "reviewed_on": None,
        "human_correction_attestation": False,
        "instructions": "Correct all omitted/added/mislabelled edges against the actual prose answer. Preserve its hedging, citations and mistakes. Established means cited or unhedged. Do not improve the answer or silently replace its evidence.",
        "items": items,
    }
    with output.open("x") as stream:
        stream.write(json.dumps(packet, indent=2) + "\n")
    return {"baseline_items": len(items), "status": "pending human correction of prose extraction"}


def export(*, runs: Path, corrections: Path, output: Path):
    review = json.loads(corrections.read_text())
    reviewer = review.get("reviewer", "").strip()
    if (
        not reviewer
        or not review.get("human_correction_attestation")
        or not review.get("reviewed_on")
    ):
        raise ValueError("human correction identity/date/attestation required")
    date.fromisoformat(review["reviewed_on"])
    paths = {
        str(path.resolve()): path
        for path in runs.glob("*/*.json")
        if json.loads(path.read_text()).get("prose_answer") is not None
    }
    items = {row["source_path"]: row for row in review["items"]}
    if not paths or len(items) != len(review["items"]) or set(items) != set(paths):
        raise ValueError("corrections must cover exactly all prose baseline artifacts")
    corrected = {}
    for address, item in items.items():
        if not item["correction_complete"] or digest(paths[address]) != item["source_sha256"]:
            raise ValueError("incomplete or stale prose correction")
        original = json.loads(paths[address].read_text())
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
            json.dumps(corrected.get(str(path.resolve()), json.loads(path.read_text())), indent=2)
            + "\n"
        )
    receipt = {
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (
        prepare(args.runs, args.output)
        if args.command == "prepare"
        else export(runs=args.runs, corrections=args.corrections, output=args.output)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
