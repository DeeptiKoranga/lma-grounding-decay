"""The agentic capability metrics over synthetic run logs.

`runs/**` is gitignored, so these build their own lines. The point is the
pairing rule: a `tool_result` carries no tool name, so a redundant search can
only be counted by matching the result back to the call that preceded it. Get
that wrong and `verify_edge` results start counting as redundant searches.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "report_agent_metrics", REPO / "scripts/report_agent_metrics.py"
)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


def _call(step, tool, condition="M", query_id="q1", run_id="r1"):
    return {
        "event": "tool_call",
        "run_id": run_id,
        "query_id": query_id,
        "condition": condition,
        "step": step,
        "call": {"tool": tool},
    }


def _result(step, new_passages, condition="M", query_id="q1", run_id="r1"):
    return {
        "event": "tool_result",
        "run_id": run_id,
        "query_id": query_id,
        "condition": condition,
        "step": step,
        "new_passages": new_passages,
    }


def test_a_search_that_adds_nothing_is_redundant():
    report = module.summarise([_call(0, "search_corpus"), _result(0, 0)])
    assert report["M"]["searches"] == 1
    assert report["M"]["redundant_searches"] == 1
    assert report["M"]["redundant_search_rate"] == 1.0


def test_a_search_that_adds_a_passage_is_not():
    report = module.summarise([_call(0, "search_corpus"), _result(0, 3)])
    assert report["M"]["redundant_searches"] == 0
    assert report["M"]["redundant_search_rate"] == 0.0


def test_a_verify_result_is_never_a_redundant_search():
    """verify_edge re-reads passages the run already holds, so new_passages is 0
    by construction. Counting it would inflate the rate with every verification."""
    report = module.summarise([_call(0, "verify_edge"), _result(0, 0)])
    assert report["M"]["searches"] == 0
    assert report["M"]["redundant_searches"] == 0
    assert report["M"]["redundant_search_rate"] is None


def test_counter_search_counts_as_a_search():
    report = module.summarise([_call(0, "counter_search"), _result(0, 0)])
    assert report["M"]["searches"] == 1
    assert report["M"]["redundant_searches"] == 1


def test_results_pair_with_their_own_call_across_interleaved_steps():
    lines = [
        _call(0, "search_corpus"),
        _call(1, "verify_edge"),
        _result(1, 0),  # verification, not a redundant search
        _result(0, 0),  # the search, which was redundant
    ]
    report = module.summarise(lines)
    assert report["M"]["searches"] == 1
    assert report["M"]["redundant_searches"] == 1


def test_results_do_not_pair_across_runs_at_the_same_step():
    lines = [
        _call(0, "search_corpus", run_id="r1"),
        _call(0, "verify_edge", run_id="r2"),
        _result(0, 0, run_id="r2"),
        _result(0, 4, run_id="r1"),
    ]
    report = module.summarise(lines)
    assert report["M"]["redundant_searches"] == 0, "r2's verify result consumed r1's search"


def test_tool_calls_are_counted_per_query_not_pooled():
    lines = [
        _call(0, "search_corpus", query_id="q1"),
        _call(1, "search_corpus", query_id="q1"),
        _call(0, "search_corpus", query_id="q2"),
    ]
    report = module.summarise(lines)["M"]
    assert report["queries"] == 2
    assert report["tool_calls_total"] == 3
    assert report["tool_calls_per_query_mean"] == 1.5
    assert report["tool_calls_per_query_max"] == 2


def test_open_edges_at_stop_are_reported_with_their_reason():
    lines = [
        {
            "event": "stop",
            "run_id": "r1",
            "query_id": "q1",
            "condition": "M",
            "step": 9,
            "reason": "budget_exhausted",
            "open_edges_remaining": 3,
        },
        {
            "event": "stop",
            "run_id": "r2",
            "query_id": "q2",
            "condition": "M",
            "step": 4,
            "reason": "important_edges_resolved",
            "open_edges_remaining": 0,
        },
    ]
    report = module.summarise(lines)["M"]
    assert report["stops"] == 2
    assert report["stops_with_open_edges"] == 1
    assert report["open_edges_at_stop_total"] == 3
    assert report["stop_reasons"] == {"budget_exhausted": 1, "important_edges_resolved": 1}


def test_conditions_are_kept_apart():
    lines = [
        _call(0, "search_corpus", condition="M"),
        _result(0, 0, condition="M"),
        _call(0, "search_corpus", condition="B1", query_id="q9", run_id="r9"),
        _result(0, 5, condition="B1", query_id="q9", run_id="r9"),
    ]
    report = module.summarise(lines)
    assert report["M"]["redundant_search_rate"] == 1.0
    assert report["B1"]["redundant_search_rate"] is None


def test_a_condition_that_never_searches_has_an_undefined_rate_not_zero():
    """A-NoLoop retrieves once outside the loop. Reporting 0.0 would read as
    'never redundant', which is a claim the data does not make."""
    report = module.summarise([_call(0, "update_graph", condition="A-NoLoop")])
    assert report["A-NoLoop"]["redundant_search_rate"] is None


@pytest.mark.parametrize("condition", ["A-NoLoop", "B0", "B1", "B1-R", "B2"])
def test_initial_retrieval_does_not_create_a_loop_redundancy_rate(condition):
    report = module.summarise(
        [
            _call(0, "search_corpus", condition=condition),
            _result(0, 3, condition=condition),
        ]
    )
    assert report[condition]["searches"] == 1
    assert report[condition]["redundant_search_rate"] is None


def test_zero_call_queries_are_included_in_call_mean():
    report = module.summarise(
        [
            _call(0, "search_corpus", query_id="q1"),
            {
                "event": "stop",
                "condition": "M",
                "query_id": "q2",
                "reason": "important_edges_resolved",
                "open_edges_remaining": 0,
            },
        ]
    )
    assert report["M"]["tool_calls_per_query_mean"] == 0.5


def test_the_renderer_states_the_undefined_rate_rather_than_printing_none():
    text = module.render(module.summarise([_call(0, "update_graph")]), Path("runs/x"))
    assert "n/a" in text
    assert "None" not in text


def test_loader_ignores_orphan_logs(tmp_path, monkeypatch):
    from eval import run_audit

    monkeypatch.setattr(run_audit, "audit", lambda **_: {"complete": True})
    condition = tmp_path / "M"
    condition.mkdir()
    (condition / "q.json").write_text('{"graph": {}, "log_file": "bound.jsonl"}')
    (condition / "bound.jsonl").write_text('{"event": "bound"}\n')
    (condition / "orphan.jsonl").write_text('{"event": "orphan"}\n')
    assert module._lines(tmp_path) == [{"event": "bound"}]


@pytest.mark.parametrize("tool", list(module.SEARCH_TOOLS))
def test_every_declared_search_tool_is_one_the_agent_actually_has(tool):
    from schema.enums import ToolName

    assert tool in {t.value for t in ToolName}
