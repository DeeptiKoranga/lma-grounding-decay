"""Model-output validation fixtures; no fixture is a human evidence judgment."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from retrieval.automated_review import MODEL, REVISION, parse_labels, plan, prompt_for, run


def packet(passages):
    return {
        "queries": [
            {
                "query_id": "fixture-query",
                "query": "How were oil costs related to the rupee?",
                "as_of": "2026-03-31",
            }
        ],
        "candidates": [
            {"query_id": "fixture-query", "passage": p.model_dump(mode="json")}
            for p in passages[:2]
        ],
    }


def test_explicit_complete_decisions_keep_exact_positive_spans(passages):
    batch = plan(packet(passages))[0]
    span = batch["candidates"][0]["passage"]["text"][:45]
    rows = parse_labels(json.dumps([[0, "y", span], [1, "n", ""]]), batch)
    assert rows[0]["decision"] == "relevant" and rows[0]["evidence_span"] == span
    assert rows[1]["decision"] == "irrelevant" and rows[1]["evidence_span"] is None
    assert "independent_review" not in rows[0] and "reviewer" not in rows[0]


@pytest.mark.parametrize(
    "value",
    [
        [],
        [[0, "n", ""]],
        [[0, "n", ""], [0, "n", ""]],
        [[False, "n", ""], [1, "n", ""]],
        [[0, "unknown", ""], [1, "n", ""]],
        [[0, "n", "invented quote"], [1, "n", ""]],
    ],
)
def test_omissions_duplicates_wrong_types_and_invalid_negative_spans_are_not_negatives(
    passages, value
):
    with pytest.raises(ValueError):
        parse_labels(json.dumps(value), plan(packet(passages))[0])


def test_nonverbatim_positive_is_uncertain_instead_of_accepted(passages):
    rows = parse_labels(
        '[[0,"y","invented source wording"],[1,"u","not enough context"]]',
        plan(packet(passages))[0],
    )
    assert all(row["decision"] == "uncertain" and row["evidence_span"] is None for row in rows)


def test_batching_keeps_every_whole_passage_and_hides_ranking_fields(passages):
    p = packet(passages)
    p["scores"] = [100, 1]
    p["seed_labels"] = [True, False]
    batches = plan(p, size=1)
    assert len(batches) == 2
    assert [b["candidates"][0]["passage"]["text"] for b in batches] == [
        x.text for x in passages[:2]
    ]
    prompt = prompt_for(batches[0])
    assert "scores" not in prompt and "seed_labels" not in prompt
    p["candidates"][0]["passage"]["published_at"] = "2026-04-01T00:00:00+05:30"
    with pytest.raises(ValueError, match="after query cutoff"):
        plan(p)


def test_resume_is_input_bound_and_never_writes_human_review_files(passages, tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("fixture corpus")
    from retrieval.automated_review import digest

    data = {**packet(passages), "corpus_sha256": digest(corpus)}
    p = tmp_path / "packet.json"
    p.write_text(json.dumps(data))
    calls = []

    class FixtureGenerator:
        def generate(self, prompt, **_):
            calls.append(prompt)
            return SimpleNamespace(
                text='[[0,"n",""],[1,"u","fixture uncertainty"]]',
                model=MODEL + "@" + REVISION,
                backend="mlx",
                prompt_tokens=10,
                completion_tokens=10,
                latency_ms=5,
            )

    output = tmp_path / "machine"
    kwargs = {
        "packet_path": p,
        "corpus": corpus,
        "output": output,
        "model_path": Path("unused"),
        "generator": FixtureGenerator(),
    }
    result = run(**kwargs)
    assert result["complete"] and result["items_classified"] == 2
    assert not result["independent_human_review"] and not result["research_acceptance"]
    run(**kwargs)
    assert len(calls) == 1
    assert not (output / "judgments.json").exists() and not (output / "receipt.json").exists()
    with pytest.raises(ValueError, match="unchanged"):
        run(**{**kwargs, "batch_size": 1})
