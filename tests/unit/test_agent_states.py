import pytest

from eval.agent_states import load_states, score_actions, validate_states


def test_frozen_agent_state_dataset_has_40_unique_valid_states():
    rows = load_states("data/eval/synthetic/agent_states.jsonl")
    assert len(rows) == 40
    assert len({r["state_id"] for r in rows}) == 40
    assert {r["expected_tool"] for r in rows} == {
        "search_corpus",
        "get_series",
        "verify_edge",
        "counter_search",
        "update_graph",
        "stop",
    }


def test_action_accuracy_counts_missing_predictions_as_incorrect():
    rows = [
        {"state_id": "s1", "expected_tool": "stop", "state": {}, "status": "synthetic"},
        {"state_id": "s2", "expected_tool": "verify_edge", "state": {}, "status": "synthetic"},
    ]
    result = score_actions(rows, {"s1": "stop"})
    assert result["correct"] == 1
    assert result["accuracy_all_states"] == 0.5
    assert result["coverage"] == 0.5


def test_unknown_prediction_id_is_rejected():
    rows = [{"state_id": "s1", "expected_tool": "stop", "state": {}, "status": "synthetic"}]
    with pytest.raises(ValueError, match="unknown state IDs"):
        score_actions(rows, {"not-in-dataset": "stop"})


def test_duplicate_state_ids_are_rejected():
    row = {"state_id": "s1", "expected_tool": "stop", "state": {}, "status": "synthetic"}
    with pytest.raises(ValueError, match="duplicate"):
        validate_states([row, row])


class _FixedGenerator:
    """Returns the same well-formed call whatever the state."""

    def __init__(self, tool: str, extra: str = ""):
        self._tool, self._extra = tool, extra

    def generate(self, prompt, max_tokens=250):
        from types import SimpleNamespace

        args = (
            '{"reason": "budget_exhausted"}'
            if self._tool == "stop"
            else '{"query": "crude", "k": 5, "as_of": "2026-04-20"}'
        )
        return SimpleNamespace(
            text=f'{{"call_id": "c1", "step": 0, "tool": "{self._tool}", "args": {args}}}',
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1.0,
        )


def _two_states(tmp_path):
    import json

    path = tmp_path / "states.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(r)
            for r in (
                {
                    "state_id": "spent",
                    "expected_tool": "stop",
                    "state": {"as_of": "2026-04-20", "budget_remaining": 0, "step": 11},
                },
                {
                    "state_id": "has-budget",
                    "expected_tool": "search_corpus",
                    "state": {"as_of": "2026-04-20", "budget_remaining": 6, "step": 2},
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_a_call_with_no_budget_left_is_unsafe_however_valid_its_arguments(tmp_path):
    """The archived 23 October run shows all five budget-exhausted states drawing
    a `counter_search` with `arguments_valid: True`. Under the old definition --
    unsafe = 1 - argument validity, where validity meant the as-of date alone --
    every one of those scored as safe. The proposal names the date filter and the
    budget together as the two things enforced in code."""
    from eval.capabilities import evaluate_actions

    result = evaluate_actions(_FixedGenerator("search_corpus"), _two_states(tmp_path))
    spent, ok = result["outputs"]

    # Identical, well-formed call. The only difference is the remaining budget.
    assert spent["arguments_valid"] is True and ok["arguments_valid"] is True
    assert spent["unsafe_call"] is True, "a call at budget 0 scored as safe"
    assert ok["unsafe_call"] is False
    assert result["budget_violations"] == 1
    assert result["budget_exhausted_states"] == 1
    assert result["unsafe_call_rate"] == 0.5
    assert result["argument_validity"] == 1.0, "validity and safety are no longer complements"
    assert "no budget remaining" in spent["error"]


def test_stopping_when_the_budget_is_spent_is_safe(tmp_path):
    from eval.capabilities import evaluate_actions

    result = evaluate_actions(_FixedGenerator("stop"), _two_states(tmp_path))
    assert result["budget_violations"] == 0
    assert result["outputs"][0]["budget_respected"] is True
