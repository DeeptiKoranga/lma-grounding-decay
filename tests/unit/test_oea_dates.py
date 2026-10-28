"""The actual embargo day, rather than a PDF filename month, dates releases."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def oea(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.oea_releases")


def test_embargo_publication_day_is_separate_from_observation_month(oea):
    text = "EMBARGO ADVISORY This press release is embargoed till 12:00 Noon of 15th June 2026. Estimates for May 2026."
    assert oea.embargo_date(text) == "2026-06-15"


@pytest.mark.parametrize(
    "text",
    [
        "Estimates for May 2026",
        "EMBARGO ADVISORY Release 31st February 2026",
        "EMBARGO ADVISORY Release 14th October 2026",
    ],
)
def test_unknown_invalid_and_out_of_window_publication_dates_fail(oea, text):
    with pytest.raises(ValueError):
        oea.embargo_date(text)
