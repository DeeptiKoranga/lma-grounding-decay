"""Official rate definitions and display timestamps survive normalization."""

import importlib
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def fbil(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.fbil_series")


def row(**changes):
    return {
        "processRunDate": "2026-03-06 00:00:00",
        "displayTime": "2026-03-06 13:00:00",
        "subProdName": "INR / 1 USD",
        "rate": 91.6829,
        **changes,
    }


def parse(fbil, rows):
    return fbil.parse_reference_rates(
        rows,
        url="https://www.fbil.org.in/public-api",
        start=date(2026, 3, 1),
        end=date(2026, 3, 31),
    )


def test_only_usd_reference_rates_with_actual_availability_are_imported(fbil):
    result = parse(fbil, [row(), row(subProdName="INR / 100 JPY", rate=58.08)])
    assert len(result) == 1
    assert result[0].value == 91.6829
    assert result[0].unit == "INR per USD"
    assert result[0].available_on == date(2026, 3, 6)
    revised = parse(fbil, [row(displayTime="2026-03-09 13:00:00")])[0]
    assert revised.on == date(2026, 3, 6) and revised.available_on == date(2026, 3, 9)


@pytest.mark.parametrize(
    "rows",
    [
        [row(rate=0)],
        [row(rate=float("nan"))],
        [row(displayTime="2026-03-05 13:00:00")],
        [row(processRunDate="2026-04-01 00:00:00")],
        [row(), row()],
        [row(subProdName="INR / 1 EUR")],
        {"data": [row()]},
    ],
)
def test_invalid_definitions_dates_values_and_duplicates_fail_closed(fbil, rows):
    with pytest.raises(ValueError):
        parse(fbil, rows)
