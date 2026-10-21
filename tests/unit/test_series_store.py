"""Point-in-time macro tests use illustrative values only in temporary fixtures."""

from __future__ import annotations

import csv
import importlib
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus.series import (
    CSV_FIELDS,
    SERIES_SPECS,
    Observation,
    SeriesStore,
    read_csv,
    write_csv,
)
from schema import Direction
from schema.tools import GetSeriesArgs, parse_tool_result


def observation(on="2026-03-31", available_on="2026-04-12", value=4.0, **kwargs):
    return Observation(
        on=on,
        available_on=available_on,
        value=value,
        source_url=kwargs.get("source_url", "https://example.org/releases/cpi"),
        unit=kwargs.get("unit", "percent year on year"),
    )


def query(
    as_of="2026-04-12", *, series_id="cpi_headline_yoy", start="2026-03-01", end="2026-03-31"
):
    return GetSeriesArgs(series_id=series_id, start=start, end=end, as_of=as_of)


def test_monthly_value_is_invisible_until_actual_release():
    store = SeriesStore({"cpi_headline_yoy": [observation()]})
    before = store.get_series(query("2026-03-31"), call_id="before")
    assert not before.ok
    assert before.error.kind == "empty_result"
    assert before.points == []
    released = store.get_series(query(), call_id="released")
    assert released.ok
    assert [(point.on, point.value) for point in released.points] == [(date(2026, 3, 31), 4.0)]
    assert released.move is None
    assert parse_tool_result(released.model_dump(mode="json")) == released


def test_revisions_do_not_rewrite_earlier_as_of_queries():
    original = observation(value=4.0)
    revision = observation(available_on="2026-05-12", value=4.2)
    later = observation(on="2026-04-30", available_on="2026-05-12", value=4.5)
    store = SeriesStore({"cpi_headline_yoy": [later, revision, original]})
    assert [row.value for row in store.observations(query())] == [4.0]
    assert [row.value for row in store.observations(query("2026-05-12"))] == [4.2]
    result = store.get_series(query("2026-05-12", end="2026-04-30"), call_id="later")
    assert [point.value for point in result.points] == [4.2, 4.5]
    assert result.move == Direction.UP
    assert store.observations(query("2026-05-12"))[0].source_url == original.source_url


@pytest.mark.parametrize("values,expected", [([5, 4], "down"), ([4, 4], "stable"), ([4, 5], "up")])
def test_moves_use_only_visible_observations_inside_requested_window(values, expected):
    rows = [
        observation("2026-02-28", "2026-03-12", value=100),
        observation("2026-03-31", "2026-04-12", value=values[0]),
        observation("2026-04-30", "2026-05-12", value=values[1]),
        observation("2026-05-31", "2026-06-12", value=100),
    ]
    result = SeriesStore({"cpi_headline_yoy": rows}).get_series(
        query("2026-06-30", end="2026-04-30"), call_id="move"
    )
    assert result.move == expected
    assert len(result.points) == 2


def test_missing_series_is_an_explicit_error():
    for series_id in ("missing", "brent_usd_bbl", "../../secret"):
        result = SeriesStore({}).get_series(query(series_id=series_id), call_id="missing")
        assert not result.ok
        assert result.error.kind == "unknown_series"
        assert result.points == []
        assert result.move is None


def test_unchecked_arguments_cannot_widen_as_of():
    store = SeriesStore({"cpi_headline_yoy": [observation()]})
    forged = query().model_copy(update={"as_of": date(2026, 3, 1)})
    with pytest.raises(ValidationError, match="after the as-of"):
        store.get_series(forged, call_id="forged")


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_values_are_rejected(bad_value):
    with pytest.raises(ValidationError, match="finite"):
        observation(value=bad_value)


def test_dates_sources_units_and_duplicate_vintages_are_validated():
    with pytest.raises(ValidationError, match="cannot precede"):
        observation(available_on="2026-03-30")
    for url in (
        "",
        "file:///tmp/data.csv",
        "https://user:secret@example.org/a",
        "https://example.org/a b",
    ):
        with pytest.raises(ValidationError, match="source_url"):
            observation(source_url=url)
    with pytest.raises(ValueError, match="requires unit"):
        SeriesStore({"cpi_headline_yoy": [observation(unit="index")]})
    with pytest.raises(ValueError, match="duplicate"):
        SeriesStore({"cpi_headline_yoy": [observation(), observation(value=5)]})
    with pytest.raises(ValueError, match="unknown series"):
        SeriesStore({"unknown": []})
    forged = observation().model_copy(update={"value": float("inf")})
    with pytest.raises(ValidationError, match="finite"):
        SeriesStore({"cpi_headline_yoy": [forged]})


def test_csv_round_trip_preserves_vintages_provenance_and_units(tmp_path):
    rows = [observation(available_on="2026-05-12", value=4.2), observation()]
    path = tmp_path / "cpi_headline_yoy.csv"
    write_csv(path, series_id="cpi_headline_yoy", records=rows)
    loaded = read_csv(path, series_id="cpi_headline_yoy")
    assert loaded == tuple(reversed(rows))
    store = SeriesStore.from_directory(tmp_path)
    assert store.observations(query()) == (rows[1],)
    assert path.read_text().splitlines()[0] == ",".join(CSV_FIELDS)
    assert len(SERIES_SPECS) == 6


@pytest.mark.parametrize(
    "content",
    [
        "on,value\n2026-03-31,4.0\n",
        "on,value,available_on,source_url,unit,unit\n",
        "on,value,available_on,source_url,unit\n2026-03-31,nan,2026-04-12,https://example.org/a,percent year on year\n",
        "on,value,available_on,source_url,unit\n2026-03-31,4.0,,https://example.org/a,percent year on year\n",
        "on,value,available_on,source_url,unit\n2026-03-31,4.0,2026-04-12,https://example.org/a,percent year on year,extra\n",
    ],
)
def test_csv_does_not_guess_missing_metadata_or_skip_bad_rows(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_csv(path, series_id="cpi_headline_yoy")


def test_missing_directory_is_not_silently_created(tmp_path):
    with pytest.raises(FileNotFoundError):
        SeriesStore.from_directory(tmp_path / "not-there")


def test_import_is_validated_atomic_and_requires_explicit_replacement(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    importer = importlib.import_module("scripts.fetch.series")
    source = tmp_path / "input.csv"
    write_csv(source, series_id="cpi_headline_yoy", records=[observation()])
    root = tmp_path / "series"
    summary = importer.import_series(source, series_id="cpi_headline_yoy", root=root)
    assert summary["observations"] == 1
    assert summary["vintages"] == 1
    assert len(summary["sha256"]) == 64
    target = root / "cpi_headline_yoy.csv"
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        importer.import_series(source, series_id="cpi_headline_yoy", root=root)
    write_csv(source, series_id="cpi_headline_yoy", records=[observation(value=5)])
    importer.import_series(source, series_id="cpi_headline_yoy", root=root, replace=True)
    assert target.read_bytes() != before
    with source.open("a", newline="") as stream:
        csv.writer(stream).writerow(["bad", "nan", "", "", ""])
    before = target.read_bytes()
    with pytest.raises(ValueError):
        importer.import_series(source, series_id="cpi_headline_yoy", root=root, replace=True)
    assert target.read_bytes() == before
    assert not list(root.glob("*.tmp"))
