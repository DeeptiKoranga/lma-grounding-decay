import importlib
from datetime import date
from pathlib import Path

import pytest

from schema import Passage


@pytest.fixture
def news_series(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.news_series")


def passage(base, text, day):
    return Passage.model_validate(
        {
            **base.model_dump(),
            "text": text,
            "char_start": 0,
            "char_end": len(text),
            "published_at": day + "T17:00:00+05:30",
        }
    )


def test_front_month_price_is_not_price_change_or_wti(news_series, passages):
    p = passage(
        passages[0],
        "Front month Brent crude futures gained $0.71, or 0.8%, to $84.50 a barrel. WTI rose to $81 a barrel.",
        "2026-08-04",
    )
    row, info = news_series.extract_claim("brent_front_quote", p, date(2026, 8, 4))
    assert row.value == 84.5
    assert row.available_on == row.on
    assert "intraday" in info["measure"]


def test_expiring_front_contract_is_not_more_active_deferred_contract(news_series, passages):
    p = passage(
        passages[0],
        "Brent crude futures for August delivery, which expire on Tuesday, rose by 16 cents or 0.22% to reach $73.31 per barrel during trading. The more actively traded September Brent contract rose to $74.36 per barrel.",
        "2026-06-30",
    )
    row, info = news_series.extract_claim("brent_expiry_quote", p, date(2026, 6, 30))
    assert row.value == 73.31
    assert info["contract_month"] == "August"
    with pytest.raises(ValueError, match="expire"):
        news_series.extract_claim(
            "brent_expiry_quote",
            passage(p, p.text.replace("Tuesday", "Wednesday"), "2026-06-30"),
            date(2026, 6, 30),
        )


def test_spot_or_unspecified_brent_is_not_accepted_as_front_month(news_series, passages):
    p = passage(passages[0], "Brent spot crude rose to $84.50 a barrel.", "2026-08-04")
    with pytest.raises(ValueError, match="front-month"):
        news_series.extract_claim("brent_front_quote", p, date(2026, 8, 4))


def test_front_month_forecast_cannot_be_imported_as_an_observation(news_series, passages):
    p = passage(
        passages[0],
        "Front month Brent crude futures are expected to rise to $84.50 a barrel.",
        "2026-08-04",
    )
    with pytest.raises(ValueError, match="front-month"):
        news_series.extract_claim("brent_front_quote", p, date(2026, 8, 4))


def test_closing_benchmark_yield_is_not_coupon_high_or_previous(news_series, passages):
    p = passage(
        passages[0],
        "The yield of the benchmark 10-year G-Sec (6.48 per cent GS 2035), which touched an intraday high of 6.76 per cent, closed at 6.72 per cent, up over the previous close of 6.69 per cent.",
        "2026-03-09",
    )
    row, info = news_series.extract_claim("gsec_close", p, date(2026, 3, 9))
    assert row.value == 6.72
    assert info["security"] == "6.48% GS 2035"


@pytest.mark.parametrize(
    "text",
    [
        "The 10-year par yield closed at 6.72 per cent.",
        "The benchmark 6.48% GS 2035 is expected to close at 6.72 per cent.",
        "The benchmark 6.48% GS 2045 closed at 6.72 per cent.",
    ],
)
def test_unnamed_wrong_tenor_or_projected_yields_rejected(news_series, passages, text):
    p = passage(passages[0], text, "2026-03-09")
    with pytest.raises(ValueError):
        news_series.extract_claim("gsec_close", p, date(2026, 3, 9))


def test_fpi_uses_completed_month_not_current_mtd_and_converts_only_scale(news_series, passages):
    text = "Over the month so far, overseas investors have net sold more than $6.5 billion worth of local stock and bonds, adding to March's $13.6 billion outflow."
    p = passage(passages[0], text, "2026-04-13")
    row, info = news_series.extract_claim("fpi_monthly_net", p, date(2026, 3, 31))
    assert row.value == -13600
    assert row.available_on == date(2026, 4, 13)
    assert info["reported_precision_usd_million"] == 100
    with pytest.raises(ValueError):
        news_series.extract_claim("fpi_monthly_net", p, date(2026, 4, 13))


@pytest.mark.parametrize(
    "change",
    [("local stock and bonds", "local stocks"), ("March's $13.6", "March's more than $13.6")],
)
def test_fpi_equity_only_or_bound_is_not_total(news_series, passages, change):
    text = "overseas investors have net sold $6.5 billion worth of local stock and bonds, adding to March's $13.6 billion outflow."
    p = passage(passages[0], text.replace(*change), "2026-04-13")
    with pytest.raises(ValueError):
        news_series.extract_claim("fpi_monthly_net", p, date(2026, 3, 31))


def test_news_quote_cannot_be_backdated_to_an_earlier_observation_day(news_series, passages):
    p = passage(
        passages[0], "Front month Brent crude futures rose to $84.50 a barrel.", "2026-08-04"
    )
    with pytest.raises(ValueError, match="publication day"):
        news_series.extract_claim("brent_front_quote", p, date(2026, 8, 3))
