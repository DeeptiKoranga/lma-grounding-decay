"""Seeded paired bootstrap over queries, restricted to the predeclared contrasts."""

from __future__ import annotations

import math
import random
from statistics import mean


def paired_bootstrap(
    left: dict[str, float | None], right: dict[str, float | None], *, samples=10000, seed=2026
) -> dict:
    if set(left) != set(right) or not left:
        raise ValueError("paired bootstrap requires the same nonempty query ids on both sides")
    if samples < 100:
        raise ValueError("bootstrap requires at least 100 resamples")
    ids = sorted(qid for qid in left if left[qid] is not None and right[qid] is not None)
    if any(
        not math.isfinite(value)
        for table in (left, right)
        for value in table.values()
        if value is not None
    ):
        raise ValueError("bootstrap values must be finite")
    if not ids:
        return {
            "estimate": None,
            "ci95": None,
            "paired_queries": 0,
            "excluded_queries": sorted(left),
        }
    differences = [left[qid] - right[qid] for qid in ids]
    rng = random.Random(seed)
    draws = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(samples))
    return {
        "estimate": mean(differences),
        "ci95": [draws[int(0.025 * (samples - 1))], draws[int(0.975 * (samples - 1))]],
        "paired_queries": len(ids),
        "excluded_queries": sorted(set(left) - set(ids)),
        "samples": samples,
        "seed": seed,
        "resampling_unit": "query",
    }


def predeclared_contrasts(scores: dict[str, dict[str, dict]], *, metric="uer", samples=10000):
    if metric not in {"uer", "strength_inflation"}:
        raise ValueError("only UER and pre-specified strength inflation contrasts are declared")
    if not {"B1", "M"} <= scores.keys():
        raise ValueError("predeclared contrasts require B1 and M")
    b1, full = scores["B1"], scores["M"]
    return {
        "B1_deep_minus_shallow": paired_bootstrap(
            {qid: row["3+"][metric] for qid, row in b1.items()},
            {qid: row["1"][metric] for qid, row in b1.items()},
            samples=samples,
        ),
        "M_minus_B1_overall": paired_bootstrap(
            {qid: row["overall"][metric] for qid, row in full.items()},
            {qid: row["overall"][metric] for qid, row in b1.items()},
            samples=samples,
        ),
    }
