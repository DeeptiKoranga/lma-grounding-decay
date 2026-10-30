"""B10 - the public-data strength checks.

The mapping test is the load-bearing one. Yu et al.'s label 1 is *direct* and 3
is *correlational*, which is the reverse of the order a reader expects, and
getting it backwards would invert every number in the report while leaving it
looking entirely plausible.
"""

from __future__ import annotations

import pytest

from eval.strength_bench import (
    YU_EXPECTED_COUNTS,
    YU_LABEL_TO_STRENGTH,
    cue_strength,
    score,
    yu_strength,
)
from schema import Strength

# ---------------------------------------------------------------------------
# The label mapping
# ---------------------------------------------------------------------------


def test_yu_label_one_is_direct_and_three_is_correlational():
    """Not the intuitive order. Pinned because inverting it is invisible."""
    assert yu_strength(1) is Strength.DIRECT
    assert yu_strength(2) is Strength.CONDITIONAL
    assert yu_strength(3) is Strength.CORRELATIONAL


def test_no_relationship_has_no_strength():
    assert yu_strength(0) is None


def test_the_mapping_covers_every_strength_exactly_once():
    assert set(YU_LABEL_TO_STRENGTH.values()) == set(Strength)
    assert len(YU_LABEL_TO_STRENGTH) == len(Strength)


def test_the_published_counts_are_recorded_so_a_rerelease_is_caught():
    assert YU_EXPECTED_COUNTS == {0: 1356, 1: 494, 2: 213, 3: 998}
    assert sum(YU_EXPECTED_COUNTS.values()) == 3061


@pytest.mark.parametrize("label", ["1", "2", "3"])
def test_string_labels_are_accepted(label):
    assert yu_strength(label) is yu_strength(int(label))


# ---------------------------------------------------------------------------
# The cue baseline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("The rupee fell due to the surge in crude prices.", Strength.DIRECT),
        ("Higher fuel costs drove the increase in the import bill.", Strength.DIRECT),
        ("The move could raise imported inflation later this year.", Strength.CONDITIONAL),
        ("Yields may rise if the MPC tightens further.", Strength.CONDITIONAL),
        ("The rupee weakened amid a broad dollar rally.", Strength.CORRELATIONAL),
        ("Bond yields were associated with foreign outflows.", Strength.CORRELATIONAL),
    ],
)
def test_the_cue_lists_classify_their_own_examples(sentence, expected):
    assert cue_strength(sentence) is expected


def test_hedging_outranks_causal_wording():
    """ "may have been caused by" is a conditional claim, not a direct one."""
    assert cue_strength("The fall may have been caused by the oil shock.") is Strength.CONDITIONAL


def test_a_sentence_with_no_cue_abstains():
    assert cue_strength("Brent settled at $104.63 a barrel.") is None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def test_a_perfect_classifier_scores_one():
    gold = [Strength.DIRECT, Strength.CONDITIONAL, Strength.CORRELATIONAL]
    report = score(gold, list(gold))
    assert report.accuracy == 1.0
    assert report.macro_f1 == 1.0
    assert report.abstentions == 0


def test_an_abstention_is_never_credited_as_correct():
    """Otherwise a classifier buys precision by declining the hard cases."""
    gold = [Strength.DIRECT, Strength.DIRECT]
    report = score(gold, [Strength.DIRECT, None])
    assert report.abstentions == 1
    assert report.row("direct").recall == 0.5
    assert report.row("direct").precision == 1.0


def test_the_confusion_matrix_accounts_for_every_item():
    gold = [Strength.DIRECT, Strength.CORRELATIONAL, Strength.CONDITIONAL]
    report = score(gold, [Strength.CONDITIONAL, Strength.CORRELATIONAL, None])
    total = sum(sum(row.values()) for row in report.confusion.values())
    assert total == len(gold) == report.n


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError, match="gold has"):
        score([Strength.DIRECT], [])


def test_an_empty_benchmark_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        score([], [])
