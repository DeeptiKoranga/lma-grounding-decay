"""B2 - confirm the anchor episodes against the macro series store.

The proposal anchors its queries on eight 2026 episodes and says they "will be
confirmed against official data". This module does that confirmation, and does
it under **as-of discipline**: an observation confirms an episode only when its
`available_on` date falls on or before the episode's as-of date. A CPI print
released on 13 July cannot confirm an anchor for a query dated 30 June, and an
anchor that rests on a later vintage is a leak dressed as a fact.

Four dispositions, and the useful ones are the failures:

`confirmed`
    A visible observation satisfies the claim at the proposed as-of date.
`redate`
    An observation satisfies the claim, but only becomes visible later.
    `earliest_as_of` says when, so the query can be moved rather than dropped.
`unconfirmed`
    No observation in the window satisfies the claim at any as-of date. The
    episode has to be dropped or restated.
`no_series`
    The anchor variable has no series in the store, so the move cannot be
    confirmed this way at all. Administered prices (ATF) and policy decisions
    (the MPC meetings) land here. These are not false; they are
    document-confirmed, which is weaker and is labelled rather than hidden.

Series confirm that a move happened. They are never evidence for an edge
(proposal section 10), and nothing here produces or touches an `Edge`.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus.series import Observation, SeriesStore

__all__ = [
    "Comparison",
    "Disposition",
    "Episode",
    "EpisodeConfirmation",
    "EpisodeSet",
    "confirm_episode",
    "confirm_episodes",
    "load_episode_set",
]

#: Publishers whose releases count as official data for anchor confirmation.
#: Track A's store also carries news-reported observations for Brent, the
#: benchmark yield and FPI; those confirm a dated move but are not official.
_OFFICIAL_HOSTS = frozenset(
    {
        "fbil.org.in",
        "mospi.gov.in",
        "ppac.gov.in",
        "rbi.org.in",
        "sebi.gov.in",
        "dea.gov.in",
        "pib.gov.in",
        "eaindustry.nic.in",
    }
)


class Comparison(StrEnum):
    """How an observation is tested against the episode's threshold."""

    AT_OR_ABOVE = "at_or_above"
    AT_OR_BELOW = "at_or_below"

    def holds(self, value: float, threshold: float) -> bool:
        if self is Comparison.AT_OR_ABOVE:
            return value >= threshold
        return value <= threshold


class Disposition(StrEnum):
    CONFIRMED = "confirmed"
    REDATE = "redate"
    UNCONFIRMED = "unconfirmed"
    NO_SERIES = "no_series"


class Episode(BaseModel):
    """One candidate anchor event, and what would confirm it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    anchor_var: str = Field(min_length=1)
    direction: str
    series_id: str | None = None
    threshold: float | None = None
    comparison: Comparison | None = None
    claimed_on: date
    proposed_as_of: date
    note: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.proposed_as_of < self.claimed_on:
            raise ValueError(
                f"episode {self.id!r}: as-of date {self.proposed_as_of} precedes "
                f"the claimed date {self.claimed_on}"
            )
        if self.series_id is not None and (self.threshold is None or self.comparison is None):
            raise ValueError(
                f"episode {self.id!r}: a series-backed episode needs both a threshold "
                "and a comparison, or the check cannot fail"
            )
        if self.series_id is None and self.threshold is not None:
            raise ValueError(f"episode {self.id!r}: a threshold without a series cannot be tested")
        return self

    @property
    def is_series_backed(self) -> bool:
        return self.series_id is not None


class EpisodeSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    checked_on: date
    window_start: date
    window_end: date
    episodes: tuple[Episode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _inside_the_window(self) -> Self:
        seen: set[str] = set()
        for episode in self.episodes:
            if episode.id in seen:
                raise ValueError(f"duplicate episode id {episode.id!r}")
            seen.add(episode.id)
            if not self.window_start <= episode.claimed_on <= self.window_end:
                raise ValueError(
                    f"episode {episode.id!r} is claimed on {episode.claimed_on}, "
                    f"outside the frozen window {self.window_start}..{self.window_end}"
                )
        return self


class EpisodeConfirmation(BaseModel):
    """What the series store can and cannot say about one episode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    label: str
    anchor_var: str
    as_of: date
    disposition: Disposition
    reason: str
    observed_on: date | None = None
    observed_value: float | None = None
    available_on: date | None = None
    source_url: str | None = None
    earliest_as_of: date | None = Field(
        default=None,
        description="For `redate`, the first as-of date at which the claim is visible.",
    )

    @model_validator(mode="after")
    def _evidence_matches_disposition(self) -> Self:
        if self.disposition is Disposition.CONFIRMED and self.observed_on is None:
            raise ValueError(f"{self.episode_id}: confirmed without naming an observation")
        if self.disposition is Disposition.REDATE and self.earliest_as_of is None:
            raise ValueError(f"{self.episode_id}: redate without an earliest as-of date")
        return self

    @property
    def usable_as_declared(self) -> bool:
        return self.disposition is Disposition.CONFIRMED

    @property
    def official_source(self) -> bool | None:
        """Whether the confirming observation came from an official publisher.

        The proposal says the episodes "will be confirmed against official data".
        Track A's store meets that for CPI and FX, but records Brent, the
        benchmark yield and FPI as *news-reported* observations
        (`data/series/README.md`). A news-reported confirmation is still a dated
        observation under as-of discipline, but it is not official data, and the
        mid report has to say which is which. None when nothing confirmed it.
        """
        if self.source_url is None:
            return None
        host = urlsplit(self.source_url).hostname or ""
        return any(host == domain or host.endswith(f".{domain}") for domain in _OFFICIAL_HOSTS)


def load_episode_set(path: str | Path) -> EpisodeSet:
    """Read the candidate episodes from YAML. No series access, no I/O beyond this."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return EpisodeSet.model_validate(raw)


def _satisfying(episode: Episode, observations: Sequence[Observation]) -> list[Observation]:
    assert episode.comparison is not None and episode.threshold is not None
    return [obs for obs in observations if episode.comparison.holds(obs.value, episode.threshold)]


def confirm_episode(episode: Episode, store: SeriesStore) -> EpisodeConfirmation:
    """Test one episode against the store under as-of discipline."""
    common = {
        "episode_id": episode.id,
        "label": episode.label,
        "anchor_var": episode.anchor_var,
        "as_of": episode.proposed_as_of,
    }

    if not episode.is_series_backed:
        return EpisodeConfirmation(
            **common,
            disposition=Disposition.NO_SERIES,
            reason=(
                f"{episode.anchor_var} has no series in the store, so the move cannot be "
                "series-confirmed; this anchor is document-confirmed only"
            ),
        )

    assert episode.series_id is not None
    # Every held vintage. The as-of filter is applied below, deliberately, rather
    # than by `store.observations`, because a `redate` disposition has to know
    # about the observations the as-of date hides.
    held = store.series.get(episode.series_id, ())
    satisfying = _satisfying(episode, held)
    if not satisfying:
        return EpisodeConfirmation(
            **common,
            disposition=Disposition.UNCONFIRMED,
            reason=(
                f"no observation in {episode.series_id!r} satisfies "
                f"{episode.claim!r} at any as-of date; the series holds "
                f"{len(held)} observation(s)"
            ),
        )

    # Earliest date at which some satisfying observation had been published.
    earliest = min(obs.available_on for obs in satisfying)
    visible = [obs for obs in satisfying if obs.available_on <= episode.proposed_as_of]

    if not visible:
        # Name the observation that *would* confirm it, so the table says what the
        # redated anchor rests on rather than only that the date is wrong.
        would_confirm = min(satisfying, key=lambda obs: (obs.available_on, obs.on))
        return EpisodeConfirmation(
            **common,
            disposition=Disposition.REDATE,
            reason=(
                f"{episode.claim!r} is satisfied in {episode.series_id!r}, but the "
                f"earliest satisfying observation was published on {earliest}, after "
                f"the proposed as-of date {episode.proposed_as_of}"
            ),
            observed_on=would_confirm.on,
            observed_value=would_confirm.value,
            available_on=would_confirm.available_on,
            source_url=would_confirm.source_url,
            earliest_as_of=earliest,
        )

    # Prefer the observation closest to the claimed date among the visible ones.
    chosen = min(visible, key=lambda obs: abs((obs.on - episode.claimed_on).days))
    return EpisodeConfirmation(
        **common,
        disposition=Disposition.CONFIRMED,
        reason=(
            f"{episode.series_id!r} observation on {chosen.on} of {chosen.value}, "
            f"published {chosen.available_on}, satisfies {episode.claim!r}"
        ),
        observed_on=chosen.on,
        observed_value=chosen.value,
        available_on=chosen.available_on,
        source_url=chosen.source_url,
        earliest_as_of=earliest,
    )


def confirm_episodes(episode_set: EpisodeSet, store: SeriesStore) -> Iterator[EpisodeConfirmation]:
    for episode in episode_set.episodes:
        yield confirm_episode(episode, store)
