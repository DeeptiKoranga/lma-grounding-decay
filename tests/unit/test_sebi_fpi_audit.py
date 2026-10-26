"""Publication, universe, table-identity and arithmetic guards for SEBI candidates."""

import importlib
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import BadZipFile, ZipFile

import pytest

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@pytest.fixture
def sebi(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.audit_sebi_fpi")


def source(
    tmp_path,
    *,
    modified="2026-07-03",
    usd_label="Net Investment (US $ mn.)",
    net="-100",
    usd="-1.05",
    on=46142,
):
    """Minimal source fixture; the FPI table deliberately has a nonstandard name."""
    path = tmp_path / "source.xlsx"
    values = {
        "A1": "Table 49: Trends in Foreign Portfolio Investment",
        "A2": "Year / Month",
        "E2": usd_label,
    }
    cells = "".join(
        f'<c r="{key}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        for key, value in values.items()
    )
    cells += "".join(
        f'<c r="{key}"><v>{value}</v></c>'
        for key, value in {"A6": on, "B6": 500, "C6": 600, "D6": net, "E6": usd}.items()
    )
    with ZipFile(path, "w") as zipped:
        zipped.writestr(
            "docProps/core.xml",
            f'<core xmlns:d="http://purl.org/dc/terms/"><d:modified>{modified}T12:00:00Z</d:modified></core>',
        )
        zipped.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets><sheet name="historical_table" r:id="rId1"/></sheets></workbook>',
        )
        zipped.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        zipped.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{MAIN}"><sheetData><row>{cells}</row></sheetData></worksheet>',
        )
    return path


def test_finds_table_by_title_and_keeps_native_value(tmp_path, sebi):
    result = sebi.read_table(source(tmp_path), published_on=date(2026, 7, 3))
    assert result["sheet"] == "historical_table"
    assert result["rows"] == [
        {
            "on": "2026-04-30",
            "value": "-1.05",
            "available_on": "2026-07-03",
            "unit": "USD million, net",
            "sheet": "historical_table",
            "cell": "E6",
            "net_investment_inr_crore": "-100",
        }
    ]


def test_later_file_version_cannot_use_earlier_listing_date(tmp_path, sebi):
    with pytest.raises(ValueError, match="postdates listed publication"):
        sebi.read_table(source(tmp_path, modified="2026-09-01"), published_on=date(2026, 8, 27))


def test_rupee_column_cannot_be_substituted_for_native_usd(tmp_path, sebi):
    with pytest.raises(ValueError, match="column label differs"):
        sebi.read_table(
            source(tmp_path, usd_label="Net Investment (INR crore)"), published_on=date(2026, 7, 3)
        )


def test_nonreconciling_total_is_rejected(tmp_path, sebi):
    with pytest.raises(ValueError, match="do not reconcile"):
        sebi.read_table(source(tmp_path, net="-90"), published_on=date(2026, 7, 3))


def test_cached_formula_error_is_not_a_zero(tmp_path, sebi):
    with pytest.raises(ValueError, match="nonnumeric"):
        sebi.read_table(source(tmp_path, usd="#DIV/0!"), published_on=date(2026, 7, 3))


def test_future_observation_is_rejected(tmp_path, sebi):
    with pytest.raises(ValueError, match="observation postdates publication"):
        sebi.read_table(source(tmp_path, on=48000), published_on=date(2026, 7, 3))


def test_truncated_download_is_not_an_empty_history(tmp_path, sebi):
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"PK\x03\x04not-a-complete-workbook")
    with pytest.raises(BadZipFile):
        sebi.read_table(path, published_on=date(2026, 7, 3))
