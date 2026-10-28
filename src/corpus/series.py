"""Vintage-aware macro series for A10; observations confirm moves, never causal edges.

The observation date and the date information became public are separate. A CPI
reading for March cannot be returned on 31 March when it was released in April.
Revisions retain their own availability date instead of rewriting history.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from schema import Direction, load_ontology
from schema.tools import GetSeriesArgs, GetSeriesResult, SeriesPoint, ToolError

SERIES_VARIABLES = (
    "BRENT",
    "INDIAN_BASKET",
    "INR_USD",
    "CPI_HEADLINE",
    "GSEC_10Y",
    "FPI_FLOWS",
)
SERIES_SPECS = MappingProxyType(
    {load_ontology()[var].series_id: load_ontology()[var] for var in SERIES_VARIABLES}
)
CSV_FIELDS = ("on", "value", "available_on", "source_url", "unit")


class Observation(BaseModel):
    """One published vintage of one observation, with auditable provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    on: date
    value: float
    available_on: date
    source_url: str
    unit: str

    @field_validator("value")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("series values must be finite")
        return value

    @field_validator("source_url")
    @classmethod
    def _source_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or any(char.isspace() for char in value)
        ):
            raise ValueError("source_url must be a public HTTP(S) source URL")
        return value

    @model_validator(mode="after")
    def _release_after_observation(self) -> Observation:
        if self.available_on < self.on:
            raise ValueError("available_on cannot precede the observation date")
        return self


def validate_observations(
    series_id: str, records: Iterable[Observation]
) -> tuple[Observation, ...]:
    """Require known units and unique observation/vintage pairs, ordered reproducibly."""
    if series_id not in SERIES_SPECS:
        raise ValueError(f"unknown series id: {series_id}")
    unit = SERIES_SPECS[series_id].unit
    validated = []
    seen = set()
    for record in records:
        # Validate even a Pydantic model produced through model_construct().
        record = Observation.model_validate(record.model_dump())
        key = (record.on, record.available_on)
        if key in seen:
            raise ValueError(f"duplicate observation/vintage: {record.on}/{record.available_on}")
        if record.unit != unit:
            raise ValueError(f"{series_id} requires unit {unit!r}, got {record.unit!r}")
        seen.add(key)
        validated.append(record)
    return tuple(sorted(validated, key=lambda row: (row.on, row.available_on)))


def read_csv(path: str | Path, *, series_id: str) -> tuple[Observation, ...]:
    """Read normalized values; never guess missing release dates, units or sources."""
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != set(CSV_FIELDS):
            raise ValueError(f"CSV columns must be exactly {', '.join(CSV_FIELDS)}")
        if len(reader.fieldnames) != len(CSV_FIELDS):
            raise ValueError("CSV columns must not be repeated")
        records = []
        for number, row in enumerate(reader, start=2):
            try:
                records.append(Observation.model_validate(row))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"invalid series CSV row {number}: {exc}") from exc
    return validate_observations(series_id, records)


def write_csv(path: str | Path, *, series_id: str, records: Iterable[Observation]) -> None:
    """Write canonical, validated CSV. Caller controls whether replacement is allowed."""
    validated = validate_observations(series_id, records)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in validated:
            writer.writerow(row.model_dump(mode="json"))


class SeriesStore:
    """Read-only point-in-time access, ready for Track C's get_series adapter."""

    def __init__(self, series: Mapping[str, Iterable[Observation]]):
        self.series = MappingProxyType(
            {
                series_id: validate_observations(series_id, rows)
                for series_id, rows in series.items()
            }
        )

    @classmethod
    def from_directory(cls, root: str | Path) -> SeriesStore:
        root = Path(root)
        if not root.is_dir():
            raise FileNotFoundError(f"series directory does not exist: {root}")
        return cls(
            {
                series_id: read_csv(root / f"{series_id}.csv", series_id=series_id)
                for series_id in SERIES_SPECS
                if (root / f"{series_id}.csv").is_file()
            }
        )

    def observations(self, args: GetSeriesArgs) -> tuple[Observation, ...]:
        """Return latest visible vintages, retaining provenance for audit callers."""
        # Revalidate callers that use model_construct() or unchecked model_copy().
        args = GetSeriesArgs.model_validate(args.model_dump())
        if args.series_id not in self.series:
            raise KeyError(f"series is unknown or has not been imported: {args.series_id}")
        visible = {}
        for row in self.series[args.series_id]:
            if args.start <= row.on <= args.end and row.available_on <= args.as_of:
                visible[row.on] = row
        return tuple(visible[on] for on in sorted(visible))

    def get_series(self, args: GetSeriesArgs, *, call_id: str) -> GetSeriesResult:
        """Conform to the frozen tool result without introducing evidence labels."""
        try:
            rows = self.observations(args)
        except KeyError as exc:
            return GetSeriesResult(
                call_id=call_id,
                ok=False,
                series_id=args.series_id,
                error=ToolError(kind="unknown_series", message=str(exc)),
            )
        if not rows:
            return GetSeriesResult(
                call_id=call_id,
                ok=False,
                series_id=args.series_id,
                error=ToolError(kind="empty_result", message="no observations available by as-of"),
            )
        move = None
        if len(rows) >= 2:
            difference = rows[-1].value - rows[0].value
            move = (
                Direction.UP
                if difference > 0
                else Direction.DOWN if difference < 0 else Direction.STABLE
            )
        return GetSeriesResult(
            call_id=call_id,
            series_id=args.series_id,
            points=[SeriesPoint(on=row.on, value=row.value) for row in rows],
            move=move,
        )
