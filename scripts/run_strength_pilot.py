"""Run the B10 strength and detection checks and write reports/pilot_strength.md.

    python scripts/run_strength_pilot.py [--classifier cue|llm]

`cue` is the deterministic word-list baseline in `eval.strength_bench`, needs no
model, and is the thing the model arm has to beat.

`llm` runs the pinned local model over the same 200 items on the same strength
taxonomy, and needs `--model-path` and `--revision`. Without the model it says
exactly what is missing and writes nothing, rather than leaving a gap that reads
like a result.

Scope the report has to state: the `llm` arm is **not** `verify.Verifier` end to
end. The verifier runs its deterministic rule layer against a corpus passage
first, and these benchmark sentences are not in our corpus - no passage, no
as-of date, no document id, so there is nothing for rules 1, 2 and 4 to check.
What is compared is the model's strength judgement against the word list's,
which is the comparison the design needs, on the taxonomy wording lifted from
the verifier's own prompt.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from eval.strength_bench import ScoreReport, cue_strength, llm_strength, score
from schema import Strength

REPO = Path(__file__).resolve().parent.parent
ITEMS = REPO / "data/eval/strength_benchmark.jsonl"
MANIFEST = REPO / "data/eval/strength_benchmark_manifest.json"
REPORT = REPO / "reports/pilot_strength.md"

#: Detection is binary; the cue baseline "detects" a relation when it fires at all.
CAUSAL, NOT_CAUSAL = "causal", "not_causal"


def _load() -> list[dict]:
    if not ITEMS.is_file():
        raise SystemExit(
            f"{ITEMS.relative_to(REPO)} not found. Run scripts/build_strength_benchmark.py "
            "against the downloaded sources first."
        )
    return [
        json.loads(line) for line in ITEMS.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _table(report: ScoreReport) -> list[str]:
    lines = [
        "| class | support | precision | recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report.per_class:
        lines.append(
            f"| {row.label} | {row.support} | {row.precision:.3f} | "
            f"{row.recall:.3f} | {row.f1:.3f} |"
        )
    lines.append(f"| **macro** | **{report.n}** | | | **{report.macro_f1:.3f}** |")
    return lines


def _confusion(report: ScoreReport) -> list[str]:
    predicted = list(next(iter(report.confusion.values())))
    lines = [
        "| gold \\ predicted | " + " | ".join(predicted) + " |",
        "|---" * (len(predicted) + 1) + "|",
    ]
    for gold, row in report.confusion.items():
        lines.append(f"| {gold} | " + " | ".join(str(row[p]) for p in predicted) + " |")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier", choices=["cue", "llm"], default="cue")
    parser.add_argument("--model-path", type=Path, default=Path("data/raw/generator/qwen3-8b-4bit"))
    parser.add_argument("--model", default="mlx-community/Qwen3-8B-4bit")
    parser.add_argument("--revision", help="pinned model revision; required for --classifier llm")
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--predictions", type=Path, help="write item IDs and predicted labels")
    args = parser.parse_args(argv)
    if args.classifier == "llm" and args.report == REPORT:
        parser.error("supply a separate --report to preserve the cue baseline")

    classify, generator = cue_strength, None
    if args.classifier == "llm":
        if not args.revision:
            print(
                "--classifier llm requires --revision (the pinned model revision)", file=sys.stderr
            )
            return 2
        if not args.model_path.is_dir():
            print(
                f"model not found at {args.model_path}. The pinned Qwen3-8B 4-bit weights are "
                "not on every machine; see reports/compute_log.md for where they live.",
                file=sys.stderr,
            )
            return 2
        from llm.generate import MLXGenerator

        generator = MLXGenerator(args.model_path, model_id=args.model, revision=args.revision)

        def classify(sentence: str) -> Strength | None:
            """An unparseable response is an abstention, never a guess: `score`
            counts abstentions against recall and never as correct."""
            try:
                return llm_strength(generator, sentence)
            except ValueError:
                return None

    items = _load()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    strength_items = [i for i in items if i["task"] == "strength"]
    gold = [Strength(i["gold"]) for i in strength_items]
    predicted = [classify(i["text"]) for i in strength_items]
    strength_report = score(gold, predicted)

    detection_items = [i for i in items if i["task"] == "detection"]
    det_gold = [i["gold"] for i in detection_items]
    detection_labels = [classify(i["text"]) for i in detection_items]
    det_pred = [CAUSAL if label is not None else NOT_CAUSAL for label in detection_labels]
    tp = sum(1 for g, p in zip(det_gold, det_pred, strict=True) if g == p == CAUSAL)
    fp = sum(1 for g, p in zip(det_gold, det_pred, strict=True) if g != p == CAUSAL)
    fn = sum(1 for g, p in zip(det_gold, det_pred, strict=True) if p != g == CAUSAL)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    accuracy = sum(1 for g, p in zip(det_gold, det_pred, strict=True) if g == p) / len(det_gold)

    lines = [
        "# Strength and direction checks on public data (B10)",
        "",
        "<!-- Generated by scripts/run_strength_pilot.py. Do not edit by hand. -->",
        "",
        f"Run {date.today()}. **Diagnostics only; neither dataset is used for training.**",
        "",
        "## What was measured, and against what",
        "",
        "Two public datasets nobody on this project wrote:",
        "",
        "- **Yu et al. (2019)**, causal language in PubMed findings. Its four classes are",
        "  the scheme proposal Table 2 was adapted from, so they map onto our strength",
        "  levels exactly: label 1 is *direct*, 2 is *conditional*, 3 is *correlational*,",
        "  and 0 (no relationship) is excluded. **1 is direct and 3 is correlational, not**",
        "  **the other way round** — the builder asserts the published class counts on load",
        "  so a re-release cannot silently invert this.",
        "- **FinCausal 2020** task 1, causal detection in financial news. Sampled balanced",
        "  at 100/100: the trial set is about 93% non-causal, so a proportional 200 leaves",
        "  roughly a dozen positives, too few to estimate recall on the class that matters.",
        "",
        f"Sample: {manifest['n_per_benchmark']} items per benchmark, seed {manifest['seed']}. ",
        "Source SHA-256 values and the selected row ids are in",
        "`data/eval/strength_benchmark_manifest.json`; the text itself is not redistributed.",
        "",
        (
            f"Classifier: {args.model} at revision `{args.revision}`."
            if generator
            else "Classifier: deterministic cue list."
        ),
        "",
        "## Strength, 3-class (Yu et al.)",
        "",
        *_table(strength_report),
        "",
        f"Accuracy {strength_report.accuracy:.3f}, macro-F1 {strength_report.macro_f1:.3f}, ",
        f"{strength_report.abstentions} abstentions (scored as wrong).",
        "",
        *_confusion(strength_report),
        "",
        "## Detection, binary (FinCausal 2020 task 1)",
        "",
        "Detection counts a returned strength label as causal.",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| accuracy | {accuracy:.3f} |",
        f"| precision | {precision:.3f} |",
        f"| recall | {recall:.3f} |",
        f"| F1 | {f1:.3f} |",
        "",
        "## Reading this",
        "",
        "The benchmark measures standalone taxonomy classification on public text. "
        "It does not run the corpus verifier's citation and date checks. "
        "Neither benchmark supplies edge-direction labels.",
    ]

    if args.predictions:
        rows = [
            {"id": item["id"], "gold": item["gold"], "predicted": label}
            for item, label in zip(items, [*predicted, *det_pred], strict=True)
        ]
        args.predictions.write_text(
            json.dumps(
                {"classifier": args.classifier, "revision": args.revision, "rows": rows}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )

    # Strip trailing whitespace per line: the pre-commit hook would otherwise
    # rewrite a generated file and fight the generator on every commit.
    body = "\n".join(line.rstrip() for line in lines).rstrip()
    args.report.write_text(body + "\n", encoding="utf-8")
    print(f"strength  macro-F1 {strength_report.macro_f1:.3f}  acc {strength_report.accuracy:.3f}")
    print(f"detection F1       {f1:.3f}  acc {accuracy:.3f}")
    print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
