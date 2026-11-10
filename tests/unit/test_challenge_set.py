"""The challenge set and its rules-only arm (B9 #20, #40).

The load-bearing assertion here is a *negative* one: two of the five corruption
families must NOT be caught by the rule layer. If a rule ever caught a reversed
relation or an inflated strength label, it would be doing something it does not
claim to do, and the argument for the semantic verifier - which rests on that
blind spot - would be resting on nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from scripts.run_challenge import RULE_VISIBLE, score

from eval.challenge import CORRUPTIONS, MIN_INFLATABLE_SEEDS, MIN_SEEDS, build
from eval.gold import load_gold_graph
from eval.references import prepare
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
def test_the_set_records_the_adjudicated_gold_it_was_built_from(items):
    """The false-alarm rate over controls is only trustworthy when the gold set
    behind it was signed for, so every row carries that status and the receipt
    hash it was built against. This flipped False -> True on 8 Nov 2026 when the
    reviewers signed (D-26); it is a change worth noticing in a diff either way."""
    assert all(row["gold_adjudicated"] is True for row in items)
    receipts = {row["reference_review_receipt_sha256"] for row in items}
    assert len(receipts) == 1, "one build, one receipt"
    assert re.fullmatch(
        r"[0-9a-f]{64}", receipts.pop()
    ), "an adjudicated set must name the receipt its controls rest on"


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
def test_unsigned_gold_needs_the_flag(tmp_path):
    """The receipt gate is what stops an unsigned gold set producing a quotable
    false-alarm rate. The real dev receipt is signed now, so this builds the
    unsigned case rather than relying on the repository being in that state -
    otherwise signing the receipt would have quietly deleted the test.
    """
    folder = tmp_path / "gold"
    folder.mkdir()
    for query_id in DEV_QUERIES:
        graph = load_gold_graph(query_id)
        (folder / f"{query_id}.json").write_text(graph.model_dump_json(indent=2, exclude_none=True))
    prepare(references=folder, corpus=CORPUS)  # writes a blank, unsigned receipt
    receipt = json.loads((folder / "review_receipt.json").read_text())
    assert receipt["reviewer"] == "" and receipt["independent_review"] is False

    with pytest.raises(ValueError, match="attestation"):
        build(gold=folder, corpus=CORPUS, output=tmp_path / "challenge.jsonl")

    # ...and with the flag it builds, but says what it is standing on.
    manifest = build(
        gold=folder,
        corpus=CORPUS,
        output=tmp_path / "unsigned.jsonl",
        allow_unreviewed=True,
    )
    assert manifest["gold_adjudicated"] is False
    assert manifest["reference_review_receipt_sha256"] is None
    assert (
        "do not quote it" in manifest["reading"]
    ), "an unsigned build must say so where the rates are read, not only in a flag"


@needs_corpus
def test_a_signed_receipt_stops_matching_once_gold_changes(tmp_path):
    """The receipt binds to the gold bytes, so an edit after signing invalidates
    it. Without this a reviewer could sign, then the set could drift underneath
    the signature."""
    folder = tmp_path / "gold"
    folder.mkdir()
    for query_id in DEV_QUERIES:
        graph = load_gold_graph(query_id)
        (folder / f"{query_id}.json").write_text(graph.model_dump_json(indent=2, exclude_none=True))
    prepare(references=folder, corpus=CORPUS)
    path = folder / "review_receipt.json"
    receipt = json.loads(path.read_text())
    receipt.update(
        reviewer="A Reviewer",
        reviewed_on="2026-11-08",
        independent_review=True,
        all_relations_and_strengths_reviewed=True,
    )
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    build(gold=folder, corpus=CORPUS, output=tmp_path / "signed.jsonl")  # accepted

    changed = folder / f"{DEV_QUERIES[0]}.json"
    graph = json.loads(changed.read_text())
    graph["notes"] = (graph.get("notes") or "") + " edited after signing"
    changed.write_text(json.dumps(graph, indent=2) + "\n")
    with pytest.raises(ValueError, match="changed after their review receipt"):
        build(gold=folder, corpus=CORPUS, output=tmp_path / "after.jsonl")


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


def test_several_gold_directories_still_bind_to_one_receipt_hash():
    """The manifest's receipt field is what makes the false-alarm rate quotable,
    and several callers read it as a single hash. Building from both halves must
    not empty it; it becomes a digest over the receipts, which still changes if
    any one of them does."""
    import hashlib
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo / "data/eval/challenge_manifest.json").read_text(encoding="utf-8"))
    receipts = manifest["reference_review_receipts"]
    assert len(receipts) > 1, "this set is built from both halves"
    joined = "\n".join(f"{name}:{value}" for name, value in sorted(receipts.items()))
    assert (
        manifest["reference_review_receipt_sha256"]
        == hashlib.sha256(joined.encode("utf-8")).hexdigest()
    )


def test_the_set_reaches_the_size_the_proposal_specifies():
    """89 items from the dev half alone fell short of the proposal's 125. Both
    halves clear it. A drop below 125 means a gold directory stopped being
    included, which would be silent otherwise."""
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo / "data/eval/challenge_manifest.json").read_text(encoding="utf-8"))
    assert manifest["items"] >= 125
    assert len(manifest["gold_directories"]) == 2


def test_a_query_id_in_two_gold_directories_is_refused():
    """Silently overwriting one half's graph with another's would change the
    seed set without changing the item count."""
    from pathlib import Path
    from unittest.mock import patch

    from eval import challenge

    clash = ({"q1": object()}, "aa" * 32)
    with (
        patch.object(challenge, "validate", return_value=clash),
        pytest.raises(ValueError, match="more than one gold directory"),
    ):
        challenge.build(
            gold=[Path("a"), Path("b")],
            corpus=Path("data/processed/articles.jsonl"),
            output=Path("/tmp/unused-challenge.jsonl"),
        )
