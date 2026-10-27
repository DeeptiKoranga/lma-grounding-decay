"""B6 - the deterministic rule layer the LLM verifier never gets to skip.

The proposal allows a passage to support an edge only when all four of these
hold. They are checked here, in code, with no model in the loop:

1. **in corpus** - the passage belongs to the frozen corpus, by `doc_id`;
2. **on or before the as-of date** - publication date <= as-of, *inclusive*;
3. **both variables mentioned** - the edge's source and destination variable
   are named, through the alias table (`verify.aliases`), in the cited passage
   or in the paragraph immediately before it (docs/decisions.md D-17);
4. **span verbatim** - the passage contains the quoted evidence span word for
   word (`verify.normalise` fixes exactly how much typographic slack is given).

Why a structured result rather than a bool
------------------------------------------
Two callers need to tell the failures apart. The agent's `verify_edge` tool
(C3) reports `rule_failures` back to the model, and "I quoted a span that is not
in that passage" should send it to re-read the passage, while "that document was
published after the as-of date" should send it to search again. The eval harness
slices the same distinction: a span miss is a grounding failure, an as-of miss
is a leakage failure, and averaging them together would hide both. So every
check runs - the layer never short-circuits - and each failure carries its own
reason string.

What passing does and does not mean
-----------------------------------
A `RuleReport` with no failures means **eligible for the LLM verifier**, not
supported. Nothing here reads the sentence; a passage can mention both variables
and contain the span and still not assert the relation (or assert the opposite
direction). That judgement is B7's, and `RuleReport.verdict` returns `None`
rather than `VerifyVerdict.SUPPORTED` to keep the two from being confused.
Failures, by contrast, are final: no LLM call can rescue an edge whose evidence
is out of corpus, after the as-of date, or not actually in the passage.

Pure functions, no I/O beyond reading the two YAML tables, no network, no corpus
dependency: everything here is testable against `tests/fixtures/` today.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schema import Edge, Passage, VerifyVerdict

from .aliases import AliasTable, load_aliases
from .normalise import normalise_presentation

__all__ = [
    "RULE_ORDER",
    "EdgeScreening",
    "MentionMatch",
    "MentionScope",
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
    "preceding_window",
    "screen_edge",
]

#: How much of a span to quote back in a failure message.
_EXCERPT = 90


class RuleName(StrEnum):
    """The four pre-checks. These strings land in `ToolResult.rule_failures`."""

    IN_CORPUS = "in_corpus"
    ON_OR_BEFORE_AS_OF = "on_or_before_as_of"
    BOTH_VARIABLES_MENTIONED = "both_variables_mentioned"
    SPAN_VERBATIM = "span_verbatim"


#: Cheapest and most fundamental first; also the order failures are reported in.
RULE_ORDER: tuple[RuleName, ...] = (
    RuleName.IN_CORPUS,
    RuleName.ON_OR_BEFORE_AS_OF,
    RuleName.BOTH_VARIABLES_MENTIONED,
    RuleName.SPAN_VERBATIM,
)


class SpanMatchKind(StrEnum):
    """How the span matched. `EXACT` is the only one that yields char offsets."""

    EXACT = "exact"
    NORMALISED = "normalised"


class SpanMatch(BaseModel):
    """Result of looking for one quoted span inside one passage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    found: bool
    kind: SpanMatchKind | None = None
    char_start: int | None = Field(
        default=None,
        description="Offset of the span in the *document* text, for an exact match only.",
    )
    char_end: int | None = None
    reason: str | None = Field(default=None, description="Set when `found` is False.")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.found and self.kind is None:
            raise ValueError("a found span must say how it matched")
        if not self.found and self.reason is None:
            raise ValueError("a span that was not found must carry a reason")
        return self


class MentionScope(StrEnum):
    """Where rule 3 found the two variables.

    `CITED` means both were in the cited paragraph. `WINDOW` means at least one
    was only in the paragraph before it, which is weaker evidence: the relation
    is stated across a paragraph break, usually through an anaphor ("the
    increase", "the move"). The eval harness reports the two separately so a
    UER figure cannot quietly rest on cross-break edges (docs/decisions.md D-17).
    """

    CITED = "cited"
    WINDOW = "window"


class MentionMatch(BaseModel):
    """Result of looking for both variables across the mention window.

    The counterpart of `SpanMatch` for rule 3. `src_passage_id` and
    `dst_passage_id` name the paragraph each variable was found in, so a caller
    can tell a both-in-one-paragraph edge from one that spans the break.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    found: bool
    scope: MentionScope | None = None
    src_passage_id: str | None = None
    dst_passage_id: str | None = None
    reason: str | None = Field(default=None, description="Set when `found` is False.")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.found:
            if self.scope is None:
                raise ValueError("a found mention pair must say which scope it was found in")
            if not (self.src_passage_id and self.dst_passage_id):
                raise ValueError("a found mention pair must name both paragraphs")
        elif self.reason is None:
            raise ValueError("a mention pair that was not found must carry a reason")
        return self


class RuleOutcome(BaseModel):
    """One rule, on one passage. `reason` is set exactly when the rule failed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: RuleName
    passed: bool
    reason: str | None = None
    mention_match: MentionMatch | None = Field(
        default=None,
        description="Set by rule 3 only; the detail behind `passed` (D-17).",
    )

    @model_validator(mode="after")
    def _reason_iff_failed(self) -> Self:
        if self.passed and self.reason is not None:
            raise ValueError(f"{self.rule} passed but carries a failure reason")
        if not self.passed and not self.reason:
            raise ValueError(f"{self.rule} failed without a reason; callers rely on it")
        return self


def _excerpt(text: str) -> str:
    collapsed = normalise_presentation(text)
    if len(collapsed) <= _EXCERPT:
        return collapsed
    return collapsed[: _EXCERPT - 1] + "\u2026"


# ---------------------------------------------------------------------------
# The four rules, each usable on its own
# ---------------------------------------------------------------------------


def check_in_corpus(passage: Passage, corpus_doc_ids: Collection[str]) -> RuleOutcome:
    """Rule 1: the passage's document is one the frozen corpus contains.

    Pass the manifest's doc ids (A4). An empty collection fails everything,
    which is the safe direction: the rule layer never assumes a corpus.
    """
    if passage.doc_id in corpus_doc_ids:
        return RuleOutcome(rule=RuleName.IN_CORPUS, passed=True)
    return RuleOutcome(
        rule=RuleName.IN_CORPUS,
        passed=False,
        reason=(
            f"document {passage.doc_id!r} (passage {passage.passage_id!r}) is not in the "
            f"permitted corpus of {len(corpus_doc_ids)} document(s)"
        ),
    )


def check_on_or_before_as_of(passage: Passage, as_of: date) -> RuleOutcome:
    """Rule 2: published on or before the as-of date. **Inclusive**, per the proposal.

    A document published on the as-of date itself is admissible; the next day's
    is not. The passage's own `published_at` is authoritative - an edge's
    `evidence_published_at` is a copy and is never trusted here.
    """
    published = passage.published_at.date()
    if passage.visible_at(as_of):
        return RuleOutcome(rule=RuleName.ON_OR_BEFORE_AS_OF, passed=True)
    return RuleOutcome(
        rule=RuleName.ON_OR_BEFORE_AS_OF,
        passed=False,
        reason=(
            f"passage {passage.passage_id!r} was published {published.isoformat()}, after the "
            f"as-of date {as_of.isoformat()}"
        ),
    )


def preceding_window(passage: Passage, document: Iterable[Passage]) -> tuple[Passage, ...]:
    """The cited passage plus the paragraph immediately before it, in order.

    `document` may be the cited document's paragraphs or the whole corpus: only
    passages with the same `doc_id` and `para_idx == passage.para_idx - 1` are
    taken, so the window never crosses a document boundary. Paragraph 0 has no
    predecessor and yields a window of one.

    The window reaches backwards only. A later paragraph is not evidence for an
    earlier claim: the anaphor this rule exists to resolve ("the increase")
    always points back (docs/decisions.md D-17).
    """
    if passage.para_idx == 0:
        return (passage,)
    previous = [
        other
        for other in document
        if other.doc_id == passage.doc_id and other.para_idx == passage.para_idx - 1
    ]
    return (*previous, passage)


def check_variables_mentioned(
    passage: Passage,
    src_var: str,
    dst_var: str,
    aliases: AliasTable,
    *,
    context: Sequence[Passage] = (),
) -> RuleOutcome:
    """Rule 3: both variables of the edge are named within the mention window.

    The window is the cited `passage` plus whatever `context` supplies, which is
    normally `preceding_window(passage, document)`. With no `context` the rule is
    scoped to the single passage, because a neighbouring paragraph that was never
    offered cannot be searched - so a caller that forgets to pass the document
    gets the strict result, never a falsely permissive one.

    Rule 4 does not widen with this: the quoted span must still be verbatim in
    the cited passage (docs/decisions.md D-17).
    """
    searched = (*context, passage) if passage not in context else tuple(context)
    ordered = sorted(dict.fromkeys(searched), key=lambda p: p.para_idx)

    located: dict[str, tuple[str, str]] = {}
    for var in (src_var, dst_var):
        for candidate in ordered:
            form = aliases.first_mention(var, candidate.text)
            if form is not None:
                located[var] = (form, candidate.passage_id)
                break

    missing = [var for var in (src_var, dst_var) if var not in located]
    if missing:
        seen = ", ".join(
            f"{var} (as {form!r} in {where})" for var, (form, where) in located.items()
        )
        where_searched = ", ".join(p.passage_id for p in ordered)
        return RuleOutcome(
            rule=RuleName.BOTH_VARIABLES_MENTIONED,
            passed=False,
            reason=(
                f"{' or '.join(missing)} is not mentioned in the window {where_searched}: "
                "no surface form from the alias table appears in it"
                + (f"; it does mention {seen}" if seen else "")
            ),
            mention_match=MentionMatch(
                found=False,
                reason=f"{' or '.join(missing)} absent from {where_searched}",
            ),
        )

    src_where, dst_where = located[src_var][1], located[dst_var][1]
    scope = (
        MentionScope.CITED if src_where == dst_where == passage.passage_id else MentionScope.WINDOW
    )
    return RuleOutcome(
        rule=RuleName.BOTH_VARIABLES_MENTIONED,
        passed=True,
        mention_match=MentionMatch(
            found=True,
            scope=scope,
            src_passage_id=src_where,
            dst_passage_id=dst_where,
        ),
    )


def check_span_verbatim(passage: Passage, span: str | None) -> SpanMatch:
    """Rule 4: the passage contains `span` word for word.

    Exact containment is tried first. Only on failure is the comparison retried
    through `normalise_presentation`, which folds typography and nothing that
    carries meaning - see `verify.normalise` and docs/decisions.md D-13.

    Char offsets are returned for an exact match only (the first occurrence),
    and index into the *document* text, matching `Passage.char_start`. A
    normalised match has no offsets: collapsing whitespace moves every
    subsequent character, so any offset derived from it would be a lie.
    """
    if span is None or not span.strip():
        return SpanMatch(
            found=False,
            reason="no evidence span was supplied, so there is nothing to match word for word",
        )

    index = passage.text.find(span)
    if index >= 0:
        start = passage.char_start + index
        return SpanMatch(
            found=True,
            kind=SpanMatchKind.EXACT,
            char_start=start,
            char_end=start + len(span),
        )

    if normalise_presentation(span) in normalise_presentation(passage.text):
        return SpanMatch(found=True, kind=SpanMatchKind.NORMALISED)

    return SpanMatch(
        found=False,
        reason=(
            f"span is not in passage {passage.passage_id!r}, even allowing whitespace, quote "
            f"and dash normalisation; span was {_excerpt(span)!r}"
        ),
    )


def _span_outcome(match: SpanMatch) -> RuleOutcome:
    if match.found:
        return RuleOutcome(rule=RuleName.SPAN_VERBATIM, passed=True)
    assert match.reason is not None  # SpanMatch enforces this
    return RuleOutcome(rule=RuleName.SPAN_VERBATIM, passed=False, reason=match.reason)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class RuleReport(BaseModel):
    """All four rules, run against one (claim, passage) pair.

    No failures means *eligible for the LLM verifier*, not supported. See the
    module docstring.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str | None = Field(default=None, description="None when screening a loose claim.")
    src_var: str
    dst_var: str
    passage_id: str
    doc_id: str
    as_of: date
    outcomes: tuple[RuleOutcome, ...] = Field(min_length=1)
    span_match: SpanMatch

    @model_validator(mode="after")
    def _every_rule_once(self) -> Self:
        seen = [outcome.rule for outcome in self.outcomes]
        if seen != list(RULE_ORDER):
            raise ValueError(
                "a rule report must carry every rule exactly once, in RULE_ORDER; got "
                f"{[str(rule) for rule in seen]}"
            )
        return self

    # -- reading the result -----------------------------------------------

    @property
    def passed(self) -> bool:
        """True when all four rules passed. Means eligible, not supported."""
        return all(outcome.passed for outcome in self.outcomes)

    @property
    def failures(self) -> tuple[RuleOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.passed)

    @property
    def rule_failures(self) -> list[str]:
        """Failed rule names, shaped for `ToolResult.rule_failures` (C3)."""
        return [str(outcome.rule) for outcome in self.failures]

    @property
    def verdict(self) -> VerifyVerdict | None:
        """The verdict the rules alone can justify, or None when they all pass.

        `out_of_corpus` and `after_as_of` outrank a plain `unsupported` because
        the safety metric counts them separately: an edge citing a document the
        system should not have been able to see is a leak, not a weak link.
        """
        failed = {outcome.rule for outcome in self.failures}
        if RuleName.IN_CORPUS in failed:
            return VerifyVerdict.OUT_OF_CORPUS
        if RuleName.ON_OR_BEFORE_AS_OF in failed:
            return VerifyVerdict.AFTER_AS_OF
        if failed:
            return VerifyVerdict.UNSUPPORTED
        return None

    def reason(self) -> str | None:
        """Every failure reason in rule order, joined; None when nothing failed."""
        if not self.failures:
            return None
        return "; ".join(outcome.reason or "" for outcome in self.failures)

    def outcome_for(self, rule: RuleName) -> RuleOutcome:
        return next(outcome for outcome in self.outcomes if outcome.rule == rule)

    @property
    def mention_match(self) -> MentionMatch:
        """Rule 3's detail: where each variable was found, and in what scope."""
        match = self.outcome_for(RuleName.BOTH_VARIABLES_MENTIONED).mention_match
        assert match is not None  # check_variables_mentioned always sets it
        return match


class EdgeScreening(BaseModel):
    """One edge against several candidate passages - the shape `verify_edge` needs.

    `verify_edge` is called with a list of `passage_ids` (see the fixture run
    log), so the rule layer screens them all and the caller passes the survivors
    to B7.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str | None = None
    src_var: str
    dst_var: str
    as_of: date
    reports: tuple[RuleReport, ...] = ()

    @property
    def eligible(self) -> tuple[RuleReport, ...]:
        """Reports that cleared all four rules, in the order the passages came in."""
        return tuple(report for report in self.reports if report.passed)

    @property
    def passed(self) -> bool:
        return bool(self.eligible)

    @property
    def best(self) -> RuleReport | None:
        """The report to quote: an eligible one, else the one that got furthest.

        "Furthest" is fewest failures, tie-broken by how late in `RULE_ORDER`
        the first failure sits, so "the span is not in this passage" is reported
        ahead of "that document is not in the corpus".
        """
        if not self.reports:
            return None
        if self.eligible:
            return self.eligible[0]
        return min(
            self.reports,
            key=lambda report: (
                len(report.failures),
                -RULE_ORDER.index(report.failures[0].rule),
            ),
        )

    @property
    def verdict(self) -> VerifyVerdict | None:
        """None when some passage is eligible; otherwise the best report's verdict."""
        if self.passed:
            return None
        best = self.best
        return VerifyVerdict.UNSUPPORTED if best is None else best.verdict

    @property
    def rule_failures(self) -> list[str]:
        best = self.best
        return [] if best is None or self.passed else best.rule_failures


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def _resolve_aliases(aliases: AliasTable | Path | None) -> AliasTable:
    if isinstance(aliases, AliasTable):
        return aliases
    return load_aliases(aliases)


def check_claim(
    src_var: str,
    dst_var: str,
    span: str | None,
    passage: Passage,
    *,
    as_of: date,
    corpus_doc_ids: Collection[str],
    aliases: AliasTable | Path | None = None,
    edge_id: str | None = None,
    document: Iterable[Passage] = (),
) -> RuleReport:
    """Run all four rules on a (claim, passage) pair, without needing an `Edge`.

    Used by extraction (B5) and the challenge-set builder (B9), which hold a
    candidate relation before it is a schema object. `aliases` takes a loaded
    table, a path to one, or None for `data/aliases.yaml`.

    `document` should be the cited document's paragraphs (the whole corpus is
    also fine) so rule 3 can see the paragraph before the cited one. Omitting it
    gives the strict, passage-only result - see `check_variables_mentioned`.
    """
    table = _resolve_aliases(aliases)
    span_match = check_span_verbatim(passage, span)
    outcomes = (
        check_in_corpus(passage, corpus_doc_ids),
        check_on_or_before_as_of(passage, as_of),
        check_variables_mentioned(
            passage,
            src_var,
            dst_var,
            table,
            context=preceding_window(passage, document),
        ),
        _span_outcome(span_match),
    )
    return RuleReport(
        edge_id=edge_id,
        src_var=src_var,
        dst_var=dst_var,
        passage_id=passage.passage_id,
        doc_id=passage.doc_id,
        as_of=as_of,
        outcomes=outcomes,
        span_match=span_match,
    )


def check_edge(
    edge: Edge,
    passage: Passage,
    *,
    as_of: date,
    corpus_doc_ids: Collection[str],
    aliases: AliasTable | Path | None = None,
    span: str | None = None,
    document: Iterable[Passage] = (),
) -> RuleReport:
    """Run all four rules on one edge against one passage.

    The span checked is `edge.evidence_span` unless `span` overrides it, which
    is how a `model_inferred` edge is screened against a candidate span before
    anything is written to the edge (the schema forbids an inferred edge from
    carrying one - docs/decisions.md D-10).
    """
    return check_claim(
        edge.src_var,
        edge.dst_var,
        edge.evidence_span if span is None else span,
        passage,
        as_of=as_of,
        corpus_doc_ids=corpus_doc_ids,
        aliases=aliases,
        edge_id=edge.edge_id,
        document=document,
    )


def screen_edge(
    edge: Edge,
    passages: Iterable[Passage] | Sequence[Passage],
    *,
    as_of: date,
    corpus_doc_ids: Collection[str],
    aliases: AliasTable | Path | None = None,
    span: str | None = None,
    document: Iterable[Passage] = (),
) -> EdgeScreening:
    """Run the rules on one edge against every candidate passage.

    `document` is passed through to rule 3's mention window, so it must hold the
    paragraphs around each candidate - the corpus slice the caller retrieved from
    is the usual thing to hand in.
    """
    table = _resolve_aliases(aliases)
    window_source = tuple(document)
    reports = tuple(
        check_edge(
            edge,
            passage,
            as_of=as_of,
            corpus_doc_ids=corpus_doc_ids,
            aliases=table,
            span=span,
            document=window_source,
        )
        for passage in passages
    )
    return EdgeScreening(
        edge_id=edge.edge_id,
        src_var=edge.src_var,
        dst_var=edge.dst_var,
        as_of=as_of,
        reports=reports,
    )
