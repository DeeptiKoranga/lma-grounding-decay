"""ToolCall / ToolResult envelope for the six read-only tools (PLAN_MIDSUB.md §0).

Both envelopes are discriminated unions on `tool`, so each tool gets its own
argument and payload schema and `argument validity` (proposal Table 4) is a
parse, not a hand-written check. Track C validates every model-proposed call
through `parse_tool_call` before anything executes.

All six tools are read-only. `update_graph` edits the in-memory graph only, and
`stop` ends the loop; nothing here touches the corpus on disk.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .enums import Direction, Provenance, Strength, ToolName, VerifyVerdict
from .models import Edge, GraphNode, Passage

__all__ = [
    "MAX_TOOL_CALLS",
    "ToolCall",
    "ToolError",
    "ToolResult",
    "parse_tool_call",
    "parse_tool_result",
]

#: Hard agent budget (proposal §8). Enforced in code, not by prompting.
MAX_TOOL_CALLS = 12


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(min_length=1)
    step: int = Field(ge=0, description="0-based position in the agent loop.")
    run_id: str | None = None
    query_id: str | None = None


# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------


class SearchCorpusArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    k: int = Field(default=10, ge=1, le=50)
    as_of: date = Field(description="Enforced in code; the model cannot widen it.")
    source_kind: Literal["news", "official", "any"] = "any"
    must_mention: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Variable ids both of which an evidence passage should mention.",
    )


class GetSeriesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_id: str = Field(min_length=1)
    start: date
    end: date
    as_of: date

    @model_validator(mode="after")
    def _window_is_sane(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"end {self.end} precedes start {self.start}")
        if self.end > self.as_of:
            raise ValueError(f"end {self.end} is after the as-of date {self.as_of}")
        return self


class VerifyEdgeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(min_length=1)
    passage_ids: list[str] = Field(
        default_factory=list, max_length=10, description="Candidate passages to judge against."
    )
    as_of: date


class CounterSearchArgs(BaseModel):
    """Look for a competing cause of the same move, used on 'why' questions."""

    model_config = ConfigDict(extra="forbid")

    dst_var: str = Field(min_length=1)
    direction: Direction
    exclude_src_vars: list[str] = Field(default_factory=list, max_length=10)
    k: int = Field(default=10, ge=1, le=50)
    as_of: date


class UpdateGraphArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["add_node", "add_edge", "relabel_edge", "drop_edge"]
    node: GraphNode | None = None
    edge: Edge | None = None
    edge_id: str | None = None
    provenance: Provenance | None = None
    strength: Strength | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _payload_matches_op(self) -> Self:
        required = {
            "add_node": ("node",),
            "add_edge": ("edge",),
            "relabel_edge": ("edge_id",),
            "drop_edge": ("edge_id",),
        }[self.op]
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise ValueError(f"op {self.op!r} needs {', '.join(missing)}")
        if self.op == "relabel_edge" and self.provenance is None and self.strength is None:
            raise ValueError("relabel_edge needs a new provenance or strength")
        return self


class StopArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Literal[
        "important_edges_resolved",
        "two_searches_added_nothing",
        "budget_exhausted",
    ]
    note: str | None = None


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------


class SearchCorpusCall(_Envelope):
    tool: Literal[ToolName.SEARCH_CORPUS] = ToolName.SEARCH_CORPUS
    args: SearchCorpusArgs


class GetSeriesCall(_Envelope):
    tool: Literal[ToolName.GET_SERIES] = ToolName.GET_SERIES
    args: GetSeriesArgs


class VerifyEdgeCall(_Envelope):
    tool: Literal[ToolName.VERIFY_EDGE] = ToolName.VERIFY_EDGE
    args: VerifyEdgeArgs


class CounterSearchCall(_Envelope):
    tool: Literal[ToolName.COUNTER_SEARCH] = ToolName.COUNTER_SEARCH
    args: CounterSearchArgs


class UpdateGraphCall(_Envelope):
    tool: Literal[ToolName.UPDATE_GRAPH] = ToolName.UPDATE_GRAPH
    args: UpdateGraphArgs


class StopCall(_Envelope):
    tool: Literal[ToolName.STOP] = ToolName.STOP
    args: StopArgs


ToolCall = Annotated[
    SearchCorpusCall
    | GetSeriesCall
    | VerifyEdgeCall
    | CounterSearchCall
    | UpdateGraphCall
    | StopCall,
    Field(discriminator="tool"),
]

ToolCallAdapter: TypeAdapter[ToolCall] = TypeAdapter(ToolCall)


def parse_tool_call(payload: dict | str) -> ToolCall:
    """Validate one model-proposed tool call. Raises `ValidationError` if malformed."""
    if isinstance(payload, str):
        return ToolCallAdapter.validate_json(payload)
    return ToolCallAdapter.validate_python(payload)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class ToolError(BaseModel):
    """A scripted or real tool fault (C9 uses 20 of these)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "empty_result",
        "bad_arguments",
        "unknown_series",
        "unknown_edge",
        "after_as_of",
        "budget_exhausted",
        "backend_error",
    ]
    message: str = Field(min_length=1)


class SeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    on: date
    value: float


class _ResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(min_length=1)
    ok: bool = True
    error: ToolError | None = None
    latency_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _error_matches_ok(self) -> Self:
        if self.ok and self.error is not None:
            raise ValueError("a successful tool result must not carry an error")
        if not self.ok and self.error is None:
            raise ValueError("a failed tool result must carry an error")
        return self


class SearchCorpusResult(_ResultEnvelope):
    tool: Literal[ToolName.SEARCH_CORPUS] = ToolName.SEARCH_CORPUS
    passages: list[Passage] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    truncated: bool = False


class GetSeriesResult(_ResultEnvelope):
    tool: Literal[ToolName.GET_SERIES] = ToolName.GET_SERIES
    series_id: str | None = None
    points: list[SeriesPoint] = Field(default_factory=list)
    move: Direction | None = Field(
        default=None, description="Confirms a move happened. Never evidence for an edge."
    )


class VerifyEdgeResult(_ResultEnvelope):
    tool: Literal[ToolName.VERIFY_EDGE] = ToolName.VERIFY_EDGE
    edge_id: str | None = None
    verdict: VerifyVerdict | None = None
    provenance: Provenance | None = None
    strength: Strength | None = None
    direction: Direction | None = None
    evidence_span: str | None = None
    evidence_passage_id: str | None = None
    rule_failures: list[str] = Field(
        default_factory=list, description="Which of the rule-layer checks (B6) failed."
    )


class CounterSearchResult(_ResultEnvelope):
    tool: Literal[ToolName.COUNTER_SEARCH] = ToolName.COUNTER_SEARCH
    passages: list[Passage] = Field(default_factory=list)
    competing_src_vars: list[str] = Field(default_factory=list)


class UpdateGraphResult(_ResultEnvelope):
    tool: Literal[ToolName.UPDATE_GRAPH] = ToolName.UPDATE_GRAPH
    applied: bool = False
    graph_version: int | None = Field(default=None, ge=0)


class StopResult(_ResultEnvelope):
    tool: Literal[ToolName.STOP] = ToolName.STOP
    calls_used: int | None = Field(default=None, ge=0, le=MAX_TOOL_CALLS)
    open_edges_remaining: int | None = Field(default=None, ge=0)


ToolResult = Annotated[
    SearchCorpusResult
    | GetSeriesResult
    | VerifyEdgeResult
    | CounterSearchResult
    | UpdateGraphResult
    | StopResult,
    Field(discriminator="tool"),
]

ToolResultAdapter: TypeAdapter[ToolResult] = TypeAdapter(ToolResult)


def parse_tool_result(payload: dict | str) -> ToolResult:
    if isinstance(payload, str):
        return ToolResultAdapter.validate_json(payload)
    return ToolResultAdapter.validate_python(payload)
