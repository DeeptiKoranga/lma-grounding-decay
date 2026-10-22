"""FPI extraction preserves category, USD, reporting-period and candidate boundaries."""

import importlib
import io
import json
import threading
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

HEADER = [
    "Reporting Date",
    "Debt/Equity",
    "Investment Route",
    "Gross Purchases (Rs Crore)",
    "Gross Sales (Rs Crore)",
    "Net Investment (Rs Crore)",
    "Net Investment US($) million",
    "Conversion (1 USD TO INR)*",
]


@pytest.fixture
def cdsl(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.cdsl_series")


def table_row(cells):
    return "<tr>" + "".join(f"<td>{value}</td>" for value in cells) + "</tr>"


def snapshot():
    daily, monthly = [], []
    for category, usd in [
        ("Equity", 10),
        ("Debt", -2),
        ("Debt-VRR", 3),
        ("Debt FAR", 4),
        ("Hybrid", 999),
    ]:
        row = [category, "Stock Exchange", "1000", "900", "100", str(usd)]
        daily.append(row)
        monthly.append(row.copy())
        for rows in (daily, monthly):
            rows.append(["Primary market & others", "0", "0", "0", "0"])
            rows.append(["Sub-total", "1000", "900", "100", str(usd)])
    daily[0].insert(0, "30-04-2026")
    monthly[0].insert(0, "Total for April")
    return (
        "<h4>Daily Trends in FII / FPI Investments upto 30-Apr-2026</h4>"
        "<table>"
        + table_row(HEADER)
        + "".join(table_row(row) for row in daily + monthly)
        + table_row(["Total for 2026", "Equity", "irrelevant annual values"])
        + "</table><table>"
        + table_row(["derivatives", "999999"])
        + "</table>"
    )


def test_only_native_usd_equity_and_all_three_debt_subtotals_are_used(cdsl):
    observation, details = cdsl.parse_month(snapshot(), cutoff=date(2026, 4, 30))
    assert observation.value == 15
    assert observation.on == observation.available_on == date(2026, 4, 30)
    assert observation.unit == "USD million, net"
    assert details["components_usd_million"] == {
        "Equity": "10",
        "Debt": "-2",
        "Debt-VRR": "3",
        "Debt FAR": "4",
    }
    assert details["daily_reporting_rows"] == 1


@pytest.mark.parametrize(
    "before,after,error",
    [
        ("upto 30-Apr-2026", "upto 30-Sep-2026", "requested historical"),
        ("30-04-2026", "29-04-2026", "actual month-end"),
        ("30-04-2026", "30-03-2026", "out-of-period"),
        ("US($) million", "Rs crore", "USD column"),
        ("Debt-VRR", "Other", "investment category"),
        ("<td>100</td>", "<td>200</td>", "inconsistent"),
        ("<td>10</td>", "<td>NaN</td>", "invalid"),
    ],
)
def test_ambiguous_dates_units_categories_and_bad_values_are_rejected(cdsl, before, after, error):
    with pytest.raises(ValueError, match=error):
        cdsl.parse_month(snapshot().replace(before, after), cutoff=date(2026, 4, 30))


def test_daily_monthly_disagreement_is_not_silently_aggregated(cdsl):
    daily, monthly = snapshot().split("Total for April")
    monthly = monthly.replace("<td>10</td>", "<td>20</td>")
    with pytest.raises(ValueError, match="beyond rounding"):
        cdsl.parse_month(daily + "Total for April" + monthly, cutoff=date(2026, 4, 30))


def test_candidate_output_cannot_enter_the_canonical_series_store(cdsl, tmp_path):
    with pytest.raises(ValueError, match="canonical"):
        cdsl.acquire(
            raw_root=tmp_path,
            output=Path("data/series/fpi_flows_usd_mn.csv"),
            report=tmp_path / "report.json",
        )


def test_cache_identity_is_required_and_missing_months_remain_explicit(cdsl, tmp_path):
    cutoff = date(2026, 4, 30)
    raw = snapshot().encode()
    path = tmp_path / f"archive_{cutoff}.html"
    path.write_bytes(raw)
    metadata = {
        "url": cdsl.ARCHIVE_URL,
        "form_url": cdsl.FORM_URL,
        "selectedDate": "April 30, 2026",
        "requested_as_of": str(cutoff),
        "sha256": cdsl.hashlib.sha256(raw).hexdigest(),
    }
    sidecar = path.with_suffix(".meta.json")
    sidecar.write_text(json.dumps(metadata))
    output, report = tmp_path / "candidate.csv", tmp_path / "audit.json"
    result = cdsl.acquire(raw_root=tmp_path, output=output, report=report)
    assert result["observations"] == 1 and not result["accepted_for_historical_use"]
    assert result["status"] == "candidate_only_not_admitted_to_series_store"
    assert len(result["excluded_months"]) == 6
    for changes in ({"sha256": "wrong"}, {"requested_as_of": "2026-09-30"}):
        sidecar.write_text(json.dumps({**metadata, **changes}))
        with pytest.raises(ValueError, match="no eligible"):
            cdsl.acquire(raw_root=tmp_path, output=output, report=report)
        assert "checksum" in json.loads(report.read_text())["excluded_months"][1]["reason"]


@pytest.mark.parametrize("condition", ["budget", "robots", "bytes"])
def test_read_only_filter_respects_robots_request_and_byte_limits(cdsl, condition):
    policy = SimpleNamespace(
        can_fetch=lambda *_: condition != "robots",
        crawl_delay=lambda *_: None,
        request_rate=lambda *_: None,
    )
    opened = []

    def open_request(request, **_):
        opened.append(request)
        return io.BytesIO(b"12345")

    client = SimpleNamespace(
        policy=lambda _: policy,
        _origin=lambda _: "https://www.cdslindia.com",
        _request_lock=threading.Lock(),
        requests=1 if condition == "budget" else 0,
        max_requests=1,
        delay=0,
        last_request={},
        backoff={},
        max_bytes=4,
        opener=SimpleNamespace(open=open_request),
    )
    with pytest.raises(cdsl.FetchError):
        cdsl.submit_date(client, {"selectedDate": "April 30, 2026"})
    assert bool(opened) == (condition == "bytes")
