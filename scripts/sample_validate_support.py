"""Validate assistant-produced support labels against a human blind sample (#42).

The 10 November development scores rest on 247 support judgements that the
project's own record says were **assistant-produced**
(`reports/assistant_dev_support_review_20261110.md`, recoverable at commit
0933a7f). Re-labelling them as human does not make them human; the honest
options are a full human re-review or a measured sample. This is the sample.

A human blind-reviews a stratified draw from the preserved blank packets. The
agreement between that draw and the assistant's labels is then reported as the
basis for how far the remaining labels can be trusted — and quoted *with* its
raw agreement, because one label dominates here and kappa will collapse.

Two steps, run on the machine that holds the packets:

    # 1. draw the sample. Writes a blind worksheet and a private key.
    PYTHONPATH=src python scripts/sample_validate_support.py draw \\
        --packet primary=data/interim/varun_support_review_packet_01 \\
        --packet sensitivity=data/interim/varun_support_review_packet_02 \\
        --size 40 --out data/interim/support-validation

    # 2. after a human fills worksheet.csv, score it.
    PYTHONPATH=src python scripts/sample_validate_support.py score \\
        --dir data/interim/support-validation \\
        --report reports/support_sample_validation.md

**The reviewer opens `worksheet.csv` and nothing else.** It carries the evidence
and the claim and no label, no condition and no arm. `key.json` holds the
assistant's labels and is what the worksheet is scored against; opening it
first turns this from a measurement into a confirmation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from eval.agreement import kappa

#: The reviewer fills this. "supported" is the judgement the metric rests on;
#: evidence_strength is only meaningful when supported is yes.
BLANK_COLUMNS = ("supported", "evidence_strength", "note")
SUPPORTED = ("yes", "no")
STRENGTHS = ("direct", "conditional", "correlational")


def _load_packet(folder: Path) -> tuple[dict, dict]:
    """A prepared packet and its filled judgements."""
    packet = json.loads((folder / "packet.json").read_text(encoding="utf-8"))
    raw = json.loads((folder / "judgments.json").read_text(encoding="utf-8"))
    judgments = raw.get("judgments", raw)
    if isinstance(judgments, list):
        judgments = {row["item_id"]: row for row in judgments}
    return packet, judgments


def _items(packet: dict) -> dict[str, dict]:
    raw = packet.get("items", packet)
    if isinstance(raw, list):
        return {item["item_id"]: item for item in raw}
    return raw


def draw(packets: dict[str, Path], size: int, out: Path, seed: int) -> dict:
    """A stratified blind sample across arms and across the assistant's own labels.

    Stratifying on the assistant's label is the point. The primary arm labelled
    almost everything unsupported, so a uniform draw would be nearly all
    "unsupported" items and would only ever measure agreement in one direction.
    Drawing from each (arm, label) cell tests both directions of error: edges
    the assistant called supported that a human would not, and the reverse.
    """
    cells: dict[tuple[str, str], list[tuple[str, str, dict]]] = defaultdict(list)
    for arm, folder in packets.items():
        packet, judgments = _load_packet(folder)
        items = _items(packet)
        for item_id, judgment in judgments.items():
            if item_id not in items:
                raise ValueError(f"{arm}: judgement {item_id} has no item in packet.json")
            label = judgment.get("supported")
            label = "yes" if label is True else "no" if label is False else str(label)
            cells[(arm, label)].append((arm, item_id, items[item_id]))

    if not cells:
        raise ValueError("no judgements found in any packet")

    rng = random.Random(seed)
    # Sorted so the draw is reproducible from the seed alone.
    pools = {key: sorted(cells[key], key=lambda row: row[1]) for key in sorted(cells)}
    taken: dict[tuple[str, str], int] = dict.fromkeys(pools, 0)

    # Even allocation, then redistribute whatever thin strata cannot supply.
    # Without the second pass a near-empty cell silently shrinks the sample:
    # the primary arm labelled almost nothing supported, so its "yes" cell may
    # hold one item or none, and its share would otherwise just be lost.
    remaining = size
    while remaining > 0:
        hungry = [key for key, pool in pools.items() if taken[key] < len(pool)]
        if not hungry:
            break  # every item in every stratum is already drawn
        share, extra = divmod(remaining, len(hungry))
        if share == 0 and extra == 0:
            break
        progressed = False
        for index, key in enumerate(hungry):
            want = share + (1 if index < extra else 0)
            can = min(want, len(pools[key]) - taken[key])
            if can > 0:
                taken[key] += can
                remaining -= can
                progressed = True
        if not progressed:
            break

    chosen: list[tuple[str, str, dict]] = []
    for key, count in taken.items():
        if count:
            chosen.extend(rng.sample(pools[key], count))

    rng.shuffle(chosen)

    out.mkdir(parents=True, exist_ok=True)
    key_rows, sheet_rows = {}, []
    for position, (arm, item_id, item) in enumerate(chosen, start=1):
        row_id = f"v{position:03d}"
        packet, judgments = _load_packet(packets[arm])
        judgment = judgments[item_id]
        passage = item.get("passage") or {}
        key_rows[row_id] = {
            "arm": arm,
            "item_id": item_id,
            "assistant_supported": ("yes" if judgment.get("supported") is True else "no"),
            "assistant_evidence_strength": judgment.get("evidence_strength"),
        }
        sheet_rows.append(
            {
                "row_id": row_id,
                "claim": item.get("claim")
                or item.get("relation")
                or (
                    f"{item.get('src_var', '')} -> {item.get('dst_var', '')} "
                    f"({item.get('direction', '')})"
                ),
                "src_var": item.get("src_var", ""),
                "dst_var": item.get("dst_var", ""),
                "direction": item.get("direction", ""),
                "as_of": item.get("as_of", ""),
                "published": item.get("published") or passage.get("published_at", ""),
                "passage_id": item.get("passage_id") or passage.get("passage_id", ""),
                "evidence_span": item.get("evidence_span") or item.get("span") or "",
                "passage_text": passage.get("text", ""),
                **dict.fromkeys(BLANK_COLUMNS, ""),
            }
        )

    sheet = out / "worksheet.csv"
    with sheet.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sheet_rows[0]))
        writer.writeheader()
        writer.writerows(sheet_rows)

    (out / "key.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "size": len(chosen),
                "strata": {f"{a}/{lbl}": len(v) for (a, lbl), v in sorted(cells.items())},
                "rows": key_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# Blind support-label validation sample (#42)\n\n"
        f"{len(chosen)} items drawn with seed {seed} from "
        f"{len(cells)} (arm, assistant-label) strata.\n\n"
        "Fill **`worksheet.csv` only**. Do not open `key.json` first: it holds the\n"
        "assistant's labels, and reading them before you judge turns this from a\n"
        "measurement into a confirmation of what is already there.\n\n"
        "For each row decide whether the attached evidence span, from the cited\n"
        "passage and published on or before the as-of date, **states the claimed\n"
        "relation in the claimed direction**.\n\n"
        f"- `supported`: one of {', '.join(SUPPORTED)}\n"
        f"- `evidence_strength`: one of {', '.join(STRENGTHS)}; leave blank when "
        "`supported` is `no`\n"
        "- `note`: anything you hesitated over\n\n"
        "A partly-filled sheet is refused when scored. Agreement on half a sample is\n"
        "not agreement on the sample.\n",
        encoding="utf-8",
    )
    return {"size": len(chosen), "worksheet": str(sheet), "strata": len(cells)}


def _read_worksheet(path: Path) -> dict[str, dict[str, str | bool]]:
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            value = (row.get("supported") or "").strip().lower()
            if not value:
                raise ValueError(
                    f"{path} is incomplete: row {row['row_id']} has no 'supported' value. "
                    "Agreement on part of a sample is not agreement on the sample."
                )
            if value not in SUPPORTED:
                raise ValueError(f"row {row['row_id']}: supported must be yes or no, got {value!r}")
            strength = (row.get("evidence_strength") or "").strip().lower()
            if value == "no" and strength:
                raise ValueError(f"row {row['row_id']}: unsupported rows carry no strength")
            if strength and strength not in STRENGTHS:
                raise ValueError(f"row {row['row_id']}: unknown strength {strength!r}")
            rows[row["row_id"]] = {
                "supported": value,
                "evidence_strength": strength,
                "has_attached_evidence": bool(
                    (row.get("evidence_span") or "").strip()
                    and (row.get("passage_text") or "").strip()
                ),
            }
    if not rows:
        raise ValueError(f"{path} has no rows")
    return rows


def _fmt_kappa(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _fmt_ci(interval) -> str:
    return "n/a" if not interval else f"{interval[0]:.3f} to {interval[1]:.3f}"


def score(folder: Path, report: Path | None) -> str:
    key_path = folder / "key.json"
    worksheet_path = folder / "worksheet.csv"
    key = json.loads(key_path.read_text(encoding="utf-8"))
    human = _read_worksheet(worksheet_path)
    rows = key["rows"]
    if set(human) != set(rows):
        raise ValueError("worksheet rows do not match the key; was the sheet re-drawn?")

    assistant_labels = {r: rows[r]["assistant_supported"] for r in rows}
    human_labels = {r: human[r]["supported"] for r in rows}
    overall = kappa(human_labels, assistant_labels)
    informative_ids = [r for r in rows if human[r]["has_attached_evidence"]]
    if not informative_ids:
        raise ValueError("sample has no rows with attached evidence")
    informative = kappa(
        {r: human_labels[r] for r in informative_ids},
        {r: assistant_labels[r] for r in informative_ids},
    )

    disagreements = sorted(r for r in rows if human_labels[r] != assistant_labels[r])
    by_arm: dict[str, list[str]] = defaultdict(list)
    for row_id in rows:
        by_arm[rows[row_id]["arm"]].append(row_id)

    informative_disagreements = [r for r in informative_ids if r in disagreements]
    informative_rejected = sum(human_labels[r] == "no" for r in informative_ids)
    lines = [
        "# Does the assistant's support labelling survive a human sample? (#42)",
        "",
        "<!-- Generated by scripts/sample_validate_support.py. Do not edit by hand. -->",
        "",
        f"{len(rows)} items, drawn with seed {key['seed']} and stratified across arm and "
        "the assistant's own label so that both directions of error can show up. "
        f"Only {len(informative_ids)} carried both an attached passage and evidence span; "
        f"the other {len(rows) - len(informative_ids)} had no evidence to judge.",
        f"Worksheet SHA-256: `{hashlib.sha256(worksheet_path.read_bytes()).hexdigest()}`. "
        f"Private key SHA-256: `{hashlib.sha256(key_path.read_bytes()).hexdigest()}`.",
        "",
        "| measure | value |",
        "|---|---:|",
        f"| informative rows | {len(informative_ids)} of {len(rows)} |",
        f"| human rejected among informative rows | {informative_rejected} of {len(informative_ids)} |",
        f"| informative raw agreement | {informative['observed_agreement']:.3f} |",
        f"| informative chance agreement | {informative['chance_agreement']:.3f} |",
        f"| informative Cohen's kappa | {_fmt_kappa(informative['kappa'])} |",
        f"| informative 95% interval | {_fmt_ci(informative['ci95'])} |",
        f"| informative disagreements | {len(informative_disagreements)} of {len(informative_ids)} |",
        f"| all-row raw agreement (includes {len(rows) - len(informative_ids)} no-evidence rows) | {overall['observed_agreement']:.3f} |",
        "",
    ]
    if informative.get("paradox_warning"):
        lines += [
            "**High raw agreement with a low kappa.** One label dominates, so chance "
            "agreement approaches the observed agreement and the coefficient collapses. "
            "Quote the raw agreement beside it, never the kappa alone.",
            "",
        ]

    lines += [
        "## By arm",
        "",
        "| arm | informative items | assistant yes / no | human yes / no | informative disagreements | informative raw agreement |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm in sorted(by_arm):
        ids = [r for r in by_arm[arm] if r in informative_ids]
        bad = [r for r in ids if human_labels[r] != assistant_labels[r]]
        rate = f"{1 - len(bad) / len(ids):.3f}" if ids else "n/a"
        ay = sum(assistant_labels[r] == "yes" for r in ids)
        hy = sum(human_labels[r] == "yes" for r in ids)
        lines.append(
            f"| {arm} | {len(ids)} | {ay} / {len(ids) - ay} | {hy} / {len(ids) - hy} | {len(bad)} | {rate} |"
        )
    lines.append("")
    lines += [
        "## All drawn rows, including rows without evidence",
        "",
        "| arm | assistant yes | assistant no |",
        "|---|---:|---:|",
    ]
    for arm, ids in sorted(by_arm.items()):
        yes = sum(assistant_labels[r] == "yes" for r in ids)
        lines.append(f"| {arm} | {yes} | {len(ids) - yes} |")
    lines.append("")

    if disagreements:
        lines += [
            "## Where they disagreed",
            "",
            "| row | arm | human | assistant |",
            "|---|---|---|---|",
        ]
        for row_id in disagreements:
            lines.append(
                f"| `{row_id}` | {rows[row_id]['arm']} | {human_labels[row_id]} | "
                f"{assistant_labels[row_id]} |"
            )
        lines.append("")

    lines += [
        "## How to read this",
        "",
        "This measures **one human against the assistant on a sample**, not the quality "
        "of the labels in any absolute sense. It licenses a statement of the form "
        '"a human agreed with the assistant on N of M informative sampled judgements", and nothing '
        "stronger. It does not convert the remaining labels into human ones, and the "
        "scores built on them stay assistant-labelled.",
        "",
        "A sample this size cannot detect a rare error. Treat a disagreement rate near "
        "zero as consistent with the labels being usable for a descriptive development "
        "result, not as evidence they are correct.",
        "",
    ]

    text = "\n".join(lines)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    drawer = sub.add_parser("draw", help="draw a blind stratified sample")
    drawer.add_argument(
        "--packet",
        action="append",
        required=True,
        metavar="ARM=PATH",
        help="an arm name and its packet folder; repeat for each arm",
    )
    drawer.add_argument("--size", type=int, default=40)
    drawer.add_argument("--seed", type=int, default=20261110)
    drawer.add_argument("--out", type=Path, required=True)

    scorer = sub.add_parser("score", help="score a filled worksheet against the key")
    scorer.add_argument("--dir", type=Path, required=True)
    scorer.add_argument("--report", type=Path)

    args = parser.parse_args(argv)
    if args.command == "draw":
        packets = {}
        for pair in args.packet:
            if "=" not in pair:
                parser.error(f"--packet expects ARM=PATH, got {pair!r}")
            arm, path = pair.split("=", 1)
            packets[arm] = Path(path)
        result = draw(packets, args.size, args.out, args.seed)
        print(f"drew {result['size']} items across {result['strata']} strata")
        print(f"reviewer fills {result['worksheet']}; do not open key.json first")
    else:
        print(score(args.dir, args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
