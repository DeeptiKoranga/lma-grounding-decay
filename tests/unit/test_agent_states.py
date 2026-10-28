from eval.agent_states import load_states, score_actions, validate_states
import pytest


def test_frozen_agent_state_dataset_has_40_unique_valid_states():
    rows = load_states("data/eval/synthetic/agent_states.jsonl")
    assert len(rows) == 40
    assert len({r["state_id"] for r in rows}) == 40
    assert {r["expected_tool"] for r in rows} == {
        "search_corpus", "get_series", "verify_edge",
        "counter_search", "update_graph", "stop",
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
    rows = [
        {"state_id": "s1", "expected_tool": "stop", "state": {}, "status": "synthetic"}
    ]
    with pytest.raises(ValueError, match="unknown state IDs"):
        score_actions(rows, {"not-in-dataset": "stop"})


def test_duplicate_state_ids_are_rejected():
    row = {"state_id": "s1", "expected_tool": "stop", "state": {}, "status": "synthetic"}
    with pytest.raises(ValueError, match="duplicate"):
        validate_states([row, row])
