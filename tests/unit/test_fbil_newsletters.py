import importlib
from pathlib import Path

import pytest


@pytest.fixture
def parse_yield_table(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.fbil_newsletters").parse_yield_table


def table(*, header="Mar", note="March", row="India 7.03 6.58 6.48 October 06, 2035"):
    return (
        "10-year Sovereign Bond Yield of Major Economies\n"
        f"Countries/Economies Yield (%) *{header} 2026 Yield (%) Mar 2025 Coupon (%) Maturity\n"
        f"{row}\n*{note} 2026 - Month \u2013 end closing level; Source: LSEG"
    )


def test_current_yield_is_distinct_from_prior_year_coupon_and_maturity(parse_yield_table):
    result = parse_yield_table(table(), month=3, year=2026)
    assert result["value"] == 7.03
    assert result["prior_year_comparison"] == 6.58
    assert result["coupon_percent"] == 6.48
    assert result["maturity"] == "2035-10-06"
    assert result["observation_on"] == "2026-03-31"


@pytest.mark.parametrize(
    ("text", "month"),
    [
        (table(header="July", note="June"), 7),
        (table(header="Apr"), 3),
        (table().replace("Month \u2013 end closing level", "monthly average"), 3),
        (table().replace("*March 2026", "*March 2025"), 3),
        (table(row="India 7.03 6.58"), 3),
        (table(row="India 7.03 6.58 0.00 October 06, 2035"), 3),
        (table() + table(), 3),
    ],
)
def test_ambiguous_or_misidentified_tables_are_rejected(text, month, parse_yield_table):
    with pytest.raises(ValueError):
        parse_yield_table(text, month=month, year=2026)
