"""Stage monthly net equity-plus-debt FPI flows from CDSL's public archive.

USD subtotals are supplied by the depository. Hybrid, MF, AIF and derivatives
are excluded. Month-end snapshots without a report on that date are omitted;
the selected calendar date alone is not evidence of publication. These dynamic
historical reports lack revision timestamps and are not admitted to SeriesStore.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import time
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request

from corpus.series import Observation, write_csv

from .client import USER_AGENT, Client, FetchError
from .sources import Source

FORM_URL = "https://www.cdslindia.com/Publications/FIITrends.aspx"
ARCHIVE_URL = "https://www.cdslindia.com/Publications/ArchiveDataAfter2009.aspx"
SERIES_ID = "fpi_flows_usd_mn"
COMPONENTS = frozenset({"Equity", "Debt", "Debt-VRR", "Debt FAR"})


class ArchiveHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields: dict[str, str] = {}
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None
        self.table_number = 0
        self.in_first_table = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden" and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")
        if tag == "table":
            self.table_number += 1
            self.in_first_table = self.table_number == 1
        if self.in_first_table and tag == "tr":
            self.row = []
        if self.in_first_table and tag in {"th", "td"}:
            self.cell = []

    def handle_data(self, value):
        self.text.append(value)
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.in_first_table and self.row:
            self.rows.append(self.row)
        if tag == "table":
            self.in_first_table = False


def parse_month(
    html: str, *, cutoff: date, captured_on: date | None = None
) -> tuple[Observation, dict]:
    if captured_on is not None and captured_on < cutoff:
        raise ValueError("retrospective capture cannot precede the observation month end")
    page = ArchiveHTML()
    page.feed(html)
    text = " ".join(" ".join(page.text).split())
    declared = re.findall(
        r"Daily Trends in FII / FPI Investments upto (\d{2}-[A-Za-z]{3}-\d{4})", text
    )
    if len(declared) != 1 or datetime.strptime(declared[0], "%d-%b-%Y").date() != cutoff:
        raise ValueError("CDSL archive did not return the requested historical reporting date")
    if cutoff.day != calendar.monthrange(cutoff.year, cutoff.month)[1]:
        raise ValueError("monthly acquisition requires a calendar month-end cutoff")
    if not page.rows or page.rows[0] != [
        "Reporting Date",
        "Debt/Equity",
        "Investment Route",
        "Gross Purchases (Rs Crore)",
        "Gross Sales (Rs Crore)",
        "Net Investment (Rs Crore)",
        "Net Investment US($) million",
        "Conversion (1 USD TO INR)*",
    ]:
        raise ValueError("unexpected CDSL investment table or USD column definition")
    month_label = f"Total for {calendar.month_name[cutoff.month]}"
    section, category, on = "daily", None, None
    daily: dict[date, dict[str, Decimal]] = {}
    monthly: dict[str, Decimal] = {}
    for original_row in page.rows[1:]:
        row = original_row
        if row[0] == month_label:
            if section != "daily":
                raise ValueError("duplicate monthly FPI section")
            section, category = "monthly", None
            row = row[1:]
        elif row[0].startswith(("Total for ", "Cumulative total")):
            break
        elif re.fullmatch(r"\d{2}-\d{2}-\d{4}", row[0]):
            if section != "daily":
                raise ValueError("daily row inside monthly FPI totals")
            on = datetime.strptime(row[0], "%d-%m-%Y").date()
            if (on.year, on.month) != (cutoff.year, cutoff.month) or on > cutoff or on in daily:
                raise ValueError("duplicate or out-of-period FPI reporting date")
            daily[on] = {}
            category = None
            row = row[1:]
        if row[0] in COMPONENTS | {"Hybrid", "MF", "AIF"}:
            category = row[0]
        elif len(row) >= 6 and row[1] == "Stock Exchange":
            raise ValueError("unexpected FPI investment category")
        elif row[0] == "Sub-total" and category in COMPONENTS:
            if len(row) != 5:
                raise ValueError("unexpected FPI subtotal column count")
            try:
                bought, sold, net, usd = [Decimal(cell.replace(",", "")) for cell in row[1:]]
            except InvalidOperation as exc:
                raise ValueError("nonnumeric FPI subtotal") from exc
            if not all(x.is_finite() for x in (bought, sold, net, usd)) or abs(
                bought - sold - net
            ) > Decimal("0.02"):
                raise ValueError("invalid or inconsistent FPI subtotal")
            target = monthly if section == "monthly" else daily.get(on)
            if target is None or category in target:
                raise ValueError("duplicate or undated FPI subtotal")
            target[category] = usd
    if not daily or (captured_on is None and max(daily) != cutoff):
        raise ValueError(
            "no actual month-end reporting row; selected calendar date cannot date publication"
        )
    if set(monthly) != COMPONENTS or any(set(values) != COMPONENTS for values in daily.values()):
        raise ValueError("missing equity or debt category in FPI totals")
    tolerance = Decimal(len(daily) + 1) * Decimal("0.005")
    for component in COMPONENTS:
        if (
            abs(monthly[component] - sum(values[component] for values in daily.values()))
            > tolerance
        ):
            raise ValueError("daily and monthly USD FPI subtotals disagree beyond rounding")
    observation = Observation(
        on=cutoff,
        available_on=captured_on or cutoff,
        value=float(sum(monthly.values())),
        source_url=ARCHIVE_URL,
        unit="USD million, net",
    )
    return observation, {
        "availability_basis": (
            "actual capture date; no historical release/vintage claim"
            if captured_on is not None
            else "candidate reporting date; historical vintage unverified"
        ),
        "retrospective_only": captured_on is not None,
        "components_usd_million": {key: str(monthly[key]) for key in sorted(COMPONENTS)},
        "daily_reporting_rows": len(daily),
        "last_reporting_date": str(max(daily)),
        "monthly_label": month_label,
        "daily_monthly_rounding_tolerance_usd_million": str(tolerance),
    }


def submit_date(client: Client, fields: dict[str, str]) -> bytes:
    """Read-only public report filter, paced and bounded like the GET collector."""
    policy = client.policy(FORM_URL)
    if not policy.can_fetch("LmaGroundingResearch", FORM_URL):
        raise FetchError("robots.txt disallows the CDSL report filter")
    origin = client._origin(FORM_URL)
    with client._request_lock:
        if client.requests >= client.max_requests:
            raise FetchError("request budget exhausted")
        interval = max(client.delay, policy.crawl_delay("LmaGroundingResearch") or 0)
        rate = policy.request_rate("LmaGroundingResearch")
        if rate:
            interval = max(interval, rate.seconds / rate.requests)
        remaining = (
            max(client.last_request.get(origin, 0) + interval, client.backoff.get(origin, 0))
            - time.monotonic()
        )
        if remaining > 0:
            time.sleep(remaining)
        client.requests += 1
        client.last_request[origin] = time.monotonic()
    request = Request(
        FORM_URL,
        data=urlencode(fields).encode(),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with client.opener.open(request, timeout=25) as response:
        raw = response.read(client.max_bytes + 1)
    if len(raw) > client.max_bytes:
        raise FetchError("CDSL filter response exceeds the byte budget")
    return raw


def download_month(client: Client, *, cutoff: date, raw_root: Path) -> None:
    path = raw_root / f"archive_{cutoff}.html"
    if path.exists() and path.with_suffix(".meta.json").exists():
        return
    form = ArchiveHTML()
    form.feed(client.get(FORM_URL).body.decode("utf-8"))
    if not {"__VIEWSTATE", "__EVENTVALIDATION"} <= form.fields.keys():
        raise ValueError("CDSL public date form has changed")
    selection = f"{calendar.month_name[cutoff.month]} {cutoff.day}, {cutoff.year}"
    response = submit_date(
        client, {**form.fields, "grpArchive": "rdbAfter", "selectedDate": selection, "ctl30": "Go"}
    )
    if b"window.open('ArchiveDataAfter2009.aspx'" not in response:
        raise ValueError("CDSL date filter did not select the requested archive")
    archived = client.get(ARCHIVE_URL)
    # The session holds the selected date. Validate returned content on import;
    # a successful HTTP response alone does not establish historical identity.
    raw_root.mkdir(parents=True, exist_ok=True)
    path.write_bytes(archived.body)
    path.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "url": ARCHIVE_URL,
                "form_url": FORM_URL,
                "selectedDate": selection,
                "requested_as_of": str(cutoff),
                "sha256": hashlib.sha256(archived.body).hexdigest(),
                "bytes": len(archived.body),
                "fetched_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n"
    )


def acquire(*, raw_root: Path, output: Path, report: Path, download: bool = False) -> dict:
    if output.resolve().is_relative_to(Path("data/series").resolve()):
        raise ValueError(
            "unverified FPI vintages must remain outside the canonical data/series store"
        )
    client = None
    if download:
        client = Client(
            Source("cdsl", "https://www.cdslindia.com", ("www.cdslindia.com",)),
            max_requests=30,
            max_bytes=4_000_000,
        )
        client.opener.add_handler(HTTPCookieProcessor(CookieJar()))
    observations, sources, excluded = [], [], []
    for month in range(3, 10):
        cutoff = date(2026, month, calendar.monthrange(2026, month)[1])
        path = raw_root / f"archive_{cutoff}.html"
        try:
            if client:
                download_month(client, cutoff=cutoff, raw_root=raw_root)
            raw = path.read_bytes()
            metadata = json.loads(path.with_suffix(".meta.json").read_text())
            selection = f"{calendar.month_name[month]} {cutoff.day}, 2026"
            if any(
                metadata.get(key) != expected
                for key, expected in {
                    "url": ARCHIVE_URL,
                    "form_url": FORM_URL,
                    "selectedDate": selection,
                    "requested_as_of": str(cutoff),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }.items()
            ):
                raise ValueError("CDSL cached snapshot identity/checksum mismatch")
            row, details = parse_month(raw.decode("utf-8"), cutoff=cutoff)
            observations.append(row)
            sources.append(
                {
                    **metadata,
                    "raw_path": str(path),
                    "observation": row.model_dump(mode="json"),
                    **details,
                }
            )
        except (ValueError, OSError, KeyError) as exc:
            excluded.append({"month": f"2026-{month:02d}", "reason": str(exc)})
    summary = {
        "series_id": SERIES_ID,
        "observations": len(observations),
        "status": "candidate_only_not_admitted_to_series_store",
        "accepted_for_historical_use": False,
        "coverage_complete": len(observations) == 7,
        "frequency": "monthly net flows by custodian reporting month, not trading month",
        "definition": "Equity + Debt + Debt-VRR + Debt FAR, native USD million; excludes Hybrid, MF, AIF and derivatives",
        "candidate_availability": "archive-declared month-end reporting date, additionally required as an actual table reporting row; value vintage still unverified",
        "limitation": "Historical archive is generated on request; CDSL supplies no revision timestamps. Historical vintage stability is unverified.",
        "sources": sources,
        "excluded_months": excluded,
        "use": "move_confirmation_only",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n")
    if not observations:
        raise ValueError(f"no eligible monthly FPI observations; inspect {report}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, series_id=SERIES_ID, records=observations)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw/series/cdsl"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/series/fpi_flows_usd_mn_candidate.csv")
    )
    parser.add_argument("--report", type=Path, default=Path("reports/fpi_acquisition_review.json"))
    parser.add_argument(
        "--download",
        action="store_true",
        help="Use CDSL's public read-only date filter; otherwise require verified local caches",
    )
    args = parser.parse_args()
    try:
        result = acquire(
            raw_root=args.raw, output=args.output, report=args.report, download=args.download
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in result.items() if key != "sources"}, indent=2))


if __name__ == "__main__":
    main()
