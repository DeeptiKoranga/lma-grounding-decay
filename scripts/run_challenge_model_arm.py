"""The challenge set's model arm: what the verifier catches that rules cannot.

    PYTHONPATH=src python scripts/run_challenge_model_arm.py \\
        --revision 545dc4251c05440727734bcd94334791f6ab0192 \\
        --output runs/challenge-model-arm --resume

`scripts/run_challenge.py` runs the rule layer alone and catches 69 of 69
citation corruptions with no false alarms and **none of the 38 semantic ones**.
That is structural, not a shortfall: reversing an edge leaves the same two
variables in the same passage with the same verbatim span, so every rule still
passes, and no rule reads the strength field.

Those 38 are what the LLM verifier exists for, and this is the arm that
measures it. It is the proposal's isolating comparison for the Reasoning
capability (M against A-NoVerify) on the one dataset built to test it.

**What counts as a detection depends on the corruption**, and conflating them
would flatter the result:

* `reversed_relation` - the claim now runs the wrong way. A detection is the
  verifier declining to call it source-asserted: `contradicted` is the ideal
  answer, `unsupported` also counts, because either way the edge does not enter
  a graph as sourced. `Verifier.verify` already downgrades a `supported`
  verdict whose direction disagrees with the claim, so this is read off
  provenance.
* `inflated_strength` - the claim is genuine but overstated, `conditional`
  presented as `direct`. Here the verifier will and should return
  source-asserted, so provenance says nothing. The detection is the **strength
  it returns**: weaker than claimed means it refused the inflation. Scoring
  this on provenance would record zero detections for a verifier doing exactly
  the right thing.
* the three citation corruptions - the rules reject these before the model is
  reached, which is the pipeline working as designed. They are reported so the
  arm's totals match the rules arm's, not because the model is being tested.
* `control` - a clean edge. A flag here is a **false alarm**. Strength
  disagreement on a control is reported separately rather than as a false
  alarm: calling a `direct` edge `conditional` is a different error from
  rejecting a sound citation, and the proposal's false-alarm rate is about the
  second.

Every item is logged in full. Resumable, because 130 model calls is not a
single sitting on a laptop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path

from agent.logging import RunLogger
from conditions.provenance import model_identity, runtime_identity, write_json
from llm.generate import MLXGenerator
from schema import Edge, Passage, Provenance, Strength
from schema.enums import strength_rank
from verify import load_aliases
from verify.llm_verifier import Verifier

REPO = Path(__file__).resolve().parent.parent
ITEMS = REPO / "data/eval/challenge.jsonl"
CORPUS = REPO / "data/processed/articles.jsonl"
REPORT = REPO / "reports/challenge_model_arm.md"

#: Corruptions the rule layer provably cannot see. These are the arm's point.
SEMANTIC = ("reversed_relation", "inflated_strength")


def flagged(kind: str, claimed: Edge, result) -> tuple[bool, str]:
    """Did the verifier catch this item? Returns (flagged, why).

    `kind` is the corruption family, or "control" for a clean edge.
    """
    sourced = result.provenance == Provenance.SOURCE_ASSERTED
    if kind == "inflated_strength":
        # Provenance is the wrong instrument here: the underlying edge is real,
        # so a correct verifier returns source-asserted and disagrees on
        # strength. Reading provenance would score that as a miss.
        if result.strength is None:
            return (False, "no weaker strength returned")
        weaker = strength_rank(Strength(result.strength)) > strength_rank(claimed.strength)
        return (weaker, f"returned {result.strength} against claimed {claimed.strength}")
    if kind == "control":
        return (not sourced, f"verdict {result.verdict}")
    return (not sourced, f"verdict {result.verdict}")


def strength_disagreement(claimed: Edge, result) -> bool:
    """For controls: the citation held but the strength label differs."""
    return (
        result.provenance == Provenance.SOURCE_ASSERTED
        and result.strength is not None
        and Strength(result.strength) != claimed.strength
    )


def summarise(rows: list[dict]) -> dict:
    by_kind: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "flagged": 0, "errors": 0, "strength_disagreements": 0, "verdicts": {}}
    )
    for row in rows:
        bucket = by_kind[row["kind"]]
        bucket["total"] += 1
        if row.get("error"):
            bucket["errors"] += 1
            continue
        bucket["flagged"] += bool(row["flagged"])
        bucket["strength_disagreements"] += bool(row.get("strength_disagreement"))
        verdict = row.get("verdict") or "?"
        bucket["verdicts"][verdict] = bucket["verdicts"].get(verdict, 0) + 1
    out = {}
    for kind, bucket in sorted(by_kind.items()):
        scored = bucket["total"] - bucket["errors"]
        out[kind] = {
            **bucket,
            "scored": scored,
            "rate": round(bucket["flagged"] / scored, 3) if scored else None,
        }
    return out


def render(summary: dict, rules_report: Path | None = None) -> str:
    semantic = [k for k in SEMANTIC if k in summary]
    caught = sum(summary[k]["flagged"] for k in semantic)
    total = sum(summary[k]["scored"] for k in semantic)
    semantic_total = sum(summary[k]["total"] for k in semantic)
    control = summary.get("control", {})
    lines = [
        "# Challenge set, model arm: what the verifier catches that rules cannot",
        "",
        "<!-- Generated by scripts/run_challenge_model_arm.py. Do not edit by hand. -->",
        "",
        "The rules-only arm (`reports/challenge_rules.md`) catches every citation "
        "corruption and **none** of the semantic ones, which is structural: a reversed "
        "edge keeps the same two variables, the same passage and the same verbatim "
        "span, so no deterministic rule can see it. This arm measures the verifier on "
        "exactly those items.",
        "",
        "| Corruption family | Items | Scored | Flagged | Rate | Rules could see it? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for kind, row in summary.items():
        if kind == "control":
            continue
        rate = "n/a" if row["rate"] is None else f"{row['rate']:.3f}"
        visible = "no, by construction" if kind in SEMANTIC else "yes, rejected before the model"
        lines.append(
            f"| {kind} | {row['total']} | {row['scored']} | {row['flagged']} | {rate} | {visible} |"
        )
    if control:
        rate = "n/a" if control["rate"] is None else f"{control['rate']:.3f}"
        lines += [
            "",
            f"**False-alarm rate on the {control['scored']} clean controls: {rate}.** "
            f"Unscored controls: {control['errors']}. "
            f"Strength disagreements on controls, reported separately and not counted as "
            f"false alarms: {control['strength_disagreements']}.",
        ]
    lines += [
        "",
        "## The number this arm exists for",
        "",
        f"**{caught} of {total} semantic corruptions caught** "
        f"({'n/a' if not total else round(caught / total, 3)}), against **0 of {total}** "
        "for the rule layer on the same scored subset. "
        f"{semantic_total - total} of {semantic_total} semantic items were unscored.",
        "",
        "## How detection is defined, and why it differs by family",
        "",
        "A `reversed_relation` is caught when the verifier declines to call the edge "
        "source-asserted. `contradicted` is the ideal answer and `unsupported` also "
        "counts, because either way the edge does not enter a graph as sourced.",
        "",
        "An `inflated_strength` item is **not** scored on provenance. The underlying "
        "edge is genuine, so a correct verifier returns source-asserted and disagrees "
        "on the strength label; scoring provenance would record zero detections for a "
        "verifier behaving exactly as intended. The detection is the strength it "
        "returns being weaker than the one claimed.",
        "",
        "The three citation corruptions are rejected by the rule layer before the model "
        "is reached. They are listed so this arm's totals match the rules arm's, not "
        "because the model is being tested on them.",
        "",
        "## What it does not establish",
        "",
        "Each corruption is applied mechanically to a known edge, so detection is "
        "ground truth and needs no human review. The false-alarm rate is different: a "
        "control is only clean if its gold edge was right, which rests on the "
        "adjudicated gold and its signed receipts.",
        "",
        "This is one model at one temperature on one frozen set. It says what this "
        "verifier caught here, not what a verifier catches in general.",
        "",
    ]
    if rules_report:
        lines += [f"Rules arm for comparison: `{rules_report}`.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=ITEMS)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--model-path", type=Path, default=Path("data/raw/generator/qwen3-8b-4bit"))
    parser.add_argument("--model", default="mlx-community/Qwen3-8B-4bit")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True, help="run directory for logs")
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--resume", action="store_true", help="skip items already judged")
    args = parser.parse_args(argv)

    if not args.corpus.is_file():
        raise SystemExit(f"corpus not found at {args.corpus}; it is not in git")
    items = [
        json.loads(line)
        for line in args.items.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    passages = [
        Passage.model_validate_json(line)
        for line in args.corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {p.passage_id: p for p in passages}

    args.output.mkdir(parents=True, exist_ok=True)
    results_path = args.output / "results.jsonl"
    done: set[str] = set()
    if args.resume and results_path.is_file():
        done = {
            json.loads(line)["item_id"]
            for line in results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        print(f"resuming: {len(done)} of {len(items)} already judged")

    write_json(
        args.output / "inputs.json",
        {
            "model": args.model,
            "revision": args.revision,
            "backend": "mlx",
            "model_files": model_identity(args.model_path),
            "runtime": runtime_identity(),
            "items": len(items),
            "status": "challenge-set model arm; detections are ground truth, "
            "the false-alarm rate rests on the adjudicated gold",
            "input_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (Path(__file__), args.items, REPO / "src/verify/llm_verifier.py")
            },
        },
    )

    generator = MLXGenerator(args.model_path, model_id=args.model, revision=args.revision)
    aliases = load_aliases()
    verifier = Verifier(generator, passages, aliases=aliases)

    with results_path.open("a", encoding="utf-8") as sink:
        for index, item in enumerate(items, start=1):
            item_id = item["item_id"]
            if item_id in done:
                continue
            kind = item["proposed_corruption"] or "control"
            row = {"item_id": item_id, "kind": kind, "query_id": item["query_id"]}
            passage = by_id.get(item["passage_id"])
            try:
                edge = Edge.model_validate(item["edge"])
            except ValueError as exc:
                # The schema refuses some corruptions outright. That is a
                # detection, and a stricter one than either layer.
                row |= {"flagged": True, "why": "schema refused the edge", "verdict": "schema"}
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                print(f"{index}/{len(items)} {item_id} schema-refused ({exc.__class__.__name__})")
                continue
            if passage is None:
                row |= {"error": "passage not in corpus"}
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                continue
            run_id = uuid.uuid4().hex
            log_path = args.output / f"{item_id}.jsonl"
            if log_path.exists():
                log_path = args.output / f"{item_id}-{run_id}.jsonl"
            logger = RunLogger(
                log_path,
                run_id=run_id,
                query_id=item_id,
                condition="M",
            )
            verifier.log_model = logger.model
            try:
                result = verifier.verify(
                    edge,
                    passage=passage,
                    span=edge.evidence_span or "",
                    as_of=date.fromisoformat(item["as_of"]),
                    call_id=item_id,
                )
                hit, why = flagged(kind, edge, result)
                row |= {
                    "flagged": hit,
                    "rule_failures": result.rule_failures,
                    "log_file": log_path.name,
                    "why": why,
                    "verdict": str(result.verdict),
                    "provenance": str(result.provenance),
                    "returned_strength": None if result.strength is None else str(result.strength),
                    "claimed_strength": str(edge.strength),
                    "strength_disagreement": (
                        strength_disagreement(edge, result) if kind == "control" else False
                    ),
                }
            except ValueError as exc:
                row |= {"error": f"unparseable judgment: {exc}", "log_file": log_path.name}
            finally:
                logger.close()
            sink.write(json.dumps(row) + "\n")
            sink.flush()
            print(f"{index}/{len(items)} {item_id} {kind} flagged={row.get('flagged')}")

    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary = summarise(rows)
    write_json(args.output / "summary.json", summary)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(summary, Path("reports/challenge_rules.md")), encoding="utf-8")
    print(f"\nwrote {args.report}")
    print(json.dumps({k: {"scored": v["scored"], "rate": v["rate"]} for k, v in summary.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
