"""Build the 200-item strength and detection benchmarks (B10).

    python scripts/build_strength_benchmark.py [--source DIR] [--n 200]

Reads two public datasets, samples a deterministic stratified subset of each,
and writes:

* ``data/eval/strength_benchmark.jsonl``  — the items (gitignored: third-party
  text, research use only, not ours to redistribute)
* ``data/eval/strength_benchmark_manifest.json`` — committed. Source URLs,
  SHA-256 of each source file, the selected row ids and the class counts, so
  the sample is reproducible without the text being in the repository.

Neither dataset is used for training. They are diagnostics on labelled text
nobody on this project wrote.

Download the sources first (they are not fetched automatically, so a build is
never silently different from the last one):

    curl -L -o <DIR>/pubmed_causal_language_use.csv \\
      https://raw.githubusercontent.com/junwang4/causal-language-use-in-science/master/data/pubmed_causal_language_use.csv
    curl -L -o <DIR>/fnp2020-fincausal-task1.csv \\
      https://raw.githubusercontent.com/yseop/YseopLab/develop/FNP_2020_FinCausal/data/trial/fnp2020-fincausal-task1.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

from eval.strength_bench import YU_EXPECTED_COUNTS, yu_strength

REPO = Path(__file__).resolve().parent.parent
ITEMS = REPO / "data/eval/strength_benchmark.jsonl"
MANIFEST = REPO / "data/eval/strength_benchmark_manifest.json"

YU_FILE = "pubmed_causal_language_use.csv"
FINCAUSAL_FILE = "fnp2020-fincausal-task1.csv"

SOURCES = {
    YU_FILE: (
        "https://raw.githubusercontent.com/junwang4/causal-language-use-in-science"
        "/master/data/pubmed_causal_language_use.csv"
    ),
    FINCAUSAL_FILE: (
        "https://raw.githubusercontent.com/yseop/YseopLab/develop"
        "/FNP_2020_FinCausal/data/trial/fnp2020-fincausal-task1.csv"
    ),
}

#: Fixed, so the sample is the same on every machine and in every re-run.
SEED = 20261027


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _load_yu(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    counts: dict[int, int] = {}
    for row in rows:
        counts[int(row["label"])] = counts.get(int(row["label"]), 0) + 1
    if counts != YU_EXPECTED_COUNTS:
        raise SystemExit(
            "Yu et al. class counts do not match the published README "
            f"({counts} != {YU_EXPECTED_COUNTS}). The label mapping in "
            "eval.strength_bench may no longer hold - check before trusting any score."
        )
    return [
        {
            "id": f"yu-{i:04d}",
            "source": "yu2019",
            "task": "strength",
            "text": row["sentence"],
            "gold": str(yu_strength(row["label"])),
            "raw_label": int(row["label"]),
        }
        for i, row in enumerate(rows)
        if yu_strength(row["label"]) is not None
    ]


def _load_fincausal(path: Path) -> list[dict]:
    csv.field_size_limit(10**7)
    out: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = next(reader)
        if [h.strip() for h in header][:3] != ["Index", "Text", "Gold"]:
            raise SystemExit(f"unexpected FinCausal header: {header}")
        for row in reader:
            if len(row) < 3:
                continue
            index, text, gold = row[0].strip(), row[1].strip(), row[2].strip()
            if gold not in {"0", "1"}:
                continue
            out.append(
                {
                    "id": f"fincausal-{index}",
                    "source": "fincausal2020",
                    "task": "detection",
                    "text": text,
                    "gold": "causal" if gold == "1" else "not_causal",
                    "raw_label": int(gold),
                }
            )
    return out


def _stratified(
    rows: list[dict], n: int, rng: random.Random, *, balanced: bool = False
) -> list[dict]:
    """Sample by gold class, deterministically.

    Proportional by default, which keeps the source's class balance. `balanced`
    takes an equal share of each class instead, used for detection: the
    FinCausal trial set is about 93% non-causal, and a proportional 200 leaves
    roughly a dozen positives, far too few for recall on the class the check
    exists to measure.
    """
    by_class: dict[str, list[dict]] = {}
    for row in rows:
        by_class.setdefault(row["gold"], []).append(row)

    picked: list[dict] = []
    for label in sorted(by_class):
        pool = sorted(by_class[label], key=lambda r: r["id"])
        share = n // len(by_class) if balanced else max(1, round(n * len(pool) / len(rows)))
        picked.extend(rng.sample(pool, min(share, len(pool))))
    picked.sort(key=lambda r: r["id"])
    return picked[:n]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="directory holding the two CSVs")
    parser.add_argument("--n", type=int, default=200, help="items per benchmark (default 200)")
    args = parser.parse_args(argv)

    missing = [name for name in SOURCES if not (args.source / name).is_file()]
    if missing:
        print(f"missing source files in {args.source}: {', '.join(missing)}", file=sys.stderr)
        print(__doc__ or "", file=sys.stderr)
        return 1

    rng = random.Random(SEED)
    yu = _stratified(_load_yu(args.source / YU_FILE), args.n, rng)
    fincausal = _stratified(
        _load_fincausal(args.source / FINCAUSAL_FILE), args.n, rng, balanced=True
    )
    items = [*yu, *fincausal]

    ITEMS.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n",
        encoding="utf-8",
    )

    def counts(rows: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            out[row["gold"]] = out.get(row["gold"], 0) + 1
        return dict(sorted(out.items()))

    manifest = {
        "seed": SEED,
        "n_per_benchmark": args.n,
        "note": (
            "Third-party text is not redistributed here. Re-run the builder against "
            "the source files to regenerate strength_benchmark.jsonl."
        ),
        "sampling": {
            "strength": "proportional to the source class balance",
            "detection": (
                "balanced across classes; the FinCausal trial set is about 93% "
                "non-causal, so a proportional sample leaves too few positives to "
                "estimate recall"
            ),
        },
        "sources": {
            name: {
                "url": url,
                "sha256": _sha256(args.source / name),
                "bytes": (args.source / name).stat().st_size,
            }
            for name, url in SOURCES.items()
        },
        "benchmarks": {
            "strength": {"n": len(yu), "counts": counts(yu), "ids": [r["id"] for r in yu]},
            "detection": {
                "n": len(fincausal),
                "counts": counts(fincausal),
                "ids": [r["id"] for r in fincausal],
            },
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"strength  {len(yu):4d} items {counts(yu)}")
    print(f"detection {len(fincausal):4d} items {counts(fincausal)}")
    print(f"wrote {ITEMS.relative_to(REPO)} and {MANIFEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
