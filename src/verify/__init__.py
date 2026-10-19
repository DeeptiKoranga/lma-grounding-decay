"""Verifier (Track B).

Three small modules, one concern each:

* `normalise` - the written-down policy on how much a quoted span may differ
  from its passage and still count as verbatim;
* `aliases` - the loader for `data/aliases.yaml`, the surface forms each
  ontology variable goes by (Track A owns the file from A6);
* `rules` - B6, the four deterministic pre-checks that must pass before the LLM
  verifier (B7) is consulted.

Import from here rather than from the submodules.
"""

from .aliases import ALIASES_PATH, AliasTable, load_aliases
from .normalise import collapse_whitespace, normalise_presentation
from .rules import (
    RULE_ORDER,
    EdgeScreening,
    RuleName,
    RuleOutcome,
    RuleReport,
    SpanMatch,
    SpanMatchKind,
    check_claim,
    check_edge,
    check_in_corpus,
    check_on_or_before_as_of,
    check_span_verbatim,
    check_variables_mentioned,
    screen_edge,
)

__all__ = [
    "ALIASES_PATH",
    "RULE_ORDER",
    "AliasTable",
    "EdgeScreening",
    "RuleName",
    "RuleOutcome",
    "RuleReport",
    "SpanMatch",
    "SpanMatchKind",
    "check_claim",
    "check_edge",
    "check_in_corpus",
    "check_on_or_before_as_of",
    "check_span_verbatim",
    "check_variables_mentioned",
    "collapse_whitespace",
    "load_aliases",
    "normalise_presentation",
    "screen_edge",
]
