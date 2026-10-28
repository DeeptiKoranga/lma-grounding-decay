"""Audit dated SEBI FPI annexures without substituting their broader total series.

Read XLSX XML directly, verify cached source hashes and publication/version dates,
and retain the official total as a separately defined research candidate. The
canonical equity-plus-debt news series is never written by this command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PUBLICATIONS = {
    1: ("2026-09-23", "sebi-bulletin-september-2026_104675.html"),
    2: ("2026-08-27", "sebi-bulletin-august-2026_104049.html"),
    3: ("2026-07-27", "sebi-bulletin-july-2026_103048.html"),
    4: ("2026-07-03", "sebi-bulletin-jun-2026_102586.html"),
    5: ("2026-06-12", "sebi-bulletin-may-2026_102098.html"),
    6: ("2026-04-30", "sebi-bulletin-april-2026_101194.html"),
    7: ("2026-03-27", "sebi-bulletin-march2026_100626.html"),
}


def read_table(path: Path, *, published_on: date) -> dict:
    with ZipFile(path) as archive:
        if bad := archive.testzip():
            raise ValueError(f"XLSX checksum failure: {bad}")
        core = ET.fromstring(archive.read("docProps/core.xml"))
        modified = core.find("{http://purl.org/dc/terms/}modified")
        if modified is None or not modified.text:
            raise ValueError("missing file-version modification date")
        modified_on = date.fromisoformat(modified.text[:10])
        if modified_on > published_on:
            raise ValueError("file version postdates listed publication; no backdating")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(s.itertext()) for s in shared.findall(f"{{{MAIN}}}si")]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        matches = []
        for sheet in workbook.findall(f"{{{MAIN}}}sheets/{{{MAIN}}}sheet"):
            target = targets[sheet.attrib[f"{{{REL}}}id"]]
            member = target.lstrip("/") if target.startswith("/") else "xl/" + target
            node = ET.fromstring(archive.read(member))
            cells = {}
            for cell in node.findall(f".//{{{MAIN}}}c"):
                value = cell.find(f"{{{MAIN}}}v")
                kind = cell.get("t")
                if kind == "inlineStr":
                    value = cell.find(f"{{{MAIN}}}is")
                    decoded = "".join(value.itertext()) if value is not None else ""
                elif value is None or value.text is None:
                    continue
                else:
                    decoded = strings[int(value.text)] if kind == "s" else value.text
                cells[cell.attrib["r"]] = decoded
            title = cells.get("A1", "").strip()
            if re.fullmatch(r"Table\s+\d+:\s*Trends in Foreign Portfolio Investment", title):
                matches.append((sheet.attrib["name"], title, cells))
        if len(matches) != 1:
            raise ValueError("expected one FPI trends table identified by title, not sheet number")
        name, title, cells = matches[0]
        if cells.get("A2", "").strip() != "Year / Month" or not re.fullmatch(
            r"Net Investment\s*\(US\s*\$\s*mn\.\)", cells.get("E2", "").strip()
        ):
            raise ValueError("FPI date or native USD-million column label differs")
        rows = []
        for address, value in cells.items():
            if not re.fullmatch(r"A\d+", address) or not re.fullmatch(r"\d+(?:\.\d+)?", value):
                continue
            serial = Decimal(value)
            if not 45000 <= serial <= 50000 or serial != int(serial):
                continue
            on = date(1899, 12, 30) + timedelta(days=int(serial))
            if on > published_on:
                raise ValueError("FPI observation postdates publication")
            suffix = address[1:]
            try:
                purchase, sales, net, usd = [Decimal(cells[c + suffix]) for c in "BCDE"]
            except (InvalidOperation, KeyError) as exc:
                raise ValueError("missing or nonnumeric FPI source value") from exc
            if not all(v.is_finite() for v in (purchase, sales, net, usd)):
                raise ValueError("nonfinite FPI source value")
            if abs(purchase - sales - net) > Decimal("0.02"):
                raise ValueError("gross purchases/sales do not reconcile with net INR value")
            if date(2026, 3, 1) <= on <= date(2026, 9, 30):
                rows.append(
                    {
                        "on": on.isoformat(),
                        "value": str(usd),
                        "available_on": published_on.isoformat(),
                        "unit": "USD million, net",
                        "sheet": name,
                        "cell": "E" + suffix,
                        "net_investment_inr_crore": str(net),
                    }
                )
        return {"sheet": name, "title": title, "file_modified_on": str(modified_on), "rows": rows}


def audit(raw: Path, output: Path) -> dict:
    listing = json.loads((raw / "sebi_listing.meta.json").read_text())
    assert hashlib.sha256((raw / "sebi_listing.html").read_bytes()).hexdigest() == listing["sha256"]
    listing_html = (raw / "sebi_listing.html").read_text()
    sources, first = [], {}
    for number, (published, slug) in PUBLICATIONS.items():
        path = raw / f"sebi_annexure_{number}.xlsx"
        meta = json.loads(path.with_suffix(".meta.json").read_text())
        row = {"source_url": meta["url"], "published_on": published, "sha256": meta.get("sha256")}
        try:
            if slug not in listing_html or meta["url"] not in listing_html:
                raise ValueError(
                    "source asset or publication is absent from archived publisher listing"
                )
            if hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
                raise ValueError("source file checksum differs from acquisition record")
            table = read_table(path, published_on=date.fromisoformat(published))
            row.update(status="valid dated total-series candidate; different universe", **table)
            for observation in table["rows"]:
                previous = first.get(observation["on"])
                if previous is None or observation["available_on"] < previous["available_on"]:
                    first[observation["on"]] = {
                        **observation,
                        "source_url": meta["url"],
                        "source_sha256": meta["sha256"],
                    }
        except (OSError, BadZipFile, ValueError, KeyError, ET.ParseError) as exc:
            row.update(status="excluded", reason=str(exc))
        sources.append(row)
    result = {
        "checked_on": "2026-10-26",
        "definition": "SEBI/NSDL published total FPI net investment, including mutual-fund investment; not the canonical equity-plus-debt news measure.",
        "definition_source": "SEBI September 2026 Bulletin, PDF page 13 footnote 4 and page 14 chart legend.",
        "definition_source_url": "https://www.sebi.gov.in/sebi_data/attachdocs/sep-2026/1790161152660.pdf",
        "listing": listing,
        "sources": sources,
        "earliest_valid_captured_vintages": [first[k] for k in sorted(first)],
        "canonical_observations_added": 0,
        "canonical_series_changed": False,
        "raw_assets_redistributed": False,
        "research_acceptance": False,
        "limitations": [
            "The broader universe cannot be mixed with the existing equity-plus-debt series.",
            "Listing dates and file metadata detect known later versions; unchanged historical bytes are not independently certified.",
            "Monthly data cannot confirm a daily anchor or imply a causal edge.",
            "No corrupted workbook, formula error, missing month or later file version becomes a zero or an earlier observation.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.raw, args.output)
    print(
        json.dumps(
            {
                "assets_checked": len(result["sources"]),
                "monthly_candidates": len(result["earliest_valid_captured_vintages"]),
                "canonical_observations_added": 0,
            }
        )
    )
