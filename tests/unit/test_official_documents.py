"""Official release dates, cached payload integrity and optional PDF extraction."""

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus.documents import chunk_document
from corpus.official import parse_official, pdf_file_day, pdf_paragraphs
from corpus.parser import ParseError
from corpus.quality import rejection_reason
from schema import SourceKind

BODY = (
    "The monetary policy committee reviewed inflation and growth conditions in India. "
    "Higher crude oil prices may raise import costs, while the outlook remains uncertain. "
    "The committee retained the policy repo rate and will monitor incoming economic data."
)


@pytest.fixture(autouse=True)
def semantic_html_only(monkeypatch):
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **kw: None))


@pytest.fixture
def official(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.official")


def html(*, date="2026-04-08", extra=""):
    meta = f'<meta property="article:published_time" content="{date}">' if date else ""
    return (
        f"<html><head>{meta}{extra}</head><main><p>{BODY}</p><p>{BODY}</p></main></html>".encode()
    )


def release(official, name="a", **changes):
    values = {
        "source": "rbi",
        "url": f"https://www.rbi.org.in/{name}.html",
        "title": "Monetary policy statement",
        "published_at": "2026-04-08",
        "publication_date_source": "https://www.rbi.org.in/releases.html",
    }
    values.update(changes)
    return official.Release(**values)


def fake_factory(payload=None):
    clients = []

    class FakeClient:
        def __init__(self, source, **kwargs):
            self.source = source
            self.requests = 0
            self.calls = []
            clients.append(self)

        def get(self, url):
            self.requests += 1
            self.calls.append(url)
            return SimpleNamespace(
                url=url,
                body=html() if payload is None else payload,
                content_type="text/html",
                charset="utf-8",
            )

    return FakeClient, clients


@pytest.mark.parametrize(
    "payload,accepted", [(b"%PDF-1.4 test", True), (b"arbitrary binary", False)]
)
def test_generic_download_mime_requires_a_real_pdf_signature(
    official, tmp_path, monkeypatch, payload, accepted
):
    class Client:
        def __init__(self, source, **kwargs):
            self.requests = 0

        def get(self, url):
            self.requests += 1
            return SimpleNamespace(
                url=url, body=payload, content_type="application/octet-stream", charset="utf-8"
            )

    monkeypatch.setattr(
        official, "parse_official", lambda *args, **kwargs: SimpleNamespace(doc_id="checked")
    )
    counts = official.collect_releases([release(official)], tmp_path, client_factory=Client)[
        "counts"
    ]
    assert counts["accepted" if accepted else "rejected"] == 1
    if accepted:
        meta = json.loads(next(tmp_path.glob("*/*.meta.json")).read_text())
        assert meta["content_type"] == "application/pdf"
        assert next(tmp_path.glob("*/*.pdf")).read_bytes() == payload


def test_official_html_has_official_kind_and_exact_offsets():
    document = parse_official(
        html(),
        source="rbi",
        url="https://www.rbi.org.in/a.html",
        title="  Monetary   policy statement ",
        published_at="2026-04-08",
        content_type="text/html",
    )
    assert document.source_kind is SourceKind.OFFICIAL
    assert document.title == "Monetary policy statement"
    assert document.published_at.date().isoformat() == "2026-04-08"
    passages = chunk_document(document)
    assert len(passages) == 2
    for passage in passages:
        assert passage.source_kind is SourceKind.OFFICIAL
        assert document.text[passage.char_start : passage.char_end] == passage.text


def test_pdf_extraction_can_be_injected_without_heavy_dependency():
    calls = []
    payload = b"%PDF-1.4 synthetic stub"
    document = parse_official(
        payload,
        source="mospi",
        url="https://www.mospi.gov.in/cpi.pdf",
        title="CPI release",
        published_at="2026-04-08",
        content_type="application/pdf",
        extract_pdf=lambda value: calls.append(value) or [BODY, "Second paragraph."],
    )
    assert calls == [payload]
    assert document.text == BODY + "\n\nSecond paragraph."
    assert document.source_kind is SourceKind.OFFICIAL


def test_pdf_backend_missing_dependency_and_non_pdf_are_explicit(monkeypatch):
    with pytest.raises(ParseError, match="not a PDF"):
        pdf_paragraphs(b"<html>Not a PDF</html>")
    monkeypatch.setitem(sys.modules, "pymupdf", None)
    with pytest.raises(ParseError, match="optional pymupdf"):
        pdf_paragraphs(b"%PDF-1.4")


def test_real_small_pdf_if_optional_backend_is_installed():
    pymupdf = pytest.importorskip("pymupdf")
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_textbox(pymupdf.Rect(40, 40, 550, 750), BODY)
        payload = pdf.tobytes()
    paragraphs = pdf_paragraphs(payload)
    assert "monetary policy committee" in " ".join(paragraphs)
    document = parse_official(
        payload,
        source="rbi",
        url="https://www.rbi.org.in/a.pdf",
        title="Policy statement",
        published_at="2026-04-08",
        content_type="application/pdf",
    )
    assert len(document.text) >= 200
    for passage in chunk_document(document):
        assert document.text[passage.char_start : passage.char_end] == passage.text


def test_official_pdf_cannot_backdate_a_later_file_version():
    pymupdf = pytest.importorskip("pymupdf")
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_textbox(pymupdf.Rect(40, 40, 550, 750), BODY)
        pdf.set_metadata(
            {"creationDate": "D:20260408120000+05'30'", "modDate": "D:20261021120000Z"}
        )
        payload = pdf.tobytes()
    document = parse_official(
        payload,
        source="mospi",
        url="https://mospi.gov.in/release.pdf",
        title="Official release",
        published_at="2026-04-08",
        content_type="application/pdf",
    )
    assert document.published_at.date().isoformat() == "2026-04-08"
    assert document.modified_at.date().isoformat() == "2026-10-21"
    assert "version screen" in rejection_reason(document)


@pytest.mark.parametrize("stamp", ["", "D:2026", "D:20260231000000Z", "unknown"])
def test_unknown_pdf_file_day_never_becomes_a_publication_date(stamp):
    assert pdf_file_day(stamp) is None


@pytest.mark.parametrize("date", ["2026-02-28", "2026-10-01"])
def test_out_of_window_release_is_rejected_before_pdf_extraction(date):
    with pytest.raises(ParseError, match="frozen corpus window"):
        parse_official(
            b"not even a pdf",
            source="rbi",
            url="https://www.rbi.org.in/a.pdf",
            title="Policy statement",
            published_at=date,
            content_type="application/pdf",
            extract_pdf=lambda _: pytest.fail("should validate the release date first"),
        )


@pytest.mark.parametrize(
    "payload",
    [
        html(date="2026-10-01"),
        html(
            date=None,
            extra='<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-10-01"}</script>',
        ),
    ],
)
def test_page_publication_metadata_cannot_override_curated_release_date(payload):
    with pytest.raises(ParseError, match="disagrees"):
        parse_official(
            payload,
            source="rbi",
            url="https://www.rbi.org.in/a.html",
            title="Policy statement",
            published_at="2026-04-08",
            content_type="text/html",
        )


def test_modified_date_is_not_a_publication_declaration():
    document = parse_official(
        html(
            date=None,
            extra='<script type="application/ld+json">{"@type":"Article","dateModified":"2026-10-01"}</script>',
        ),
        source="rbi",
        url="https://www.rbi.org.in/a.html",
        title="Policy statement",
        published_at="2026-04-08",
        content_type="text/html",
    )
    assert document.published_at.date().isoformat() == "2026-04-08"


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "mint"},
        {"url": "https://evil.example/release.pdf"},
        {"publication_date_source": "https://evil.example/date"},
        {"published_at": "2026-10-01"},
        {"title": "   "},
    ],
)
def test_release_manifest_validates_publisher_date_and_metadata(official, changes):
    with pytest.raises(ValueError):
        release(official, **changes)


def test_collection_resume_preserves_release_metadata_and_advances(official, tmp_path):
    factory, clients = fake_factory()
    rows = [release(official, "b"), release(official, "a")]
    one = official.collect_releases(rows, tmp_path, max_documents=1, client_factory=factory)
    two = official.collect_releases(rows, tmp_path, max_documents=1, client_factory=factory)
    assert one == {"counts": {"downloaded": 1, "accepted": 1}, "requests": 1}
    assert two == {"counts": {"cached": 1, "accepted": 2, "downloaded": 1}, "requests": 1}
    assert sum(client.requests for client in clients) == 2
    for row in rows:
        key = hashlib.sha256(row.url.encode()).hexdigest()[:20]
        metadata = json.loads((tmp_path / "rbi" / f"{key}.meta.json").read_text())
        assert metadata["accepted"]
        assert metadata["source_kind"] == "official"
        assert metadata["publication_date_source"] == row.publication_date_source
        assert metadata["published_at"] == row.published_at


@pytest.mark.parametrize("corrupt", ["{", "[]", "{}"])
def test_corrupt_cache_metadata_is_logged_and_does_not_abort_next_release(
    official, tmp_path, corrupt
):
    rows = [release(official, "a"), release(official, "b")]
    directory = tmp_path / "rbi"
    directory.mkdir()
    key = hashlib.sha256(rows[0].url.encode()).hexdigest()[:20]
    (directory / f"{key}.meta.json").write_text(corrupt)
    factory, _ = fake_factory()
    result = official.collect_releases(rows, tmp_path, client_factory=factory)
    assert result["counts"] == {"rejected": 1, "downloaded": 1, "accepted": 1}
    events = [
        json.loads(line) for line in (directory / "collection_log.jsonl").read_text().splitlines()
    ]
    assert [event["status"] for event in events] == ["rejected", "accepted"]


def test_checksum_and_changed_release_metadata_are_rejected(official, tmp_path):
    row = release(official)
    factory, _ = fake_factory()
    official.collect_releases([row], tmp_path, client_factory=factory)
    key = hashlib.sha256(row.url.encode()).hexdigest()[:20]
    payload = tmp_path / "rbi" / f"{key}.html"
    payload.write_bytes(b"tampered")
    result = official.collect_releases([row], tmp_path, client_factory=factory)
    assert result["counts"] == {"rejected": 1}
    meta = json.loads(payload.with_suffix(".meta.json").read_text())
    assert not meta["accepted"]
    assert "checksum" in meta["rejection_reason"]
    payload.write_bytes(html())
    changed = release(official, title="A conflicting title")
    result = official.collect_releases([changed], tmp_path, client_factory=factory)
    assert result["counts"] == {"rejected": 1}
    meta = json.loads(payload.with_suffix(".meta.json").read_text())
    assert "metadata changed" in meta["rejection_reason"]


def test_conflicting_manifest_rows_fail_before_any_cache_is_written(official, tmp_path):
    rows = [release(official), release(official, title="Other title")]
    factory, clients = fake_factory()
    with pytest.raises(ValueError, match="conflicting release metadata"):
        official.collect_releases(rows, tmp_path, client_factory=factory)
    assert not clients
    assert list(tmp_path.iterdir()) == []


def test_official_cli_writes_summary_and_reports_invalid_manifest(official, tmp_path, monkeypatch):
    manifest = tmp_path / "releases.jsonl"
    manifest.write_text(release(official).model_dump_json() + "\n")
    raw = tmp_path / "raw"
    calls = []

    def collect(rows, output, **kwargs):
        calls.append((rows, output, kwargs))
        return {"counts": {"accepted": 1}, "requests": 1}

    monkeypatch.setattr(official, "collect_releases", collect)
    monkeypatch.setattr(sys, "argv", ["official", "--manifest", str(manifest), "--raw", str(raw)])
    official.main()
    assert calls[0][0][0] == release(official)
    assert calls[0][1] == raw
    assert json.loads((raw / "official_collection.json").read_text())["counts"]["accepted"] == 1
    manifest.write_text("{}\n")
    with pytest.raises(SystemExit) as exc:
        official.main()
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "options", [{"max_documents": 0}, {"max_requests": 0}, {"delay": -1}, {"delay": float("nan")}]
)
def test_collection_limits_are_validated_even_for_empty_manifest(official, tmp_path, options):
    with pytest.raises(ValueError):
        official.collect_releases([], tmp_path, **options)
