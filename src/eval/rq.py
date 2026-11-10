"""RQ1 and RQ2 findings, with the gates that stop a thin slice becoming a trend.

`eval.metrics` and `eval.stats` already compute everything the two research
questions need: UER and strength inflation per hop bucket, reference-edge
recall, the pre-declared contrasts and the H2d guard. What they do not do is
decide whether the numbers are allowed to carry a claim.

That decision is the whole risk here. D-18 dropped the September bond
sell-off, which was the only anchor with a yield chain, so the hop >=3 bucket is
expected to be thin or empty - and a two-point "trend" over hops 1 and 2,
macro-averaged over four queries, looks exactly like a result while supporting
nothing. The gates below are pre-declared so the thresholds cannot be chosen
after seeing which side of them the data falls on.

RQ1  does the share of unsupported established edges rise with hop distance?
RQ2  do verification and edge-targeted retrieval reduce it without losing
     supported reference edges (H2d)?
"""

from __future__ import annotations

from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "BUCKETS",
    "MIN_BUCKETS_FOR_TREND",
    "MIN_ESTABLISHED_PER_BUCKET",
    "MIN_QUERIES_FOR_INFERENCE",
    "BucketReading",
    "Rq1Finding",
    "Rq2Finding",
    "rq1_finding",
    "rq2_finding",
]

# The four thresholds below are pre-declared in docs/decisions.md D-22, dated
# before any v7 run was scored. Lowering one after seeing a result is not a
# revisit; it is a different study. See that row before changing any of them.

#: Hop buckets, in order. "3+" pools everything at hop 3 or deeper, as the
#: proposal specifies and issue #43 asks for when deep edges are scarce.
BUCKETS: tuple[str, ...] = ("1", "2", "3+")

#: Below this many queries, no interval is inferential. The dev set is four
#: (D-19), so on dev this gate always fires - which is the point: it fires by
#: construction rather than by judgement.
MIN_QUERIES_FOR_INFERENCE = 10

#: A hop bucket carrying fewer established edges than this is reported, but
#: cannot support a claim about that hop or contribute to a trend.
MIN_ESTABLISHED_PER_BUCKET = 10

#: A monotone trend needs this many usable buckets. Two points are a line
#: through two points.
MIN_BUCKETS_FOR_TREND = 3

TrendVerdict = Literal[
    "insufficient_data",
    "rises_with_hop",
    "falls_with_hop",
    "no_monotone_trend",
]

GuardVerdict = Literal["passes", "fails", "undetermined"]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class BucketReading(BaseModel):
    """One hop bucket's numbers, plus whether they may be used for a claim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bucket: str
    uer: float | None
    strength_inflation: float | None
    reference_edge_recall: float | None
    established_edges: int
    queries_with_denominator: int
    queries_without_denominator: int
    usable: bool
    reason: str | None = None


class Rq1Finding(BaseModel):
    """Does grounding decay with distance from the anchor?"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition: str
    queries: int
    buckets: tuple[BucketReading, ...]
    trend: TrendVerdict
    usable_buckets: tuple[str, ...]
    inferential: bool = Field(
        description="False when the query count is below MIN_QUERIES_FOR_INFERENCE."
    )
    deep_bucket_empty: bool
    statement: str


class Rq2Finding(BaseModel):
    """Do verification and targeted retrieval repair it, without losing recall?"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline: str = "B1"
    treatment: str = "M"
    queries: int
    uer_delta: float | None = Field(default=None, description="M minus B1; negative is better.")
    uer_ci95: tuple[float, float] | None = None
    strength_inflation_delta: float | None = None
    recall_delta: float | None = Field(default=None, description="M minus B1 reference recall.")
    recall_guard_minimum: float = -0.10
    recall_guard: GuardVerdict = "undetermined"
    inferential: bool = False
    statement: str = ""


def _bucket_reading(bucket: str, aggregate: dict, per_query: dict[str, dict]) -> BucketReading:
    row = aggregate[bucket]
    established = sum(query[bucket]["established_edges"] for query in per_query.values())
    uer = row["uer"]
    with_denominator = uer["queries_with_denominator"]

    reasons = []
    if established == 0:
        reasons.append("no established edges in this bucket")
    elif established < MIN_ESTABLISHED_PER_BUCKET:
        reasons.append(
            f"{_plural(established, 'established edge')}, below the pre-declared "
            f"{MIN_ESTABLISHED_PER_BUCKET}"
        )
    if with_denominator == 0:
        reasons.append("no query has a denominator here")

    return BucketReading(
        bucket=bucket,
        uer=uer["mean"],
        strength_inflation=row["strength_inflation"]["mean"],
        reference_edge_recall=row["reference_edge_recall"]["mean"],
        established_edges=established,
        queries_with_denominator=with_denominator,
        queries_without_denominator=uer["queries_without_denominator"],
        usable=not reasons,
        reason="; ".join(reasons) or None,
    )


def rq1_finding(condition: str, aggregate: dict, per_query: dict[str, dict]) -> Rq1Finding:
    """Read RQ1 off one condition's scores, refusing to overstate a thin slice."""
    if not per_query:
        raise ValueError("RQ1 needs at least one scored query")

    readings = tuple(_bucket_reading(bucket, aggregate, per_query) for bucket in BUCKETS)
    usable = tuple(r.bucket for r in readings if r.usable and r.uer is not None)
    queries = len(per_query)
    inferential = queries >= MIN_QUERIES_FOR_INFERENCE
    deep_empty = next(r.established_edges for r in readings if r.bucket == "3+") == 0

    if len(usable) < MIN_BUCKETS_FOR_TREND:
        trend: TrendVerdict = "insufficient_data"
    else:
        values = [r.uer for r in readings if r.bucket in usable]
        if all(b > a for a, b in pairwise(values)):
            trend = "rises_with_hop"
        elif all(b < a for a, b in pairwise(values)):
            trend = "falls_with_hop"
        else:
            trend = "no_monotone_trend"

    statement = _rq1_statement(condition, readings, usable, trend, queries, deep_empty)
    return Rq1Finding(
        condition=condition,
        queries=queries,
        buckets=readings,
        trend=trend,
        usable_buckets=usable,
        inferential=inferential,
        deep_bucket_empty=deep_empty,
        statement=statement,
    )


def _rq1_statement(
    condition: str,
    readings: tuple[BucketReading, ...],
    usable: tuple[str, ...],
    trend: TrendVerdict,
    queries: int,
    deep_empty: bool,
) -> str:
    if trend == "insufficient_data":
        detail = "; ".join(f"hop {r.bucket}: {r.reason}" for r in readings if not r.usable)
        base = (
            f"**H1 is not testable on {condition} as it stands.** Only "
            f"{len(usable)} of {len(BUCKETS)} hop buckets clear the pre-declared minimum "
            f"of {MIN_ESTABLISHED_PER_BUCKET} established edges, and a trend needs "
            f"{MIN_BUCKETS_FOR_TREND}. {detail or 'no usable bucket'}."
        )
        if deep_empty:
            base += (
                " The hop 3-or-deeper bucket is **empty**, so nothing is being measured in "
                "the slice H1 is actually about. Report the shallow hops descriptively and "
                "say the deep slice is absent, rather than reporting a two-point trend."
            )
        return base

    direction = {
        "rises_with_hop": "rises monotonically with hop distance, the direction H1 predicts",
        "falls_with_hop": "falls monotonically with hop distance, the opposite of H1",
        "no_monotone_trend": "is not monotone in hop distance",
    }[trend]
    caveat = (
        ""
        if queries >= MIN_QUERIES_FOR_INFERENCE
        else (
            f" **Descriptive only**: {queries} "
            f"{'query' if queries == 1 else 'queries'} is below the pre-declared "
            f"{MIN_QUERIES_FOR_INFERENCE} for any inferential claim."
        )
    )
    return f"On {condition}, UER {direction} over buckets {', '.join(usable)}.{caveat}"


def rq2_finding(result: dict) -> Rq2Finding:
    """Read RQ2 off a full `eval.review.evaluate` result."""
    scores = result.get("per_query") or {}
    if not {"B1", "M"} <= scores.keys():
        return Rq2Finding(
            queries=0,
            statement=(
                "**RQ2 is not addressable yet.** It needs B1 and M scored on the same "
                f"queries; present conditions: {', '.join(sorted(scores)) or 'none'}."
            ),
        )

    paired = sorted(set(scores["B1"]) & set(scores["M"]))
    guard = result.get("recall_guard") or {}
    contrasts = result.get("contrasts") or {}
    uer = (contrasts.get("uer") or {}).get("M_minus_B1_overall") or {}
    inflation = (contrasts.get("strength_inflation") or {}).get("M_minus_B1_overall") or {}
    uer_pairs = uer.get("paired_queries", len(paired))
    if not isinstance(uer_pairs, int) or not 0 <= uer_pairs <= len(paired):
        raise ValueError("UER paired-query count must fit the shared query set")

    passes = guard.get("passes_descriptively")
    verdict: GuardVerdict = "undetermined" if passes is None else ("passes" if passes else "fails")
    # A bootstrap over one query resamples the same value every time and
    # returns a zero-width interval, which reads as precision rather than as
    # the absence of it. Withhold it rather than print it.
    ci = uer.get("ci95") if uer_pairs >= 2 else None
    inferential = uer_pairs >= MIN_QUERIES_FOR_INFERENCE

    return Rq2Finding(
        queries=uer_pairs,
        uer_delta=uer.get("estimate"),
        uer_ci95=(tuple(ci) if ci else None),
        strength_inflation_delta=inflation.get("estimate"),
        recall_delta=guard.get("M_minus_B1"),
        recall_guard=verdict,
        inferential=inferential,
        statement=_rq2_statement(uer.get("estimate"), verdict, guard, uer_pairs, inferential),
    )


def _rq2_statement(
    uer_delta: float | None,
    verdict: GuardVerdict,
    guard: dict,
    queries: int,
    inferential: bool,
) -> str:
    if uer_delta is None:
        return (
            "**RQ2 undetermined**: no paired UER difference between M and B1. "
            f"{guard.get('status', 'reference recall is incomplete')}."
        )

    moved = "reduces" if uer_delta < 0 else ("raises" if uer_delta > 0 else "does not change")
    head = (
        f"M {moved} UER against B1 by {abs(uer_delta):.3f} over "
        f"{_plural(queries, 'paired query').replace('querys', 'queries')}."
    )

    if verdict == "undetermined":
        tail = (
            " **The H2d recall guard is undetermined, so this cannot be reported as a "
            "repair.** A UER drop with unknown reference recall is indistinguishable from "
            "the verifier deleting edges it could not confirm. "
            f"{guard.get('status', '')}".rstrip()
        )
    elif verdict == "fails":
        moved_recall = (
            f" **H2d fails**: reference-edge recall moved {guard.get('M_minus_B1', 0):+.3f}, "
            f"past the pre-declared floor of {guard.get('minimum_M_minus_B1', -0.10):+.2f}."
        )
        # Only a UER *improvement* can have been bought by deleting edges. When
        # UER also rose, saying so would describe a trade that did not happen.
        tail = moved_recall + (
            " The improvement was bought by dropping supported edges, which is the failure"
            " mode the guard exists to catch."
            if uer_delta < 0
            else " M is worse on both counts here: UER did not fall and recall still dropped"
            " past the floor, so there is no trade-off to weigh."
        )
    else:
        tail = (
            f" H2d holds: reference-edge recall moved {guard.get('M_minus_B1', 0):+.3f}, "
            f"within the pre-declared floor of {guard.get('minimum_M_minus_B1', -0.10):+.2f}."
        )

    if not inferential:
        tail += (
            f" **Descriptive only**: {queries} paired "
            f"{'query' if queries == 1 else 'queries'} is below the pre-declared "
            f"{MIN_QUERIES_FOR_INFERENCE}, so the bootstrap interval bounds this sample and "
            "not the population."
        )
    return head + tail
