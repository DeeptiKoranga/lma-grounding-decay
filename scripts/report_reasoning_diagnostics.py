"""Direction accuracy and strength macro-F1 against the reference graphs.

    PYTHONPATH=src python scripts/report_reasoning_diagnostics.py \\
        --runs runs/dev-gold-qwen3-8b --references data/eval/gold/dev

The proposal's Table 4 Reasoning row asks for "strength macro-F1 (human-labelled
edges and Yu et al. 2019 checks)" and "direction and provenance accuracy ... as
diagnostics". Three of those four are reported already: the Yu et al. half of
strength macro-F1 and the FinCausal checks in Section 4.3, provenance accuracy
in Section 4.9. The two this computes are the ones measured against the
project's **own** adjudicated edges rather than a public set:

* **direction accuracy** - of the generated edges that match a reference edge on
  source and destination, the share whose direction also matches. Kept separate
  from reference-edge recall, which requires direction to match before it counts
  an edge at all: recall asks how many reference edges were found, this asks how
  often the model got the sign right on the ones it did find. An edge that names
  the right pair and reverses the arrow is a different failure from not finding
  the pair, and the challenge set shows the rule layer cannot catch it.

* **strength macro-F1** - over the same matched edges, the model's strength
  label against the adjudicated one, macro-averaged so `correlational` counts
  as much as `direct` despite being rarer. Distinct from strength inflation,
  which counts only *over*-statements among supported edges; macro-F1 is
  symmetric and includes under-statement.

Both are **diagnostics**, as the proposal says. They are computed over whatever
matched edges exist, which on four development queries is a small number, and a
macro-F1 over a handful of edges per class is not a model comparison.

`runs/**` is gitignored, so this runs where the sweep ran.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from corpus.bindings import recorded_corpus_sha256
from eval.gold import load_gold_graph
from eval.references import validate
from eval.run_audit import audit
from schema import Graph

REPO = Path(__file__).resolve().parent.parent
STRENGTHS = ("direct", "conditional", "correlational")


def _reference_edges(references: Path) -> dict[str, dict]:
    """query_id -> the reference's cutoff and its (src, dst) -> direction, strength."""
    out: dict[str, dict] = {}
    for path in sorted(references.glob("*.json")):
        if path.name == "review_receipt.json":
            continue
        graph = load_gold_graph(path.stem, references)
        out[graph.query_id] = {
            "as_of": graph.as_of,
            "anchor": (graph.anchor.var, graph.anchor.direction, graph.anchor.event_date),
            "edges": {
                (e.src_var, e.dst_var): {
                    "direction": e.direction.value,
                    "strength": e.strength.value,
                    "edge_id": e.edge_id,
                }
                for e in graph.edges
            },
        }
    if not out:
        raise ValueError(f"no reference graphs under {references}")
    return out


def _generated(run_dir: Path) -> list[tuple[str, Graph]]:
    """(condition, graph) for every artifact that carries one."""
    found = []
    for artifact in sorted(run_dir.glob("*/*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        if "graph" not in payload:
            continue
        found.append((artifact.parent.name, Graph.model_validate(payload["graph"])))
    return found


def macro_f1(pairs: list[tuple[str, str]]) -> tuple[float | None, dict[str, dict]]:
    """Macro-F1 over (gold, predicted) label pairs, per class and averaged.

    A class with no gold instances and no predictions is dropped rather than
    scored 0, because averaging in a class nobody could have got wrong drags the
    mean toward whichever labels happen to be absent from a small sample.
    """
    per_class: dict[str, dict] = {}
    for label in STRENGTHS:
        tp = sum(1 for g, p in pairs if g == label and p == label)
        fp = sum(1 for g, p in pairs if g != label and p == label)
        fn = sum(1 for g, p in pairs if g == label and p != label)
        if tp + fp + fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "support": tp + fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }
    if not per_class:
        return None, {}
    return round(sum(c["f1"] for c in per_class.values()) / len(per_class), 3), per_class


def summarise(run_dir: Path, references: Path) -> dict:
    reference = _reference_edges(references)

    def blank() -> dict:
        return {
            "matched": 0,
            "direction_correct": 0,
            "strength_pairs": [],
            "no_reference": 0,
            "cutoff_mismatch": 0,
            "anchor_mismatch": 0,
            "graphs": 0,
        }

    by_condition: dict[str, dict] = defaultdict(blank)
    for condition, graph in _generated(run_dir):
        # Every condition that produced a graph gets a row, even one that matched
        # nothing. Creating the row only on a match made a condition with zero
        # matched edges vanish from the report rather than read 0, which is the
        # difference between "we measured nothing" and "we did not measure".
        row = by_condition[condition]
        row["graphs"] += 1
        gold = reference.get(graph.query_id)
        if gold is None:
            row["no_reference"] += 1
            continue
        if graph.as_of != gold["as_of"]:
            # The same query id at a different cutoff is a different question:
            # the reference was adjudicated under its own as-of discipline, and
            # matching across cutoffs would score edges against evidence that
            # was not yet visible, or withhold evidence that was. eval.references
            # refuses this elsewhere; so does this.
            row["cutoff_mismatch"] += 1
            continue
        if (graph.anchor.var, graph.anchor.direction, graph.anchor.event_date) != gold["anchor"]:
            row["anchor_mismatch"] += 1
            continue
        for edge in graph.edges:
            match = gold["edges"].get((edge.src_var, edge.dst_var))
            if match is None:
                continue
            row["matched"] += 1
            if edge.direction.value == match["direction"]:
                row["direction_correct"] += 1
            row["strength_pairs"].append((match["strength"], edge.strength.value))

    report = {}
    for condition in sorted(by_condition):
        row = by_condition[condition]
        f1, per_class = macro_f1(row["strength_pairs"])
        report[condition] = {
            "matched_edges": row["matched"],
            "direction_accuracy": (
                round(row["direction_correct"] / row["matched"], 3) if row["matched"] else None
            ),
            "strength_macro_f1": f1,
            "strength_per_class": per_class,
            "graphs": row["graphs"],
            "graphs_without_a_reference": row["no_reference"],
            "graphs_at_a_different_cutoff": row["cutoff_mismatch"],
            "graphs_at_a_different_anchor": row["anchor_mismatch"],
        }
    return report


def render(report: dict, runs: Path, references: Path) -> str:
    lines = [
        "# Reasoning diagnostics against the adjudicated references (Table 4)",
        "",
        "<!-- Generated by scripts/report_reasoning_diagnostics.py. Do not edit by hand. -->",
        "",
        f"Run logs `{runs}`, references `{references}`.",
        "",
        "Both figures are computed over **generated edges that match a reference "
        "edge on source and destination**. Direction accuracy asks how often the "
        "sign is right on the pairs the model did find, which reference-edge "
        "recall cannot say because it requires direction to match before counting "
        "an edge at all. Strength macro-F1 is symmetric, unlike strength "
        "inflation, so it counts under-statement as well as over-statement.",
        "",
        "| Condition | Graphs | Matched edges | Direction accuracy | Strength macro-F1 | Skipped |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for condition, row in report.items():
        acc = "n/a" if row["direction_accuracy"] is None else f"{row['direction_accuracy']:.3f}"
        f1 = "n/a" if row["strength_macro_f1"] is None else f"{row['strength_macro_f1']:.3f}"
        skipped = []
        if row["graphs_without_a_reference"]:
            skipped.append(f"{row['graphs_without_a_reference']} no reference")
        if row["graphs_at_a_different_cutoff"]:
            skipped.append(f"{row['graphs_at_a_different_cutoff']} cutoff mismatch")
        if row.get("graphs_at_a_different_anchor"):
            skipped.append(f"{row['graphs_at_a_different_anchor']} anchor mismatch")
        lines.append(
            f"| {condition} | {row['graphs']} | {row['matched_edges']} | {acc} | {f1} | "
            f"{', '.join(skipped) or '--'} |"
        )
    lines += ["", "## Strength, per class", ""]
    for condition, row in report.items():
        if not row["strength_per_class"]:
            lines.append(f"- **{condition}**: no matched edges to score.")
            continue
        parts = [
            f"`{label}` F1 {c['f1']:.3f} (n={c['support']})"
            for label, c in row["strength_per_class"].items()
        ]
        lines.append(f"- **{condition}**: " + "; ".join(parts))
    lines += [
        "",
        "## How to read this",
        "",
        "These are diagnostics, as the proposal labels them, over four "
        "development queries. A macro-F1 computed from a handful of edges per "
        "class is not a model comparison and carries no interval here.",
        "",
        "A class absent from both the references and the predictions is dropped "
        "rather than scored zero. Averaging in a class nobody could have got "
        "wrong drags the mean toward whichever labels happen to be missing from "
        "a small sample, which would make the figure move for reasons that have "
        "nothing to do with the model.",
        "",
        "A condition with 0 matched edges is shown with `n/a`, not omitted. A "
        "row that disappears reads as a condition that was never run; a row of "
        "zeros reads as a condition that produced nothing matching the "
        "references, which is a finding about that condition.",
        "",
        "Graphs are skipped, with a count, when the query has no reference or "
        "when the generated graph's cutoff differs from the reference's. The "
        "second is not pedantry: the reference was adjudicated under its own "
        "as-of discipline, so matching across cutoffs scores edges against "
        "evidence that was not yet visible, or withholds evidence that was.",
        "",
        "Direction accuracy near 1.000 with low reference-edge recall means the "
        "model finds few of the reference pairs but gets the sign right on those "
        "it finds. Those are separate failures and the challenge set shows why "
        "the distinction matters: reversing an edge leaves every deterministic "
        "rule passing, so nothing upstream of a reader catches it.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--references", type=Path, default=REPO / "data/eval/gold/dev")
    parser.add_argument("--corpus", type=Path, default=REPO / "data/processed/articles.jsonl")
    parser.add_argument("--report", type=Path, default=REPO / "reports/reasoning_diagnostics.md")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    if not args.runs.is_dir():
        raise SystemExit(f"{args.runs} is not a directory; runs/** is gitignored")
    try:
        corpus_sha = recorded_corpus_sha256(args.runs)
        inputs = json.loads((args.runs / "inputs.json").read_text(encoding="utf-8"))
        if not corpus_sha or inputs.get("format_version") != 2:
            raise ValueError("reasoning diagnostics require a bound v2 sweep")
        validation = audit(runs=args.runs, corpus=args.corpus)
        if not validation["complete"] or validation["failures"]:
            raise ValueError("sweep artifact or log audit failed")
        validate(references=args.references, corpus=args.corpus, expected_corpus_sha256=corpus_sha)
        report = summarise(args.runs, args.references)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"reasoning diagnostics: {exc}\n")
    if not report:
        raise SystemExit(f"no generated graphs under {args.runs}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(report, args.runs, args.references), encoding="utf-8")
    print(f"wrote {args.report}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
