"""B3 - the anchored query set.

Eight queries over the four anchors that survived B2, one `why` and one
`effects` each. The checks that matter are the two that can silently go wrong:

* **as-of discipline.** A query's as-of date must clear its anchor's release
  lag, the `earliest as-of` column in `data/eval/episodes.md`. A query dated
  before its anchor was published rests on a vintage the system should not have
  been able to see.
* **no shared anchors across the split.** Dev and test draw on disjoint
  episodes, so tuning on dev cannot leak through a shared event and its
  passages into the test result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conditions.pipeline import Query
from corpus.series import SeriesStore
from eval.episodes import Disposition, confirm_episodes, load_episode_set

DEV = Path("data/eval/queries_dev.jsonl")
TEST = Path("data/eval/queries_test.jsonl")

#: Which B2 episode each anchor variable stands for.
ANCHOR_EPISODE = {
    "BRENT": "ep-mar-oil-shock",
    "INR_USD": "ep-may-rupee-low",
    "CPI_HEADLINE": "ep-cpi-acceleration",
    "FPI_FLOWS": "ep-mar-fpi-outflow",
}


def _load(path: Path) -> list[Query]:
    return [
        Query.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]


@pytest.fixture(scope="module")
def dev() -> list[Query]:
    return _load(DEV)


@pytest.fixture(scope="module")
def test_queries() -> list[Query]:
    return _load(TEST)


@pytest.fixture(scope="module")
def every(dev, test_queries) -> list[Query]:
    return [*dev, *test_queries]


@pytest.fixture(scope="module")
def episodes() -> dict:
    store = SeriesStore.from_directory("data/series")
    return {
        r.episode_id: r
        for r in confirm_episodes(load_episode_set("data/eval/episodes.yaml"), store)
    }


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_four_dev_and_four_test(dev, test_queries):
    assert len(dev) == 4
    assert len(test_queries) == 4


def test_every_query_id_is_unique(every):
    ids = [q.query_id for q in every]
    assert len(set(ids)) == len(ids)


def test_each_anchor_gets_one_why_and_one_effects(every):
    by_anchor: dict[str, list[str]] = {}
    for query in every:
        by_anchor.setdefault(query.anchor.var, []).append(query.question_type)
    assert len(by_anchor) == 4
    for anchor, kinds in by_anchor.items():
        assert sorted(kinds) == ["effects", "why"], anchor


def test_the_split_is_half_why_and_half_effects(dev, test_queries):
    for half in (dev, test_queries):
        assert sum(q.question_type == "why" for q in half) == 2


def test_a_why_question_names_its_target_and_effects_stays_open(every):
    """`effects` asks what sources discussed, so it must not be pointed at one variable."""
    for query in every:
        if query.question_type == "why":
            assert query.target_var is not None, query.query_id
        else:
            assert query.target_var is None, query.query_id


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


def test_dev_and_test_share_no_anchor(dev, test_queries):
    assert {q.anchor.var for q in dev}.isdisjoint({q.anchor.var for q in test_queries})


def test_dev_and_test_share_no_as_of_date(dev, test_queries):
    """Different anchors on the same date would still pull the same passages."""
    assert {q.as_of for q in dev}.isdisjoint({q.as_of for q in test_queries})


# ---------------------------------------------------------------------------
# As-of discipline, tied back to B2
# ---------------------------------------------------------------------------


def test_every_anchor_survived_the_B2_confirmation(every, episodes):
    for query in every:
        result = episodes[ANCHOR_EPISODE[query.anchor.var]]
        assert result.disposition in {Disposition.CONFIRMED, Disposition.REDATE}, query.query_id


def test_every_as_of_clears_its_anchors_release_lag(every, episodes):
    """The check B2 exists to make possible."""
    for query in every:
        result = episodes[ANCHOR_EPISODE[query.anchor.var]]
        assert result.earliest_as_of is not None
        assert query.as_of >= result.earliest_as_of, (
            f"{query.query_id}: as-of {query.as_of} precedes the earliest date the "
            f"anchor was published, {result.earliest_as_of}"
        )


def test_the_redated_oil_anchor_is_not_used_at_its_original_march_date(every):
    """B2 moved this anchor off 12 March; nothing may quietly move it back."""
    oil = [q for q in every if q.anchor.var == "BRENT"]
    assert oil
    for query in oil:
        assert query.as_of.month >= 4
        assert query.anchor.event_date.isoformat() == "2026-04-01"


def test_the_anchor_event_never_postdates_the_query(every):
    for query in every:
        assert query.anchor.event_date <= query.as_of


def test_every_anchor_declares_its_confirming_series(every):
    for query in every:
        assert query.anchor.confirmed_by_series is True
        assert query.anchor.series_id is not None


def test_no_query_uses_a_dropped_episode(every):
    """September's bond sell-off is unconfirmable; GSEC_10Y must not anchor anything."""
    assert all(q.anchor.var != "GSEC_10Y" for q in every)


# ---------------------------------------------------------------------------
# The frozen window
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [DEV, TEST])
def test_every_date_sits_inside_the_frozen_window(path: Path):
    for line in path.read_text().splitlines():
        row = json.loads(line)
        for field in (row["as_of"], row["anchor"]["event_date"]):
            assert "2026-03-01" <= field <= "2026-09-30", row["query_id"]
