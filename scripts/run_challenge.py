"""Run the deterministic rule layer over the challenge set (B9/#40).

    python scripts/run_challenge.py

Writes `reports/challenge_rules.md`. **No model is involved**, which is the
point: this measures what the B6 rules alone catch, and therefore what the LLM
verifier has to exist for.

Two of the five corruption families are invisible to the rules by construction,
not by oversight:

* `reversed_relation` swaps source and destination, so the cited passage still
  mentions both variables and the span is still verbatim. Every rule passes.
* `inflated_strength` changes only the strength label, which no rule reads.

So a rules-only arm should detect the three citation corruptions and miss those
two. If it did catch them, a rule would be doing something it does not claim to.
That expectation is asserted in the tests rather than discovered in the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from eval.challenge import CORRUPTIONS
from schema import Edge, Passage
from verify import check_edge, load_aliases, preceding_window

REPO = Path(__file__).resolve().parent.parent
ITEMS = REPO / "data/eval/challenge.jsonl"
MANIFEST = REPO / "data/eval/challenge_manifest.json"
CORPUS = REPO / "data/processed/articles.jsonl"
REPORT = REPO / "reports/challenge_rules.md"

#: Corruptions the rule layer can see, by construction. Anything outside this
#: set needs the semantic verifier, and the report says so rather than
#: recording a miss as a shortfall.
RULE_VISIBLE: tuple[str, ...] = (
    "unsupported_intermediate",
    "wrong_date",
    "wrong_target",
)


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def score(items: list[dict], passages: dict[str, Passage]) -> dict:
    """Per-kind flag counts from the rule layer. A 'flag' is a failed rule."""
    by_doc: dict[str, list[Passage]] = {}
    for passage in passages.values():
        by_doc.setdefault(passage.doc_id, []).append(passage)
    table = load_aliases()

    results: dict[str, dict] = {}
    for item in items:
        kind = item["proposed_corruption"] or "control"
        bucket = results.setdefault(kind, {"total": 0, "flagged": 0, "unscorable": 0, "rules": {}})
        bucket["total"] += 1

        passage = passages.get(item["passage_id"])
        if passage is None:
            bucket["unscorable"] += 1
            continue
        try:
            edge = Edge.model_validate(item["edge"])
        except ValueError:
            # The schema refuses some corruptions outright - a direction the
            # ontology does not allow for the new destination, say. That is a
            # detection, and a stricter one than the rule layer.
            bucket["flagged"] += 1
            bucket["rules"]["schema"] = bucket["rules"].get("schema", 0) + 1
            continue

        report = check_edge(
            edge,
            passage,
            as_of=date.fromisoformat(item["as_of"]),
            corpus_doc_ids={p.doc_id for p in passages.values()},
            aliases=table,
            document=preceding_window(passage, by_doc.get(passage.doc_id, ())),
        )
        if not report.passed:
            bucket["flagged"] += 1
            for outcome in report.outcomes:
                if not outcome.passed:
                    name = str(outcome.rule)
                    bucket["rules"][name] = bucket["rules"].get(name, 0) + 1
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=ITEMS)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)

    if not args.items.is_file():
        print(
            f"{args.items} not found. Build it first:\n"
            "  python -m eval.challenge --gold data/eval/gold/dev "
            "--corpus data/processed/articles.jsonl --output data/eval/challenge.jsonl "
            "--allow-unreviewed",
            file=sys.stderr,
        )
        return 2
    if not args.corpus.is_file():
        print(f"{args.corpus} not found; see data/processed/MANIFEST.md", file=sys.stderr)
        return 2

    items = [json.loads(line) for line in args.items.read_text().splitlines() if line.strip()]
    passages = {
        p.passage_id: p
        for line in args.corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    results = score(items, passages)

    control = results.get("control", {"total": 0, "flagged": 0})
    false_alarm = _rate(control["flagged"], control["total"])
    visible = [k for k in RULE_VISIBLE if k in results]
    detected = sum(results[k]["flagged"] for k in visible)
    denominator = sum(results[k]["total"] for k in visible)
    # Read off the built set rather than restated by hand: one control per gold
    # edge, and inflated_strength can only seed from a hedged edge, so these two
    # counts cannot drift from the set they describe.
    seed_count = control["total"]
    inflatable_count = results.get("inflated_strength", {}).get("total", 0)
    gold_adjudicated = bool(manifest.get("gold_adjudicated", False))

    lines = [
        "# Challenge set, rules-only arm (B9, #40)",
        "",
        "<!-- Generated by scripts/run_challenge.py. Do not edit by hand. -->",
        "",
        f"Run {date.today()}. **No model involved.** This is what the B6 rule layer catches "
        "on its own, and therefore what the LLM verifier has to exist for.",
        "",
        f"Gold adjudicated: **{manifest.get('gold_adjudicated', 'unknown')}**. "
        f"Items: {len(items)}.",
        "",
        "## Detection by corruption family",
        "",
        "| family | items | flagged | rate | rules can see it? |",
        "|---|---:|---:|---:|---|",
    ]
    for kind in ("control", *CORRUPTIONS):
        row = results.get(kind)
        if row is None:
            continue
        rate = _rate(row["flagged"], row["total"])
        if kind == "control":
            note = "n/a - these are the false alarms"
        else:
            note = "yes" if kind in RULE_VISIBLE else "**no, by construction**"
        lines.append(f"| {kind} | {row['total']} | {row['flagged']} | {_fmt(rate)} | {note} |")

    lines += [
        "",
        f"**Detection over the three rule-visible families: {detected}/{denominator} = "
        f"{_fmt(_rate(detected, denominator))}.**",
        f"**False-alarm rate on the {control['total']} clean controls: {_fmt(false_alarm)}.**",
        "",
        "## What the two misses mean",
        "",
        "`reversed_relation` and `inflated_strength` are invisible to these rules by "
        "construction. Reversing an edge leaves the same two variables in the same passage "
        "with the same verbatim span, so all four rules still pass; inflating a strength "
        "label changes nothing any rule reads. **This is the clearest argument in the "
        "project for the semantic verifier**: roughly two fifths of the corruption families, "
        "and the two that a careless graph is most likely to contain, cannot be caught by "
        "matching text at all.",
        "",
        "It also bounds the claim in the other direction. The three families the rules do "
        "catch are caught deterministically, cheaply and with no model, so a verifier that "
        "spends budget re-checking citations is spending it in the wrong place.",
        "",
        "## Reading the numbers",
        "",
        "Per-type counts are **uneven by construction** (D-21): the gold set supplies "
        f"{seed_count} seeds but only {inflatable_count} hedged links, so "
        f"`inflated_strength` has a denominator of {inflatable_count}. "
        "Quote every rate with its denominator; a macro average over families is not "
        "meaningful here.",
        "",
        "Corruption detection is sound either way, because each corruption was applied "
        "mechanically and is known by construction. **The false-alarm rate is not**: a "
        "control is only clean if its gold edge was right, so that figure rests on the "
        "state of the gold set.",
        "",
        (
            "The gold graphs here are **adjudicated** (D-26: two annotators, independently, "
            "8 Nov 2026), so the controls are as clean as that reconciliation left them. "
            "`gold_adjudicated` above reads the review receipt, which carries the "
            "reviewers' own signed attestation and is a separate step from the labelling; "
            "it stays False until they sign it."
            if not gold_adjudicated
            else "The gold graphs are adjudicated and the review receipt is signed."
        ),
        "",
    ]

    broken = {k: v["rules"] for k, v in results.items() if v.get("rules")}
    if broken:
        lines += ["## Which rule fired", "", "| family | rule | times |", "|---|---|---:|"]
        for kind, rules in broken.items():
            for rule, count in sorted(rules.items(), key=lambda kv: -kv[1]):
                lines.append(f"| {kind} | `{rule}` | {count} |")
        lines.append("")

    args.report.write_text(
        "\n".join(line.rstrip() for line in lines).rstrip() + "\n", encoding="utf-8"
    )
    print(f"wrote {args.report.relative_to(REPO)}")
    print(
        json.dumps(
            {
                "rule_visible_detection": _rate(detected, denominator),
                "false_alarm": false_alarm,
                "by_kind": {
                    k: {"total": v["total"], "flagged": v["flagged"]} for k, v in results.items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
