"""Fetch the three public retrospective inputs with bounded requests and caches.

The PPAC request is its public current-year table filter, not a registered
historical-report download. Provider snapshots do not establish old vintages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .client import ROBOT_AGENT, USER_AGENT, Client, FetchError
from .sources import Source

START = int(datetime(2026, 3, 1, tzinfo=UTC).timestamp())
END = int(datetime(2026, 10, 1, tzinfo=UTC).timestamp())
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?" + urlencode(
    {"period1": START, "period2": END, "interval": "1d", "events": "history"}
)
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDIRLTLT01STM&cosd=2026-03-01&coed=2026-09-30"
PPAC = "https://ppac.gov.in/AjaxController/getInternationalPricesCrudeOil"
PPAC_PARAMS = {"financialYear": "2026-2027", "reportBy": "4", "pageId": "30"}
LIMIT = 4_000_000


def download(*, output: Path, report: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        pass
    else:
        context.load_verify_locations(certifi.where())
    results = []
    for name, suffix, url in [
        ("brent_nymex_chart", ".json", YAHOO),
        ("gsec_oecd_fred_main", ".csv", FRED),
        ("ppac_current_monthly", ".json", PPAC),
    ]:
        path = output / (name + suffix)
        sidecar = output / (name + ".meta.json")
        try:
            if path.exists() and sidecar.exists():
                meta = json.loads(sidecar.read_text())
                if (
                    meta["url"] != url
                    or meta["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()
                ):
                    raise ValueError("retrospective source cache identity/checksum mismatch")
                if name == "ppac_current_monthly" and meta["parameters"] != PPAC_PARAMS:
                    raise ValueError("PPAC public filter parameters differ")
                results.append(
                    {
                        **meta,
                        "source": name,
                        "status": "verified existing cache",
                        "raw": str(path),
                        "requests_this_run": 0,
                    }
                )
                continue
            if path.exists() or sidecar.exists():
                raise ValueError("incomplete existing cache; preserve and inspect it")
            meta = {
                "url": url,
                "checked_at": datetime.now(UTC).isoformat(),
                "purpose": "retrospective capture only; no historical publication date inferred",
            }
            if name == "ppac_current_monthly":
                client = Client(
                    Source("ppac", "https://ppac.gov.in", ("ppac.gov.in",)),
                    max_requests=3,
                    max_bytes=LIMIT,
                )
                policy = client.policy(url)
                if not policy.can_fetch(ROBOT_AGENT, url):
                    raise FetchError("robots.txt disallows the public PPAC table filter")
                time.sleep(client.delay)
                request = Request(
                    url,
                    data=urlencode(PPAC_PARAMS).encode(),
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                response = client.opener.open(request, timeout=25)
                meta["parameters"] = PPAC_PARAMS
            else:
                response = urlopen(
                    Request(
                        url,
                        headers={
                            "User-Agent": USER_AGENT,
                            "Accept": "text/csv" if suffix == ".csv" else "application/json",
                        },
                    ),
                    context=context,
                    timeout=25,
                )
            with response:
                raw = response.read(LIMIT + 1)
                content_type = response.headers.get_content_type()
            if len(raw) > LIMIT:
                raise ValueError("public data response exceeds byte budget")
            if suffix == ".json":
                value = json.loads(raw)
                if name == "brent_nymex_chart" and (
                    value["chart"]["error"] is not None or not value["chart"]["result"]
                ):
                    raise ValueError("Yahoo returned a chart error")
                if name == "ppac_current_monthly" and not isinstance(value.get("result"), dict):
                    raise ValueError("PPAC returned no public table")
            elif not raw.startswith(b"observation_date,INDIRLTLT01STM"):
                raise ValueError("FRED returned an unexpected series/header")
            meta.update(
                status="acquired; retrospective inspection required",
                content_type=content_type,
                bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                path=str(path),
            )
            path.write_bytes(raw)
            sidecar.write_text(json.dumps(meta, indent=2) + "\n")
            results.append({"source": name, **meta})
            time.sleep(2)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            results.append(
                {
                    "source": name,
                    "url": url,
                    "status": "failed; no substitute or access bypass",
                    "reason": str(exc),
                }
            )
    result = {
        "status": "public snapshot acquisition; no historical vintage acceptance",
        "sources": results,
        "complete": all(
            r["status"]
            in {"verified existing cache", "acquired; retrospective inspection required"}
            for r in results
        ),
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("data/raw/track_a_20261025"))
    p.add_argument(
        "--report", type=Path, default=Path("reports/retrospective_source_fetch_20261025.json")
    )
    a = p.parse_args()
    print(json.dumps(download(output=a.output, report=a.report), indent=2))


if __name__ == "__main__":
    main()
