"""Round-trips and argument validation for the six tools and the run-log lines."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from schema import MAX_TOOL_CALLS, RunLogLine, ToolName, parse_run_log_line, parse_tool_call
from schema.tools import ToolCallAdapter, ToolResultAdapter, parse_tool_result


def call(tool: str, args: dict, **overrides) -> dict:
    payload = {"call_id": "c1", "step": 0, "tool": tool, "args": args}
    payload.update(overrides)
    return payload


def test_all_six_tools_are_representable():
    assert {t.value for t in ToolName} == {
        "search_corpus",
        "get_series",
        "verify_edge",
        "counter_search",
        "update_graph",
        "stop",
    }


def test_budget_is_twelve():
    assert MAX_TOOL_CALLS == 12


# --- tool calls -----------------------------------------------------------


def test_search_corpus_call_round_trips():
    parsed = parse_tool_call(
        call("search_corpus", {"query": "brent import bill", "k": 5, "as_of": "2026-03-20"})
    )
    assert parsed.tool is ToolName.SEARCH_CORPUS
    assert parsed.args.as_of == date(2026, 3, 20)
    assert ToolCallAdapter.validate_json(parsed.model_dump_json()) == parsed


def test_unknown_tool_is_rejected():
    with pytest.raises(ValidationError):
        parse_tool_call(call("browse_web", {"url": "https://example.invalid"}))


def test_arguments_the_tool_does_not_take_are_rejected():
    with pytest.raises(ValidationError):
        parse_tool_call(
            call("search_corpus", {"query": "x", "as_of": "2026-03-20", "site": "example.com"})
        )


def test_search_k_is_bounded():
    with pytest.raises(ValidationError):
        parse_tool_call(call("search_corpus", {"query": "x", "k": 500, "as_of": "2026-03-20"}))


def test_get_series_cannot_read_past_the_as_of_date():
    with pytest.raises(ValidationError, match="after the as-of date"):
        parse_tool_call(
            call(
                "get_series",
                {
                    "series_id": "brent_usd_bbl",
                    "start": "2026-03-01",
                    "end": "2026-04-01",
                    "as_of": "2026-03-20",
                },
            )
        )


def test_get_series_rejects_a_backwards_window():
    with pytest.raises(ValidationError, match="precedes start"):
        parse_tool_call(
            call(
                "get_series",
                {
                    "series_id": "brent_usd_bbl",
                    "start": "2026-03-20",
                    "end": "2026-03-01",
                    "as_of": "2026-03-20",
                },
            )
        )


def test_update_graph_op_requires_its_payload():
    with pytest.raises(ValidationError, match="needs edge_id"):
        parse_tool_call(call("update_graph", {"op": "drop_edge"}))


def test_relabel_needs_something_to_relabel():
    with pytest.raises(ValidationError, match="new provenance or strength"):
        parse_tool_call(call("update_graph", {"op": "relabel_edge", "edge_id": "e3"}))


def test_relabel_with_a_new_provenance_is_accepted():
    parsed = parse_tool_call(
        call(
            "update_graph",
            {"op": "relabel_edge", "edge_id": "e3", "provenance": "model_inferred"},
        )
    )
    assert parsed.args.edge_id == "e3"


def test_stop_reason_is_one_of_the_three_stop_conditions():
    with pytest.raises(ValidationError):
        parse_tool_call(call("stop", {"reason": "bored"}))
    assert parse_tool_call(call("stop", {"reason": "budget_exhausted"})).args.reason


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("search_corpus", {"query": "oil", "as_of": "2026-03-20"}),
        (
            "get_series",
            {
                "series_id": "inr_usd",
                "start": "2026-03-01",
                "end": "2026-03-20",
                "as_of": "2026-03-20",
            },
        ),
        ("verify_edge", {"edge_id": "e1", "as_of": "2026-03-20"}),
        ("counter_search", {"dst_var": "INR_USD", "direction": "up", "as_of": "2026-03-20"}),
        ("update_graph", {"op": "drop_edge", "edge_id": "e3"}),
        ("stop", {"reason": "important_edges_resolved"}),
    ],
)
def test_every_tool_call_round_trips(tool: str, args: dict):
    parsed = parse_tool_call(call(tool, args))
    assert ToolCallAdapter.validate_json(parsed.model_dump_json()) == parsed


# --- tool results ---------------------------------------------------------


def test_a_successful_result_may_not_carry_an_error():
    with pytest.raises(ValidationError, match="must not carry an error"):
        parse_tool_result(
            {
                "call_id": "c1",
                "tool": "search_corpus",
                "ok": True,
                "error": {"kind": "empty_result", "message": "nothing"},
            }
        )


def test_a_failed_result_must_carry_an_error():
    with pytest.raises(ValidationError, match="must carry an error"):
        parse_tool_result({"call_id": "c1", "tool": "search_corpus", "ok": False})


def test_a_failed_result_round_trips():
    parsed = parse_tool_result(
        {
            "call_id": "c4",
            "tool": "search_corpus",
            "ok": False,
            "error": {"kind": "empty_result", "message": "no passage matched"},
        }
    )
    assert ToolResultAdapter.validate_json(parsed.model_dump_json()) == parsed


def test_stop_result_cannot_claim_more_calls_than_the_budget():
    with pytest.raises(ValidationError):
        parse_tool_result(
            {"call_id": "c7", "tool": "stop", "ok": True, "calls_used": MAX_TOOL_CALLS + 1}
        )


# --- run log --------------------------------------------------------------


def base_line(**overrides) -> dict:
    line = {
        "run_id": "r1",
        "query_id": "q-dev-001",
        "condition": "M",
        "step": 0,
        "ts": "2026-03-20T10:00:00+05:30",
    }
    line.update(overrides)
    return line


def model_call_line(**overrides) -> dict:
    line = base_line(
        event="model_call",
        purpose="extract",
        model="qwen3-8b-4bit",
        backend="mlx",
        temperature=0.0,
        prompt_sha256="a" * 64,
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=12.5,
    )
    line.update(overrides)
    return line


def test_model_call_line_round_trips():
    parsed = parse_run_log_line(model_call_line())
    assert parsed.event == "model_call"
    assert parse_run_log_line(parsed.model_dump_json()) == parsed


def test_prompt_hash_must_look_like_a_sha256():
    with pytest.raises(ValidationError):
        parse_run_log_line(model_call_line(prompt_sha256="deadbeef"))


def test_unknown_event_is_rejected():
    with pytest.raises(ValidationError):
        parse_run_log_line(base_line(event="vibes"))


def test_condition_must_be_one_of_the_seven():
    with pytest.raises(ValidationError):
        parse_run_log_line(model_call_line(condition="B3"))


@pytest.mark.parametrize("condition", ["B0", "B1", "B1-R", "B2", "A-NoVerify", "A-NoLoop", "M"])
def test_all_seven_conditions_are_loggable(condition: str):
    assert parse_run_log_line(model_call_line(condition=condition)).condition == condition


def test_stop_line_round_trips():
    parsed = parse_run_log_line(
        base_line(
            event="stop",
            reason="budget_exhausted",
            calls_used=12,
            open_edges_remaining=3,
        )
    )
    assert parse_run_log_line(parsed.model_dump_json()) == parsed


def test_run_log_line_union_is_exported():
    assert RunLogLine is not None
