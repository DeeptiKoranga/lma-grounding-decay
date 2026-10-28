"""The challenge set and its rules-only arm (B9 #20, #40).

The load-bearing assertion here is a *negative* one: two of the five corruption
families must NOT be caught by the rule layer. If a rule ever caught a reversed
relation or an inflated strength label, it would be doing something it does not
claim to do, and the argument for the semantic verifier - which rests on that
blind spot - would be resting on nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.run_challenge import RULE_VISIBLE, score

from eval.challenge import CORRUPTIONS, MIN_INFLATABLE_SEEDS, MIN_SEEDS, build
from eval.gold import load_gold_graph
from schema import Passage

REPO = Path(__file__).parents[2]
ITEMS = REPO / "data/eval/challenge.jsonl"
CORPUS = REPO / "data/processed/articles.jsonl"
DEV_QUERIES = ["dev-oil-why", "dev-oil-effects", "dev-rupee-why", "dev-rupee-effects"]

needs_corpus = pytest.mark.skipif(not CORPUS.is_file(), reason="corpus payload is not in git")
needs_items = pytest.mark.skipif(not ITEMS.is_file(), reason="challenge set not built")


@pytest.fixture
def items():
    return [json.loads(line) for line in ITEMS.read_text().splitlines() if line.strip()]


@pytest.fixture
def passages():
    return {
        p.passage_id: p
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
        if (p := Passage.model_validate_json(line))
    }


# ---------------------------------------------------------------------------
# The set itself
# ---------------------------------------------------------------------------


@needs_items
def test_no_row_claims_a_reviewed_corruption_label(items):
    """The builder proposes corruptions; it never certifies them."""
    assert items
    for row in items:
        assert row["human_reviewed"] is False
        assert row["expected_supported"] is None


@needs_items
def test_every_corruption_family_is_present_with_its_own_denominator(items):
    counts: dict[str, int] = {}
    for row in items:
        counts[row["proposed_corruption"] or "control"] = (
            counts.get(row["proposed_corruption"] or "control", 0) + 1
        )
    assert set(counts) == {"control", *CORRUPTIONS}
    assert counts["control"] >= MIN_SEEDS
    assert counts["inflated_strength"] >= MIN_INFLATABLE_SEEDS
    # Uneven by construction (D-21): fewer hedged gold links than seeds.
    assert counts["inflated_strength"] < counts["control"]


@needs_items
def test_the_set_records_that_the_gold_behind_it_is_not_adjudicated(items):
    """When this flips to True the false-alarm rate becomes trustworthy, and
    that is a change worth noticing in a diff."""
    assert all(row["gold_adjudicated"] is False for row in items)


@needs_corpus
def test_building_refuses_a_gold_set_too_small_to_be_worth_quoting(tmp_path):
    folder = tmp_path / "gold"
    folder.mkdir()
    one = load_gold_graph(DEV_QUERIES[2])  # the four-edge graph
    (folder / f"{one.query_id}.json").write_text(one.model_dump_json(indent=2, exclude_none=True))
    with pytest.raises(ValueError, match=f"at least {MIN_SEEDS} eligible"):
        build(
            gold=folder,
            corpus=CORPUS,
            output=tmp_path / "challenge.jsonl",
            allow_unreviewed=True,
        )


@needs_corpus
def test_unreviewed_gold_needs_the_flag(tmp_path):
    """Without it the receipt gate applies, and the dev receipt is unsigned."""
    with pytest.raises(ValueError, match="attestation"):
        build(
            gold=REPO / "data/eval/gold/dev",
            corpus=CORPUS,
            output=tmp_path / "challenge.jsonl",
        )


# ---------------------------------------------------------------------------
# The rules-only arm, and what it must not catch
# ---------------------------------------------------------------------------


@needs_items
@needs_corpus
def test_the_rule_layer_catches_every_citation_corruption(items, passages):
    results = score(items, passages)
    for kind in RULE_VISIBLE:
        row = results[kind]
        assert row["flagged"] == row["total"], f"{kind}: {row['flagged']}/{row['total']}"


@needs_items
@needs_corpus
def test_the_rule_layer_raises_no_false_alarm_on_the_clean_controls(items, passages):
    control = score(items, passages)["control"]
    assert control["flagged"] == 0, "a clean gold edge was flagged; the rules or the gold is wrong"


@needs_items
@needs_corpus
def test_the_rule_layer_cannot_see_a_reversed_relation(items, passages):
    """Swapping source and destination leaves both variables in the same
    passage with the same verbatim span, so all four rules pass. The semantic
    verifier exists for this."""
    row = score(items, passages)["reversed_relation"]
    assert row["total"] > 0
    assert row["flagged"] == 0


@needs_items
@needs_corpus
def test_the_rule_layer_cannot_see_an_inflated_strength_label(items, passages):
    """No rule reads `strength`. If this ever starts failing, a rule has grown
    a capability it does not document."""
    row = score(items, passages)["inflated_strength"]
    assert row["total"] > 0
    assert row["flagged"] == 0


@needs_items
@needs_corpus
def test_a_third_of_the_corruptions_need_a_model(items, passages):
    """The headline justification for the verifier, pinned so it cannot drift
    unnoticed into a claim the data stopped supporting."""
    results = score(items, passages)
    blind = sum(results[k]["total"] for k in CORRUPTIONS if k not in RULE_VISIBLE and k in results)
    total = sum(results[k]["total"] for k in CORRUPTIONS if k in results)
    assert 0.2 < blind / total < 0.5
