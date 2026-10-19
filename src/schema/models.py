"""Frozen data contracts: Passage, Edge, Graph (PLAN_MIDSUB.md §0).

SHARED FILE. Announce in the group chat before changing anything here, and
regenerate `docs/schemas/` with `make schemas` in the same commit.

The invariants worth knowing before you edit:

* A `Passage` carries char offsets into its document and `len(text)` must equal
  `char_end - char_start`. Verbatim-span checking (B6) depends on this, so the
  model refuses to construct a passage whose offsets lie about its own text.
* An `Edge` labelled `source_asserted` must carry both an evidence span and the
  document it came from. That pairing is what the UER metric counts, so an
  asserted edge without a span is a schema error, not a data-quality problem.
* `model_inferred` edges may not carry `evidence_span`. A passage the verifier
  looked at and rejected goes in `candidate_evidence` instead, so failure
  analysis keeps it without it ever counting as support.
"""

from __future__ import annotations

from datetime import date, datetime
from itertools import pairwise
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from .enums import Direction, Provenance, SourceKind, Strength, VerifyVerdict, weakest
from .ontology import load_ontology

__all__ = [
    "CORPUS_END",
    "CORPUS_START",
    "Anchor",
    "CandidateEvidence",
    "Edge",
    "Graph",
    "GraphNode",
    "Passage",
    "Path",
]

#: The frozen corpus window (proposal §2). Enforced on every Passage.
CORPUS_START = date(2026, 3, 1)
CORPUS_END = date(2026, 9, 30)

VarId = Annotated[str, Field(min_length=2, max_length=40, pattern=r"^[A-Z][A-Z0-9_]*$")]


def _check_variable(var_id: str) -> str:
    ontology = load_ontology()
    if var_id not in ontology:
        raise ValueError(
            f"{var_id!r} is not in the closed ontology (src/schema/ontology.yaml, "
            f"version {ontology.version}). Extraction must map to an existing variable."
        )
    return var_id


# ---------------------------------------------------------------------------
# Passage
# ---------------------------------------------------------------------------


class Passage(BaseModel):
    """One paragraph of one document, with offsets back into the document text.

    Chunking happens at paragraph level (A5). `char_start` / `char_end` index into
    the *normalised document text* stored alongside the corpus, so a verifier can
    re-read the exact bytes an edge quotes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    passage_id: str = Field(
        min_length=1,
        description="Stable id, conventionally '<doc_id>#p<para_idx>'.",
    )
    doc_id: str = Field(min_length=1, description="Stable id of the parent document.")
    source: str = Field(
        min_length=1,
        description="Publication or issuing body, e.g. 'businessline', 'rbi', 'ppac'.",
    )
    source_kind: SourceKind = SourceKind.NEWS
    url: str | None = Field(default=None, description="Canonical URL, null for offline PDFs.")
    published_at: datetime = Field(
        description="Publication timestamp. The as-of filter compares its date component."
    )
    title: str = Field(min_length=1)
    text: str = Field(min_length=1, description="The paragraph itself, normalised whitespace.")
    para_idx: NonNegativeInt = Field(description="0-based paragraph index within the document.")
    char_start: NonNegativeInt = Field(description="Offset of `text` in the document text.")
    char_end: PositiveInt = Field(description="Exclusive end offset of `text`.")
    section: str | None = Field(default=None, description="e.g. 'lede', 'body', 'minutes-para-14'.")
    licence_note: str | None = None

    @model_validator(mode="after")
    def _offsets_match_text(self) -> Self:
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})"
            )
        span = self.char_end - self.char_start
        if span != len(self.text):
            raise ValueError(
                f"offsets describe {span} characters but text is {len(self.text)} long "
                f"(passage {self.passage_id!r}); verbatim-span checking would silently drift"
            )
        return self

    @model_validator(mode="after")
    def _inside_corpus_window(self) -> Self:
        published = self.published_at.date()
        if not (CORPUS_START <= published <= CORPUS_END):
            raise ValueError(
                f"passage {self.passage_id!r} is dated {published}, outside the frozen "
                f"corpus window {CORPUS_START}..{CORPUS_END}"
            )
        return self

    def visible_at(self, as_of: date) -> bool:
        """True when this passage was published on or before the as-of date (A11)."""
        return self.published_at.date() <= as_of

    def contains(self, span: str) -> bool:
        """Word-for-word containment check used by the rule layer (B6)."""
        return span in self.text


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------


class CandidateEvidence(BaseModel):
    """A passage the verifier considered and did not accept.

    Kept for failure analysis. It never counts as support, which is why it lives
    outside `evidence_span`.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    doc_id: str
    span: str = Field(min_length=1)
    verdict: VerifyVerdict
    reason: str | None = None


class Edge(BaseModel):
    """One causal link in an event-impact graph.

    `hop` is the distance of this edge's destination from the anchor event: an
    edge leaving the anchor is hop 1. Every headline metric is sliced on it.
    """

    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(min_length=1)
    src_var: VarId
    dst_var: VarId
    direction: Direction = Field(description="Which way `dst_var` moves.")
    provenance: Provenance
    strength: Strength
    hop: PositiveInt = Field(description="1 for an edge leaving the anchor event.")

    evidence_span: str | None = Field(
        default=None,
        min_length=1,
        description="Verbatim quote from the evidence passage. Required when source_asserted.",
    )
    evidence_doc_id: str | None = Field(
        default=None, description="Document the span was quoted from."
    )
    evidence_passage_id: str | None = Field(
        default=None, description="Passage the span was quoted from, when known."
    )
    evidence_published_at: datetime | None = Field(
        default=None, description="Publication timestamp of the evidence, for the as-of check."
    )
    candidate_evidence: list[CandidateEvidence] = Field(
        default_factory=list,
        description="Passages the verifier rejected. Never counts as support.",
    )

    verified_by: str | None = Field(
        default=None, description="'rules', 'llm', 'rules+llm', 'self-label' (B2) or None."
    )
    verdict: VerifyVerdict | None = None
    note: str | None = None

    @field_validator("src_var", "dst_var")
    @classmethod
    def _in_ontology(cls, value: str) -> str:
        return _check_variable(value)

    @model_validator(mode="after")
    def _no_self_loop(self) -> Self:
        if self.src_var == self.dst_var:
            raise ValueError(f"edge {self.edge_id!r} links {self.src_var} to itself")
        return self

    @model_validator(mode="after")
    def _direction_allowed_for_destination(self) -> Self:
        spec = load_ontology()[self.dst_var]
        if not spec.allows(self.direction):
            allowed = ", ".join(d.value for d in spec.allowed_directions)
            raise ValueError(
                f"direction {self.direction.value!r} is not allowed for {self.dst_var} "
                f"(allowed: {allowed})"
            )
        return self

    @model_validator(mode="after")
    def _provenance_matches_evidence(self) -> Self:
        if self.provenance is Provenance.SOURCE_ASSERTED:
            missing = [
                name
                for name, value in (
                    ("evidence_span", self.evidence_span),
                    ("evidence_doc_id", self.evidence_doc_id),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    f"edge {self.edge_id!r} is labelled source_asserted but is missing "
                    f"{' and '.join(missing)}; an asserted edge must carry its verbatim "
                    "evidence (proposal Table 2)"
                )
        elif self.evidence_span is not None:
            raise ValueError(
                f"edge {self.edge_id!r} is model_inferred but carries an evidence_span; "
                "put a rejected passage in candidate_evidence instead"
            )
        return self

    @property
    def is_asserted(self) -> bool:
        return self.provenance is Provenance.SOURCE_ASSERTED


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    """A variable as it appears in one graph, with the move attributed to it."""

    model_config = ConfigDict(extra="forbid")

    var: VarId
    direction: Direction
    label: str | None = Field(default=None, description="Display label, e.g. 'crude imports'.")
    is_anchor: bool = False
    confirmed_by_series: bool = Field(
        default=False,
        description="A macro series confirms the move happened. Never evidence for an edge.",
    )
    series_id: str | None = None

    @field_validator("var")
    @classmethod
    def _in_ontology(cls, value: str) -> str:
        return _check_variable(value)


class Anchor(BaseModel):
    """The queried event: a variable, a move, and the date it is pinned to."""

    model_config = ConfigDict(extra="forbid")

    var: VarId
    direction: Direction
    event: str = Field(min_length=1, description="One line, e.g. 'Brent crossed $100 on 12 Mar'.")
    event_date: date
    confirmed_by_series: bool = False
    series_id: str | None = None

    @field_validator("var")
    @classmethod
    def _in_ontology(cls, value: str) -> str:
        return _check_variable(value)


class Path(BaseModel):
    """A chain from the anchor outwards, scored by its weakest hop (ReCEval-style)."""

    model_config = ConfigDict(extra="forbid")

    path_id: str = Field(min_length=1)
    edge_ids: list[str] = Field(min_length=1)
    weakest_strength: Strength = Field(description="Minimum aggregation over the path's edges.")
    fully_sourced: bool = Field(description="True only when every hop is source_asserted.")
    depth: PositiveInt = Field(description="Number of hops; equals len(edge_ids).")

    @model_validator(mode="after")
    def _depth_matches_edges(self) -> Self:
        if self.depth != len(self.edge_ids):
            raise ValueError(
                f"path {self.path_id!r} says depth {self.depth} but lists "
                f"{len(self.edge_ids)} edges"
            )
        return self


class Graph(BaseModel):
    """One answer, as an inspectable event-impact graph."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    anchor: Anchor
    as_of: date = Field(description="No evidence published after this date may be used.")
    nodes: list[GraphNode] = Field(min_length=1)
    edges: list[Edge] = Field(default_factory=list)
    paths: list[Path] = Field(default_factory=list)

    condition: str | None = Field(default=None, description="Condition id, e.g. 'B1' or 'M'.")
    run_id: str | None = None
    model: str | None = None
    created_at: datetime | None = None
    schema_version: str = "1.0.0"
    notes: str | None = None

    # -- structural checks ------------------------------------------------

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        for label, ids in (
            ("node", [n.var for n in self.nodes]),
            ("edge", [e.edge_id for e in self.edges]),
            ("path", [p.path_id for p in self.paths]),
        ):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            if duplicates:
                raise ValueError(f"duplicate {label} ids in graph: {', '.join(duplicates)}")
        return self

    @model_validator(mode="after")
    def _anchor_is_a_node(self) -> Self:
        anchors = [n for n in self.nodes if n.is_anchor]
        if len(anchors) != 1:
            raise ValueError(
                f"graph {self.query_id!r} must have exactly one node flagged is_anchor, found "
                f"{len(anchors)}"
            )
        if anchors[0].var != self.anchor.var:
            raise ValueError(f"anchor node is {anchors[0].var} but Anchor.var is {self.anchor.var}")
        return self

    @model_validator(mode="after")
    def _edges_reference_known_nodes(self) -> Self:
        known = {n.var for n in self.nodes}
        for edge in self.edges:
            missing = {edge.src_var, edge.dst_var} - known
            if missing:
                raise ValueError(
                    f"edge {edge.edge_id!r} references node(s) not in the graph: "
                    f"{', '.join(sorted(missing))}"
                )
        return self

    @model_validator(mode="after")
    def _evidence_respects_as_of(self) -> Self:
        for edge in self.edges:
            stamp = edge.evidence_published_at
            if stamp is not None and stamp.date() > self.as_of:
                raise ValueError(
                    f"edge {edge.edge_id!r} cites evidence published {stamp.date()}, after the "
                    f"as-of date {self.as_of}"
                )
        return self

    @model_validator(mode="after")
    def _hops_match_distance_from_anchor(self) -> Self:
        """An edge leaving a node that sits `d` hops from the anchor is hop `d + 1`.

        Only edges whose source is reachable from the anchor are checked, so a
        partially built graph mid-agent-loop still validates.
        """
        depth = self._depth_from_anchor()
        for edge in self.edges:
            src_depth = depth.get(edge.src_var)
            if src_depth is None:
                continue
            expected = src_depth + 1
            if edge.hop != expected:
                raise ValueError(
                    f"edge {edge.edge_id!r} is labelled hop {edge.hop} but {edge.src_var} sits "
                    f"{src_depth} hop(s) from the anchor, so it is hop {expected}"
                )
        return self

    @model_validator(mode="after")
    def _paths_are_consistent(self) -> Self:
        by_id = {e.edge_id: e for e in self.edges}
        for path in self.paths:
            edges = []
            for edge_id in path.edge_ids:
                if edge_id not in by_id:
                    raise ValueError(f"path {path.path_id!r} references unknown edge {edge_id!r}")
                edges.append(by_id[edge_id])

            for earlier, later in pairwise(edges):
                if earlier.dst_var != later.src_var:
                    raise ValueError(
                        f"path {path.path_id!r} is broken: {earlier.edge_id} ends at "
                        f"{earlier.dst_var} but {later.edge_id} starts at {later.src_var}"
                    )
            if edges[0].src_var != self.anchor.var:
                raise ValueError(
                    f"path {path.path_id!r} starts at {edges[0].src_var}, not at the anchor "
                    f"{self.anchor.var}"
                )

            expected_weakest = weakest([e.strength for e in edges])
            if path.weakest_strength != expected_weakest:
                raise ValueError(
                    f"path {path.path_id!r} claims weakest hop {path.weakest_strength.value!r} "
                    f"but minimum aggregation over its edges gives "
                    f"{expected_weakest.value!r}"
                )
            expected_sourced = all(e.is_asserted for e in edges)
            if path.fully_sourced != expected_sourced:
                raise ValueError(
                    f"path {path.path_id!r} says fully_sourced={path.fully_sourced} but "
                    f"{sum(1 for e in edges if not e.is_asserted)} of {len(edges)} hops are "
                    "model_inferred"
                )
        return self

    # -- helpers -----------------------------------------------------------

    def _depth_from_anchor(self) -> dict[str, int]:
        """Breadth-first hop distance from the anchor variable."""
        adjacency: dict[str, list[str]] = {}
        for edge in self.edges:
            adjacency.setdefault(edge.src_var, []).append(edge.dst_var)

        depth = {self.anchor.var: 0}
        frontier = [self.anchor.var]
        while frontier:
            nxt: list[str] = []
            for var in frontier:
                for neighbour in adjacency.get(var, ()):
                    if neighbour not in depth:
                        depth[neighbour] = depth[var] + 1
                        nxt.append(neighbour)
            frontier = nxt
        return depth

    def edges_at_hop(self, hop: int) -> list[Edge]:
        """All edges at a given hop. `hop=3` is read as 'hop 3 or deeper' (proposal §12)."""
        if hop >= 3:
            return [e for e in self.edges if e.hop >= 3]
        return [e for e in self.edges if e.hop == hop]

    def established_edges(self) -> list[Edge]:
        """Edges the system presents as established — the denominator of UER."""
        return [e for e in self.edges if e.is_asserted]
