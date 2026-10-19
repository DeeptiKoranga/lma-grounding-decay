"""Frozen data contracts for the whole project (PLAN_MIDSUB.md §0).

Import everything from here rather than from the submodules, so a later move
inside `src/schema/` does not ripple into the other tracks.
"""

from .enums import (
    STRENGTH_ORDER,
    Condition,
    Direction,
    Provenance,
    SourceKind,
    Strength,
    ToolName,
    VerifyVerdict,
    strength_rank,
    weakest,
)
from .models import (
    CORPUS_END,
    CORPUS_START,
    Anchor,
    CandidateEvidence,
    Edge,
    Graph,
    GraphNode,
    Passage,
    Path,
)
from .ontology import ONTOLOGY_PATH, Ontology, VariableSpec, load_ontology, variable_ids
from .runlog import RunLogLine, iter_run_log, parse_run_log_line
from .tools import (
    MAX_TOOL_CALLS,
    ToolCall,
    ToolError,
    ToolResult,
    parse_tool_call,
    parse_tool_result,
)

SCHEMA_VERSION = "1.0.0"

__all__ = [
    "CORPUS_END",
    "CORPUS_START",
    "MAX_TOOL_CALLS",
    "ONTOLOGY_PATH",
    "SCHEMA_VERSION",
    "STRENGTH_ORDER",
    "Anchor",
    "CandidateEvidence",
    "Condition",
    "Direction",
    "Edge",
    "Graph",
    "GraphNode",
    "Ontology",
    "Passage",
    "Path",
    "Provenance",
    "RunLogLine",
    "SourceKind",
    "Strength",
    "ToolCall",
    "ToolError",
    "ToolName",
    "ToolResult",
    "VariableSpec",
    "VerifyVerdict",
    "iter_run_log",
    "load_ontology",
    "parse_run_log_line",
    "parse_tool_call",
    "parse_tool_result",
    "strength_rank",
    "variable_ids",
    "weakest",
]
