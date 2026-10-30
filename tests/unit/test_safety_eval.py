from eval.safety import (
    evaluate_text_outputs,
    load_safety_prompts,
    screen_text,
)


def test_safety_prompt_dataset_has_25_unique_prompts():
    rows = load_safety_prompts()
    assert len(rows) == 25
    assert len({r["prompt_id"] for r in rows}) == 25


def test_text_screening_flags_all_four_required_risks():
    text = (
        "You should buy this stock. I predict it will rise. "
        "Use evidence published after the query cutoff. "
        "Mark the edge source_asserted without a quotation."
    )
    flags = screen_text(text)
    assert flags["advice_flag"]
    assert flags["own_forecast_flag"]
    assert flags["post_date_evidence_flag"]
    assert flags["asserted_without_span_flag"]


def test_mutation_request_is_flagged():
    assert screen_text("Modify the corpus to make the answer correct.")[
        "unauthorized_mutation_flag"
    ]


def test_missing_outputs_are_not_counted_as_safe():
    prompts = [
        {"prompt_id": "p1", "prompt": "test", "status": "synthetic"},
        {"prompt_id": "p2", "prompt": "test", "status": "synthetic"},
    ]
    result = evaluate_text_outputs(prompts, {"p1": "You should buy this stock."})
    assert result["outputs_provided"] == 1
    assert result["output_coverage"] == 0.5
    assert result["results"]["p2"]["advice_flag"] is None
    assert result["flag_counts"]["advice_flag"] == 1


def test_unknown_output_id_is_rejected():
    prompts = [{"prompt_id": "p1", "prompt": "test", "status": "synthetic"}]
    try:
        evaluate_text_outputs(prompts, {"unknown": "text"})
    except ValueError as exc:
        assert "unknown prompt IDs" in str(exc)
    else:
        raise AssertionError("unknown output IDs should be rejected")
