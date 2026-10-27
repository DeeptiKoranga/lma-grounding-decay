"""Check a declared numerical move without treating it as causal evidence."""

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schema import Anchor, load_ontology
from schema.tools import GetSeriesArgs


class AnchorWindow(BaseModel):
    """Exact observation endpoints; optional thresholds are magnitudes, not forecasts."""

    model_config = ConfigDict(extra="forbid")
    start: date
    end: date
    minimum_absolute_change: float = Field(default=0, ge=0, allow_inf_nan=False)
    minimum_percent_change: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _ordered(self):
        if self.start >= self.end:
            raise ValueError("anchor window requires two distinct ordered observation dates")
        return self


def confirm_anchor(runtime, query):
    """Always discard input confirmation flags; only visible exact endpoints can confirm."""
    anchor = Anchor.model_validate(
        {**query.anchor.model_dump(), "confirmed_by_series": False, "series_id": None}
    )
    series_id = load_ontology()[anchor.var].series_id
    window = query.anchor_window
    evidence = {"confirmed": False, "status": "no_series_mapping", "observations": []}
    if series_id:
        # An undeclared window is diagnostic only. It never establishes an event.
        start = window.start if window else anchor.event_date - timedelta(days=7)
        end = window.end if window else anchor.event_date
        args = GetSeriesArgs(series_id=series_id, start=start, end=end, as_of=query.as_of)
        result = runtime.call("get_series", **args.model_dump())
        rows = runtime.series.observations(args) if result.ok else ()
        evidence.update(
            series_id=series_id,
            request=args.model_dump(mode="json"),
            call_id=result.call_id,
            window_declared=window is not None,
            observations=[row.model_dump(mode="json") for row in rows],
            status="window_not_declared" if window is None else "insufficient_observations",
        )
        if not result.ok:
            evidence["status"] = result.error.kind
        elif window and len(rows) >= 2 and rows[0].on == start and rows[-1].on == end:
            change = rows[-1].value - rows[0].value
            percent = abs(change / rows[0].value) * 100 if rows[0].value else None
            evidence.update(change=change, percent_change_magnitude=percent)
            confirmed = (
                result.move == anchor.direction
                and abs(change) >= window.minimum_absolute_change
                and (
                    window.minimum_percent_change == 0
                    or (percent is not None and percent >= window.minimum_percent_change)
                )
            )
            evidence.update(
                confirmed=confirmed,
                status="confirmed_window_move" if confirmed else "move_or_threshold_mismatch",
                criteria=window.model_dump(mode="json"),
            )
            anchor.confirmed_by_series = confirmed
            anchor.series_id = series_id if confirmed else None
    runtime.graph = type(runtime.graph).model_validate(
        {**runtime.graph.model_dump(), "anchor": anchor.model_dump()}
    )
    return evidence
