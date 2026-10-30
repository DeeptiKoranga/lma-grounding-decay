"""C2 measures the application schemas and rejects invalid project claims."""

import json
from collections import Counter

from eval.model_pilot import build_cases, score
from extract.candidates import Extraction
from schema import Strength


def test_project_pilot_is_frozen_balanced_and_uses_real_strength_labels():
    cases = build_cases()
    assert len(cases) == len({c["id"] for c in cases}) == 100
    assert set(Counter(c["task"] for c in cases).values()) == {20}
    labels = {c["gold"]["strength"] for c in cases if c["task"] == "strength"}
    assert labels == {s.value for s in Strength}
    for case in cases:
        if case["task"] in {"extraction", "json_validity"}:
            Extraction.model_validate(case["gold"])
            assert score(case, json.dumps(case["gold"]))["score"] == 1


def test_extraction_rejects_invented_quotes_and_schema_validity_is_separate():
    case = build_cases()[0]
    wrong = json.loads(json.dumps(case["gold"]))
    wrong["edges"][0]["evidence_span"] = "not in the source"
    scored = score(case, json.dumps(wrong))
    assert scored["schema_valid"] and scored["score"] == 0
    wrong["edges"][0]["src_var"] = "UNKNOWN_VARIABLE"
    assert not score(case, json.dumps(wrong))["schema_valid"]


def test_tool_score_rejects_a_changed_cutoff_and_unsupported_schema():
    case = next(
        c for c in build_cases() if c["task"] == "tool_choice" and c["gold"]["tool"] == "get_series"
    )
    call = {
        "tool": "get_series",
        "call_id": "c",
        "step": 0,
        "args": {
            "series_id": "inr_usd",
            "start": "2026-03-02",
            "end": "2026-03-10",
            "as_of": "2026-03-20",
        },
    }
    assert score(case, json.dumps(call))["score"] == 1
    call["args"]["as_of"] = "2026-04-20"
    assert score(case, json.dumps(call))["score"] == 0
    assert not score(case, '{"tool":"unknown"}')["schema_valid"]
