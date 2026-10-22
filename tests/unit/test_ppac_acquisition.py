"""Monthly basket data must retain its actual release vintage and definition."""

import importlib
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus.series import SeriesStore, read_csv
from schema.tools import GetSeriesArgs

URL = "https://ppac.gov.in/download.php?file=rep_studies/may.pdf"
TITLE = "Snapshot of India's Oil and Gas Data, May 2026"
HIGHLIGHTS = (
    "The price of Brent Crude averaged $107.55/bbl during May'2026. "
    "The Indian basket crude price averaged $106.23/bbl during May'2026 "
    "as against $114.48/bbl during April'2026 and $64.04/bbl during May'2025."
)
TABLE = (
    "25. Information on Prices, Taxes and Under-recoveries/Subsidies "
    "International FOB prices/ Exchange rates ($/bbl) "
    "Particulars 2024-25 2025-26 May-26 Crude oil (Indian Basket) 78.56 70.99 106.23"
)


@pytest.fixture
def ppac(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.ppac_series")


def release(ppac, **changes):
    return ppac.Release(
        **{
            "source": "ppac",
            "url": URL,
            "title": TITLE,
            "published_at": "2026-06-17",
            "publication_date_source": ppac.ARCHIVE_URL,
            **changes,
        }
    )


def parse(ppac, highlights=HIGHLIGHTS, table=TABLE):
    return ppac.parse_prices(
        highlights, table, month=5, year=2026, released=date(2026, 6, 17), url=URL
    )


def test_basket_comparison_prices_are_unavailable_before_the_specific_release(ppac):
    store = SeriesStore({ppac.SERIES_ID: parse(ppac)})
    args = GetSeriesArgs(
        series_id=ppac.SERIES_ID,
        start=date(2026, 3, 1),
        end=date(2026, 5, 31),
        as_of=date(2026, 6, 16),
    )
    assert store.get_series(args, call_id="before").error.kind == "empty_result"
    rows = store.observations(args.model_copy(update={"as_of": date(2026, 6, 17)}))
    assert [(r.on, r.value) for r in rows] == [
        (date(2026, 4, 30), 114.48),
        (date(2026, 5, 31), 106.23),
    ]
    assert all(r.source_url == URL and r.available_on == date(2026, 6, 17) for r in rows)


@pytest.mark.parametrize(
    "highlights,table",
    [
        (HIGHLIGHTS.replace("Indian basket", "Brent"), TABLE),
        (HIGHLIGHTS.replace("price averaged", "price closed"), TABLE),
        (HIGHLIGHTS.replace("April'2026", "March'2026"), TABLE),
        (HIGHLIGHTS.replace("May'2026", "June'2026"), TABLE),
        (HIGHLIGHTS.replace("May'2025", "May'2024"), TABLE),
        (HIGHLIGHTS.replace("$106.23", "$0"), TABLE.replace("106.23", "0")),
        (HIGHLIGHTS, TABLE.replace("106.23", "107.55")),
        (HIGHLIGHTS, TABLE.replace("May-26", "Apr-26")),
        (HIGHLIGHTS + HIGHLIGHTS, TABLE),
        (HIGHLIGHTS, TABLE + TABLE),
    ],
)
def test_wrong_metric_period_ambiguous_or_disagreeing_prices_fail(ppac, highlights, table):
    with pytest.raises(ValueError):
        parse(ppac, highlights, table)


def test_release_date_is_bound_to_the_download_link(ppac):
    html = f'<tr><a href="{URL}">May</a><td data-sort="2026-06-17">17 Jun</td></tr>'
    ppac.check_archive(html, release(ppac))
    with pytest.raises(ValueError, match="publication date"):
        ppac.check_archive(html.replace("2026-06-17", "2026-06-18"), release(ppac))
    with pytest.raises(ValueError, match="publication date"):
        ppac.check_archive(html + html, release(ppac))
    with pytest.raises(ValueError, match="publication date"):
        ppac.check_archive(html.replace(URL, "https://ppac.gov.in/other.pdf"), release(ppac))


def fake_pdf(monkeypatch, modified):
    class PDF:
        needs_pass = False
        metadata = {"creationDate": "D:20260617153110+05'30'", "modDate": modified}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def __len__(self):
            return 2

        def __iter__(self):
            return iter(
                [
                    SimpleNamespace(get_text=lambda **_: HIGHLIGHTS),
                    SimpleNamespace(get_text=lambda **_: TABLE),
                ]
            )

    monkeypatch.setitem(sys.modules, "pymupdf", SimpleNamespace(open=lambda **_: PDF()))


def test_pdf_metadata_cannot_backdate_a_later_copy(ppac, monkeypatch):
    fake_pdf(monkeypatch, "D:20260618120000Z")
    with pytest.raises(ValueError, match="later than its listed release"):
        ppac.extract_snapshot(b"%PDF-fake", release(ppac))
    fake_pdf(monkeypatch, "D:20260617120000Z")
    rows, details = ppac.extract_snapshot(b"%PDF-fake", release(ppac))
    assert len(rows) == 2
    assert details["pdf_file_version_day"] == "2026-06-17"
    assert rows[0].available_on == date(2026, 6, 17)


def test_cached_source_checksum_and_release_identity_are_required(ppac, tmp_path, monkeypatch):
    item = release(ppac)
    manifest = tmp_path / "releases.jsonl"
    manifest.write_text(item.model_dump_json() + "\n")
    archive = tmp_path / "archive.html"
    archive.write_text(f'<tr><a href="{URL}">May</a><td data-sort="2026-06-17">17 Jun</td></tr>')
    key = ppac.hashlib.sha256(URL.encode()).hexdigest()[:20]
    raw = b"%PDF-fake"
    (tmp_path / f"{key}.pdf").write_bytes(raw)
    metadata = {**item.model_dump(), "sha256": ppac.hashlib.sha256(raw).hexdigest()}
    sidecar = tmp_path / f"{key}.meta.json"
    sidecar.write_text(json.dumps(metadata))
    fake_pdf(monkeypatch, "D:20260617120000Z")
    output, report = tmp_path / "basket.csv", tmp_path / "provenance.json"
    kwargs = {
        "manifest": manifest,
        "raw_root": tmp_path,
        "archive": archive,
        "output": output,
        "report": report,
    }
    result = ppac.acquire_from_cache(**kwargs)
    assert result["observations"] == 2 and not result["coverage_complete"]
    assert len(read_csv(output, series_id=ppac.SERIES_ID)) == 2
    original = output.read_bytes()
    for change in ({"sha256": "wrong"}, {"published_at": "2026-06-16"}):
        sidecar.write_text(json.dumps({**metadata, **change}))
        with pytest.raises(ValueError, match="no eligible"):
            ppac.acquire_from_cache(**kwargs)
        assert "checksum" in json.loads(report.read_text())["excluded_sources"][0]["reason"]
        assert output.read_bytes() == original
