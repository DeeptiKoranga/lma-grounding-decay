"""Snapshot capture dates must not leak retrospective facts into earlier queries."""

import calendar
import importlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from corpus.series import SeriesStore
from schema.tools import GetSeriesArgs


@pytest.fixture
def retro(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.retrospective_series")


def metadata():
    return {"checked_at": "2026-10-25T14:00:00+00:00", "url": "https://example.org/public-history"}


def brent_payload():
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "BZ=F",
                        "currency": "USD",
                        "instrumentType": "FUTURE",
                        "exchangeName": "NYM",
                        "priceHint": 2,
                        "exchangeTimezoneName": "America/New_York",
                    },
                    "timestamp": [
                        int(datetime(2026, m, 15, 12, tzinfo=UTC).timestamp()) for m in range(3, 10)
                    ],
                    "indicators": {
                        "quote": [{"close": [100.00000001] * 7}],
                        "adjclose": [{"adjclose": [100.00000001] * 7}],
                    },
                }
            ],
        }
    }


def test_retrospective_closes_are_invisible_at_historical_cutoffs(retro):
    rows = retro.brent_rows(json.dumps(brent_payload()).encode(), metadata())
    assert len(rows) == 7 and all(r.value == 100 for r in rows)
    assert all(r.available_on == date(2026, 10, 25) for r in rows)
    store = SeriesStore({"brent_usd_bbl": rows})
    args = GetSeriesArgs(
        series_id="brent_usd_bbl",
        start=date(2026, 3, 1),
        end=date(2026, 9, 30),
        as_of=date(2026, 9, 30),
    )
    assert store.observations(args) == ()
    assert len(store.observations(args.model_copy(update={"as_of": date(2026, 10, 25)}))) == 7


@pytest.mark.parametrize("fault", ["spot", "currency", "adjusted", "missing_month", "future_day"])
def test_changed_benchmark_adjustment_and_invalid_dates_fail_closed(retro, fault):
    data = brent_payload()
    r = data["chart"]["result"][0]
    if fault == "spot":
        r["meta"]["instrumentType"] = "INDEX"
    elif fault == "currency":
        r["meta"]["currency"] = "INR"
    elif fault == "adjusted":
        r["indicators"]["adjclose"][0]["adjclose"][0] = 90
    elif fault == "missing_month":
        r["indicators"]["quote"][0]["close"][0] = None
    else:
        r["timestamp"][0] = int(datetime(2026, 10, 15, 12, tzinfo=UTC).timestamp())
    with pytest.raises(ValueError):
        retro.brent_rows(json.dumps(data).encode(), metadata())


def test_fred_monthly_period_labels_are_not_daily_closes_or_early_release_dates(retro):
    text = "observation_date,INDIRLTLT01STM\n" + "".join(
        f"2026-{m:02d}-01,6.8\n" for m in range(3, 10)
    )
    rows = retro.fred_rows(text.encode(), metadata())
    assert [r.on for r in rows] == [
        date(2026, m, calendar.monthrange(2026, m)[1]) for m in range(3, 10)
    ]
    assert all(r.available_on == date(2026, 10, 25) and r.unit == "percent" for r in rows)
    with pytest.raises(ValueError, match="seven months"):
        retro.fred_rows(text.rsplit("2026-09-01", 1)[0].encode(), metadata())


def test_capture_timestamp_uses_india_date_and_rejects_undated_values(retro):
    assert retro.capture_day({"fetched_at": "2026-10-22T22:40:00+00:00"}) == date(2026, 10, 23)
    with pytest.raises(ValueError, match="timezone"):
        retro.capture_day({"checked_at": "2026-10-22T22:40:00"})


def test_source_checksum_and_default_store_are_protected(retro, tmp_path):
    raw, meta = tmp_path / "raw", tmp_path / "meta.json"
    raw.write_text("source changed")
    meta.write_text(json.dumps({**metadata(), "sha256": "0" * 64}))
    with pytest.raises(ValueError, match="checksum"):
        retro.checked_source(raw, meta)
    with pytest.raises(ValueError, match="default store"):
        retro.acquire(
            raw=tmp_path,
            cdsl=tmp_path,
            visual_seed=tmp_path,
            canonical=tmp_path,
            output=tmp_path,
            report=tmp_path / "report",
        )
