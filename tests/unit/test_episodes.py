"""B2 - confirming anchor episodes against the series store, under as-of discipline.

The point of the check is that it can fail. An episode is confirmed only when an
observation that satisfies its claim was *already published* by the episode's
as-of date; an observation released later cannot confirm an earlier anchor, and
a series that never reaches the threshold cannot confirm it at all.
"""

from __future__ import annotations

from datetime import date

import pytest

from corpus.series import SeriesStore
from eval.episodes import (
    Comparison,
    Disposition,
    EpisodeSet,
    confirm_episode,
    confirm_episodes,
    load_episode_set,
)

SERIES_ROOT = "data/series"
EPISODES = "data/eval/episodes.yaml"


@pytest.fixture(scope="module")
def store() -> SeriesStore:
    return SeriesStore.from_directory(SERIES_ROOT)


@pytest.fixture(scope="module")
def episode_set() -> EpisodeSet:
    return load_episode_set(EPISODES)


@pytest.fixture(scope="module")
def results(episode_set: EpisodeSet, store: SeriesStore) -> dict:
    return {r.episode_id: r for r in confirm_episodes(episode_set, store)}


# ---------------------------------------------------------------------------
# The declaration itself
# ---------------------------------------------------------------------------


def test_the_proposal_asks_for_eight_episodes(episode_set: EpisodeSet):
    assert len(episode_set.episodes) == 8


def test_every_episode_sits_inside_the_frozen_window(episode_set: EpisodeSet):
    for episode in episode_set.episodes:
        assert episode_set.window_start <= episode.claimed_on <= episode_set.window_end


def test_an_as_of_date_may_not_precede_the_claim(episode_set: EpisodeSet):
    for episode in episode_set.episodes:
        assert episode.proposed_as_of >= episode.claimed_on


def test_a_series_backed_episode_must_declare_a_threshold():
    from eval.episodes import Episode

    with pytest.raises(ValueError, match="threshold"):
        Episode(
            id="bad",
            label="no threshold",
            claim="x",
            anchor_var="BRENT",
            direction="up",
            series_id="brent_usd_bbl",
            threshold=None,
            comparison=None,
            claimed_on=date(2026, 3, 12),
            proposed_as_of=date(2026, 3, 20),
        )


# ---------------------------------------------------------------------------
# As-of discipline
# ---------------------------------------------------------------------------


def test_an_observation_released_after_the_as_of_date_cannot_confirm(store: SeriesStore):
    """The Indian basket's April value was only published on 17 June."""
    from eval.episodes import Episode

    episode = Episode(
        id="basket-too-early",
        label="April basket",
        claim="Indian basket at or above 110",
        anchor_var="INDIAN_BASKET",
        direction="up",
        series_id="indian_basket_usd_bbl",
        threshold=110.0,
        comparison=Comparison.AT_OR_ABOVE,
        claimed_on=date(2026, 4, 30),
        proposed_as_of=date(2026, 5, 10),
    )
    result = confirm_episode(episode, store)
    assert result.disposition is Disposition.REDATE
    assert result.earliest_as_of == date(2026, 6, 17)


def test_the_same_episode_confirms_once_the_release_lag_is_cleared(store: SeriesStore):
    from eval.episodes import Episode

    episode = Episode(
        id="basket-late-enough",
        label="April basket",
        claim="Indian basket at or above 110",
        anchor_var="INDIAN_BASKET",
        direction="up",
        series_id="indian_basket_usd_bbl",
        threshold=110.0,
        comparison=Comparison.AT_OR_ABOVE,
        claimed_on=date(2026, 4, 30),
        proposed_as_of=date(2026, 6, 20),
    )
    assert confirm_episode(episode, store).disposition is Disposition.CONFIRMED


# ---------------------------------------------------------------------------
# The eight real episodes
# ---------------------------------------------------------------------------


def test_the_may_rupee_low_is_confirmed(results):
    """The strongest anchor in the set: same-day FX, and the window maximum."""
    result = results["ep-may-rupee-low"]
    assert result.disposition is Disposition.CONFIRMED
    assert result.observed_on == date(2026, 5, 20)
    assert result.observed_value == pytest.approx(96.8441)


def test_the_cpi_acceleration_is_confirmed(results):
    result = results["ep-cpi-acceleration"]
    assert result.disposition is Disposition.CONFIRMED
    assert result.observed_value >= 4.0


def test_the_march_fpi_outflow_is_confirmed(results):
    result = results["ep-mar-fpi-outflow"]
    assert result.disposition is Disposition.CONFIRMED
    assert result.observed_value <= -10000.0


def test_the_march_oil_shock_cannot_be_confirmed_at_its_proposed_date(results):
    """Brent's first held observation is 1 April, so no March as-of date works.

    This is the proposal's own worked example, and it has to move.
    """
    result = results["ep-mar-oil-shock"]
    assert result.disposition is Disposition.REDATE
    assert result.earliest_as_of == date(2026, 4, 1)
    assert result.observed_value == pytest.approx(104.63)


def test_the_september_bond_selloff_is_unconfirmable(results):
    """The yield series ends on 31 August and never reaches 7 per cent."""
    result = results["ep-sep-bond-selloff"]
    assert result.disposition is Disposition.UNCONFIRMED
    assert result.earliest_as_of is None


@pytest.mark.parametrize(
    "episode_id",
    ["ep-apr-atf-increase", "ep-jun-rbi-meeting", "ep-aug-rbi-meeting"],
)
def test_the_administered_and_policy_episodes_have_no_series(results, episode_id):
    """Not false - document-confirmed, which the checker labels rather than hides."""
    result = results[episode_id]
    assert result.disposition is Disposition.NO_SERIES
    assert result.observed_value is None


# ---------------------------------------------------------------------------
# What the set is worth as a whole
# ---------------------------------------------------------------------------


def test_only_three_episodes_are_series_confirmed_as_declared(results):
    confirmed = {k for k, r in results.items() if r.disposition is Disposition.CONFIRMED}
    assert confirmed == {
        "ep-may-rupee-low",
        "ep-cpi-acceleration",
        "ep-mar-fpi-outflow",
    }


def test_every_episode_gets_exactly_one_disposition(results, episode_set: EpisodeSet):
    assert set(results) == {e.id for e in episode_set.episodes}
    assert all(r.disposition is not None for r in results.values())


def test_a_confirmed_result_always_names_its_evidence(results):
    for result in results.values():
        if result.disposition is Disposition.CONFIRMED:
            assert result.observed_on is not None
            assert result.observed_value is not None
            assert result.source_url is not None
            assert result.available_on <= result.as_of


# ---------------------------------------------------------------------------
# Official vs news-reported confirmation
# ---------------------------------------------------------------------------


def test_cpi_and_fx_are_confirmed_against_official_data(results):
    """The proposal says the episodes are confirmed against official data."""
    assert results["ep-may-rupee-low"].official_source is True
    assert results["ep-cpi-acceleration"].official_source is True


def test_fpi_and_brent_rest_on_news_reported_observations(results):
    """Track A records these as news-reported, so they are dated but not official."""
    assert results["ep-mar-fpi-outflow"].official_source is False
    assert results["ep-mar-oil-shock"].official_source is False


def test_an_unconfirmed_episode_has_no_provenance(results):
    assert results["ep-sep-bond-selloff"].official_source is None
    assert results["ep-apr-atf-increase"].official_source is None


def test_only_two_episodes_meet_the_official_data_standard(results):
    official = {
        k
        for k, r in results.items()
        if r.disposition is Disposition.CONFIRMED and r.official_source
    }
    assert official == {"ep-may-rupee-low", "ep-cpi-acceleration"}
