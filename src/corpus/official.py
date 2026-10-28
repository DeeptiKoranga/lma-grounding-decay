"""Official HTML/PDF ingestion using explicitly sourced publication metadata.

PDF creation/modification timestamps describe a file, not its publication. A
curated release-list entry must supply the publication date and its source URL.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime

from schema import CORPUS_END, CORPUS_START, SourceKind

from .documents import Document, document_id, normalise_paragraphs
from .parser import ArticleHTML, ParseError, publication_time


def _publication_dates(value):
    """Read publication declarations for the page, not modified/linked content."""
    if isinstance(value, list):
        for item in value:
            yield from _publication_dates(item)
    elif isinstance(value, dict):
        if isinstance(value.get("datePublished"), str):
            yield value["datePublished"]
        for key in ("@graph", "mainEntity"):
            if key in value:
                yield from _publication_dates(value[key])


def pdf_file_day(value: str) -> datetime | None:
    """Read a file timestamp only to flag a later copy, never to date publication."""
    match = re.match(r"(?:D:)?(\d{4})(\d{2})(\d{2})", value or "")
    if not match:
        return None
    try:
        return publication_time("-".join(match.groups()))
    except ValueError:
        return None


def _pdf_content(payload: bytes) -> tuple[list[str], datetime | None]:
    """Extract blocks and a conservative file-version day in one PDF read."""
    if not payload.startswith(b"%PDF-"):
        raise ParseError("payload is not a PDF")
    try:
        import pymupdf
    except ImportError as exc:
        raise ParseError("PDF extraction requires the optional pymupdf dependency") from exc
    try:
        with pymupdf.open(stream=payload, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise ParseError("encrypted PDF; extraction unavailable")
            if pdf.page_count > 500:
                raise ParseError("PDF exceeds the 500-page extraction limit")
            paragraphs = [
                block[4]
                for page in pdf
                for block in page.get_text("blocks", sort=True)
                if block[6] == 0 and block[4].strip()
            ]
            days = [
                stamp
                for field in ("creationDate", "modDate")
                if (stamp := pdf_file_day((pdf.metadata or {}).get(field, "")))
            ]
            return paragraphs, max(days, default=None)
    except ParseError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise ParseError(f"PDF extraction failed: {exc}") from exc


def pdf_paragraphs(payload: bytes) -> list[str]:
    """Extract blocks in reading order; scanned PDFs need a separate OCR review."""
    return _pdf_content(payload)[0]


def parse_official(
    payload: bytes,
    *,
    source: str,
    url: str,
    title: str,
    published_at: str | datetime,
    content_type: str,
    charset: str = "utf-8",
    extract_pdf: Callable[[bytes], list[str]] = pdf_paragraphs,
    min_chars: int = 200,
) -> Document:
    """Use publisher release metadata; never infer a date from a PDF or URL."""
    stamp = publication_time(str(published_at))
    if not CORPUS_START <= stamp.date() <= CORPUS_END:
        raise ParseError("release date is outside the frozen corpus window")
    modified = None
    if content_type == "application/pdf":
        if extract_pdf is pdf_paragraphs:
            paragraphs, modified = _pdf_content(payload)
        else:
            paragraphs = extract_pdf(payload)
    elif content_type in {"text/html", "application/xhtml+xml"}:
        html = payload.decode(charset, errors="replace")
        page = ArticleHTML()
        page.feed(html)
        # Metadata in the page, when present, must agree with the curated listing.
        declared = [
            page.meta[key]
            for key in ("article:published_time", "datepublished", "pubdate")
            if page.meta.get(key)
        ]
        for script in page.jsonld:
            try:
                declared.extend(_publication_dates(json.loads(script)))
            except (ValueError, TypeError):
                continue
        if any(publication_time(value).date() != stamp.date() for value in declared):
            raise ParseError("page publication date disagrees with official release listing")
        updated = page.meta.get("article:modified_time") or page.meta.get("og:updated_time")
        modified = publication_time(updated) if updated else None
        try:
            import trafilatura
        except ImportError:
            extracted = None
        else:
            extracted = trafilatura.extract(
                html, include_comments=False, include_tables=False, favor_precision=True
            )
        paragraphs = extracted.splitlines() if extracted else page.paragraphs
    else:
        raise ParseError(f"unsupported official document type: {content_type}")
    text = normalise_paragraphs(paragraphs)
    if len(text) < min_chars:
        raise ParseError("missing/short official text; scanned PDFs require OCR review")
    return Document(
        doc_id=document_id(source, url),
        source=source,
        source_kind=SourceKind.OFFICIAL,
        url=url,
        published_at=stamp,
        modified_at=modified,
        title=" ".join(title.split()),
        text=text,
        licence_note=(
            "Official publisher retains rights; research use. Check the release's "
            "reproduction policy before redistributing source text."
        ),
    )
