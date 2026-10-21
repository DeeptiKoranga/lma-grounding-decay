"""CPI originals must match the requested base, period, metric and release date."""

import importlib
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def cpi(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.cpi_series")


TEXT = (
    "Dated 13th April, 2026\n"
    "PRESS RELEASE OF CONSUMER PRICE INDEX ON BASE 2024=100 FOR March, 2026\n"
    "Year-on-year inflation rate based on All India Consumer Price Index (CPI) "
    "with base year 2024 for the month of March, 2026 over March, 2025 is "
    "3.40% (Provisional). Corresponding inflation rates for rural and urban are 3.55% and 3.22%."
)


def test_original_cpi_extracts_combined_yoy_with_actual_release_day(cpi):
    row = cpi.parse_cpi_text(TEXT, source_url="https://mospi.gov.in/original.pdf", month=3)
    assert row.on == date(2026, 3, 31)
    assert row.available_on == date(2026, 4, 13)
    assert row.value == 3.40
    assert row.unit == "percent year on year"


@pytest.mark.parametrize(
    "text",
    [
        TEXT.replace("2024=100", "2012=100"),
        TEXT.replace("March, 2026 over March, 2025", "February, 2026 over February, 2025"),
        TEXT.replace("Dated 13th April, 2026", ""),
        TEXT + " Dated 14th April, 2026",
        TEXT.replace("3.40% (Provisional)", "104.80 (Index level)"),
    ],
)
def test_cpi_metric_period_and_vintage_cannot_be_guessed(cpi, text):
    with pytest.raises(ValueError):
        cpi.parse_cpi_text(text, source_url="https://mospi.gov.in/original.pdf", month=3)
