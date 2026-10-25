"""Research-topic screening and publisher boilerplate do not manufacture evidence."""

import json
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

from corpus import Document, chunk_document, parse_html
from corpus.quality import rejection_reason
from schema import SourceKind


def doc(title, text, url="https://example.com/news/story", kind=SourceKind.NEWS):
    return Document(
        doc_id="test",
        source="example",
        source_kind=kind,
        url=url,
        published_at=datetime(2026, 3, 12),
        title=title,
        text=text,
        licence_note="test",
    )


def test_topic_screen_distinguishes_policy_from_bank_administration():
    assert rejection_reason(
        doc("RBI defers a director appointment", "The board approved the appointment.")
    )
    assert (
        rejection_reason(
            doc("RBI policy transmission", "Bank deposits have yet to reflect repo rate cuts.")
        )
        is None
    )
    assert rejection_reason(doc("Rupee under pressure", "Oil import costs increased.")) is None


def test_topic_screen_does_not_accept_footer_topic_or_sponsored_copy():
    assert rejection_reason(doc("Sports scores", "Cricket. " * 250 + "Brent crude rose"))
    assert "personal-finance" in rejection_reason(
        doc("Inflation", "Inflation rose", "https://example.com/wealth/savings/story")
    )
    assert "sponsored" in rejection_reason(
        doc("Inflation", "Inflation rose. This article is generated and published by ET Spotlight.")
    )
    assert (
        rejection_reason(
            doc("Official release", "An official fiscal release.", kind=SourceKind.OFFICIAL)
        )
        is None
    )


def test_political_cpi_and_explicit_company_release_are_not_macro_news():
    assert rejection_reason(
        doc(
            "CPI(M) demands TMC account freeze",
            "A party treasurer disputed control of party bank accounts.",
        )
    )
    assert (
        rejection_reason(doc("Consumer Price Index CPI rises", "Consumer inflation increased."))
        is None
    )
    assert "sponsored" in rejection_reason(
        doc(
            "Farm care at one rupee per litre",
            "This is a company press release that is not part of editorial content.",
        )
    )


def test_later_day_revision_cannot_leak_into_an_earlier_as_of_query(monkeypatch):
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: None))
    body = "Higher crude oil prices raised import costs and put pressure on the rupee. " * 4
    html = f'<meta property="article:published_time" content="2026-03-12"><meta property="article:modified_time" content="2026-06-30"><meta property="og:title" content="Crude and rupee"><article><p>{body}</p></article>'
    parsed = parse_html(html, source="example", url="https://example.com/news")
    assert parsed.published_at.date().isoformat() == "2026-03-12"
    assert parsed.modified_at.date().isoformat() == "2026-06-30"
    assert "version screen" in rejection_reason(parsed)
    same_day = parsed.model_copy(update={"modified_at": parsed.published_at})
    assert rejection_reason(same_day) is None


def test_declared_story_body_excludes_current_recommended_news(monkeypatch):
    body = (
        'An analyst said, "Crude oil increased India\'s import costs and weakened the rupee." ' * 5
    )
    future_recommendation = "Today's bond yields rose 62 basis points after a new RBI decision."
    monkeypatch.setitem(
        sys.modules,
        "trafilatura",
        SimpleNamespace(extract=lambda *a, **k: body + "\n" + future_recommendation),
    )
    declaration = {
        "@type": "NewsArticle",
        "headline": "Oil and rupee",
        "datePublished": "2026-03-12",
        "articleBody": body.replace('"', "").replace("'", ""),
    }
    html = (
        '<meta property="article:published_time" content="2026-03-12">'
        + '<meta property="og:title" content="Oil and rupee">'
        + '<script type="application/ld+json">'
        + json.dumps(declaration)
        + "</script>"
    )
    parsed = parse_html(html, source="economic_times", url="https://example.com/news")
    assert parsed.text == body.strip()
    assert future_recommendation not in parsed.text


@pytest.mark.parametrize(
    "source,noise",
    [
        (
            "economic_times",
            "(Catch all the Business News, Breaking News and Latest News Updates on The Economic Times.)",
        ),
        ("economic_times", "Subscribe to The Economic Times Prime and read the ET ePaper online."),
        ("businessline", "Published on March 12, 2026"),
    ],
)
def test_boilerplate_removed_before_offsets_are_computed(monkeypatch, source, noise):
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: None))
    body = "Brent crude raised import costs and the rupee weakened. " * 5
    html = f'<meta property="article:published_time" content="2026-03-12"><meta property="og:title" content="Oil and rupee"><article><p>{body}</p><p>{noise}</p><p>{body}</p></article>'
    parsed = parse_html(html, source=source, url="https://example.com/news")
    assert noise not in parsed.text
    assert len(chunk_document(parsed)) == 2
    for passage in chunk_document(parsed):
        assert parsed.text[passage.char_start : passage.char_end] == passage.text
