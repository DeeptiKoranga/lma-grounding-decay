"""Agreement edge cases and optional backend boundaries remain explicit."""

import pytest

from eval.agreement import kappa, strength_agreement
from eval.figures import uer_figure
from llm.generate import ChatCompletionsGenerator, json_object


def test_kappa_reports_undefined_constant_labels_and_expected_disagreement():
    assert kappa({"a": "x", "b": "x"}, {"a": "x", "b": "x"})["kappa"] is None
    assert kappa({"a": "x", "b": "y"}, {"a": "y", "b": "x"})["kappa"] == -1
    assert kappa({"a": "x", "b": "y"}, {"a": "x", "b": "y"})["kappa"] == 1
    with pytest.raises(ValueError):
        kappa({"a": "x"}, {"b": "x"})


def test_strength_collapse_is_triggered_only_by_the_predeclared_threshold():
    result = strength_agreement(
        {"a": "direct", "b": "conditional", "c": "correlational"},
        {"a": "conditional", "b": "correlational", "c": "direct"},
    )
    assert result["collapse_triggered"]
    assert "direct_vs_hedged" in result
    with pytest.raises(ValueError):
        strength_agreement({"a": "strong"}, {"a": "direct"})


def test_remote_model_calls_are_never_an_automatic_paid_fallback():
    with pytest.raises(ValueError, match="authorization"):
        ChatCompletionsGenerator(base_url="https://example.org/v1", model="any")
    local = ChatCompletionsGenerator(base_url="http://127.0.0.1:8000/v1", model="local")
    assert local.url == "http://127.0.0.1:8000/v1/chat/completions"


@pytest.mark.parametrize("text", ['prefix {"edges":[]}', "[1,2]", "not JSON"])
def test_prose_or_arrays_cannot_be_silently_accepted_as_constrained_json(text):
    with pytest.raises(ValueError):
        json_object(text)


def test_reviewed_uer_cannot_be_drawn_from_unreviewed_or_missing_results(tmp_path):
    with pytest.raises(ValueError, match="independent"):
        uer_figure({"status": "development_unreviewed"}, tmp_path / "false.png")
    assert not (tmp_path / "false.png").exists()
