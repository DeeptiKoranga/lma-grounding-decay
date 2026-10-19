"""Closed vocabularies shared by every track.

These are frozen on Day 1 (PLAN_MIDSUB.md §0). Adding a member is a shared-file
change: announce it in the group chat before you push.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "STRENGTH_ORDER",
    "Condition",
    "Direction",
    "Provenance",
    "SourceKind",
    "Strength",
    "ToolName",
    "VerifyVerdict",
    "strength_rank",
    "weakest",
]


class Direction(StrEnum):
    """Which way the destination variable moves on this edge."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class Provenance(StrEnum):
    """Where an edge's support comes from. Set only by the verifier in M / A-NoLoop."""

    SOURCE_ASSERTED = "source_asserted"
    MODEL_INFERRED = "model_inferred"


class Strength(StrEnum):
    """Causal-strength label, adapted from Yu et al. (2019) and the Causal News Corpus."""

    DIRECT = "direct"
    CONDITIONAL = "conditional"
    CORRELATIONAL = "correlational"


#: Scoring order, strongest first (proposal Table 2: Direct > Conditional > Correlational).
STRENGTH_ORDER: tuple[Strength, ...] = (
    Strength.DIRECT,
    Strength.CONDITIONAL,
    Strength.CORRELATIONAL,
)


def strength_rank(strength: Strength) -> int:
    """0 for the strongest label, 2 for the weakest. Used by strength-inflation metrics."""
    return STRENGTH_ORDER.index(Strength(strength))


def weakest(strengths: list[Strength]) -> Strength:
    """ReCEval-style minimum aggregation: a path is only as strong as its weakest hop."""
    if not strengths:
        raise ValueError("weakest() needs at least one strength")
    return max(strengths, key=lambda s: strength_rank(s))


class SourceKind(StrEnum):
    """News copy and official documents are retrieved together but weighted differently."""

    NEWS = "news"
    OFFICIAL = "official"


class ToolName(StrEnum):
    """The six read-only tools (proposal §8). No tool may write outside the graph."""

    SEARCH_CORPUS = "search_corpus"
    GET_SERIES = "get_series"
    VERIFY_EDGE = "verify_edge"
    COUNTER_SEARCH = "counter_search"
    UPDATE_GRAPH = "update_graph"
    STOP = "stop"


class VerifyVerdict(StrEnum):
    """Outcome of one verify_edge call."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    OUT_OF_CORPUS = "out_of_corpus"
    AFTER_AS_OF = "after_as_of"


class Condition(StrEnum):
    """The seven experimental conditions. One code path, seven configs (C5)."""

    B0 = "B0"
    B1 = "B1"
    B1_R = "B1-R"
    B2 = "B2"
    A_NOVERIFY = "A-NoVerify"
    A_NOLOOP = "A-NoLoop"
    M = "M"
