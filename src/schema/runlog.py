"""RunLog line format: one JSONL line per model call, tool call or state snapshot.

Everything in `runs/<condition>/<query_id>.jsonl` is one of these. Every agentic
metric (next-action accuracy, redundant-search rate, tool calls per query) and
the whole compute log are computed from these lines, so a line that is not
written is a number that cannot be reported (C6).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .enums import Condition
from .tools import ToolCall, ToolResult

__all__ = ["RunLogLine", "iter_run_log", "parse_run_log_line"]


class _LineBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    condition: Condition
    step: int = Field(ge=0)
    ts: datetime


class ModelCallLine(_LineBase):
    """One generation. Prompts are stored in full; a hash is kept for dedup."""

    event: Literal["model_call"] = "model_call"
    purpose: Literal["parse_query", "extract", "bridge", "verify", "answer", "control"]
    model: str = Field(min_length=1)
    backend: Literal["mlx", "llama.cpp", "vllm", "api"]
    temperature: float = Field(ge=0.0, le=2.0)
    prompt: str | None = Field(default=None, description="Full prompt text when kept inline.")
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion: str | None = None
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    json_valid: bool | None = Field(
        default=None, description="Did the output parse under the expected schema?"
    )


class ToolCallLine(_LineBase):
    event: Literal["tool_call"] = "tool_call"
    budget_remaining: int = Field(ge=0)
    call: ToolCall


class ToolResultLine(_LineBase):
    event: Literal["tool_result"] = "tool_result"
    result: ToolResult
    new_passages: int = Field(default=0, ge=0, description="Passages not seen earlier this run.")


class StateLine(_LineBase):
    """Controller state after a step. Drives the redundant-search metric."""

    event: Literal["state"] = "state"
    open_edges: list[str] = Field(default_factory=list)
    verified_edges: list[str] = Field(default_factory=list)
    searches_done: int = Field(ge=0)
    budget_remaining: int = Field(ge=0)
    next_action: str | None = None


class StopLine(_LineBase):
    event: Literal["stop"] = "stop"
    reason: Literal[
        "important_edges_resolved",
        "two_searches_added_nothing",
        "budget_exhausted",
        "error",
    ]
    calls_used: int = Field(ge=0)
    open_edges_remaining: int = Field(ge=0)
    wall_clock_s: float | None = Field(default=None, ge=0)


class ErrorLine(_LineBase):
    event: Literal["error"] = "error"
    where: str = Field(min_length=1)
    message: str = Field(min_length=1)
    recoverable: bool = True


RunLogLine = Annotated[
    ModelCallLine | ToolCallLine | ToolResultLine | StateLine | StopLine | ErrorLine,
    Field(discriminator="event"),
]

RunLogAdapter: TypeAdapter[RunLogLine] = TypeAdapter(RunLogLine)


def parse_run_log_line(payload: dict | str) -> RunLogLine:
    if isinstance(payload, str):
        return RunLogAdapter.validate_json(payload)
    return RunLogAdapter.validate_python(payload)


def iter_run_log(path) -> list[RunLogLine]:
    """Read a whole `.jsonl` run log, validating every line."""
    from pathlib import Path

    lines = []
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            lines.append(parse_run_log_line(raw))
        except Exception as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return lines
