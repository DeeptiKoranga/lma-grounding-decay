"""Track A's ingest contract: publication dates and offsets are evidence-critical."""

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus import Document, ParseError, chunk_document, normalise_paragraphs, parse_html
from corpus.__main__ import main
from corpus.parser import publication_time
from schema import Passage

BODY = (
    "Brent crude rose as oil shipping disruptions raised import costs for India. "
    "The rupee weakened against the dollar as importers sought foreign exchange. "
    "Analysts said the increase could lift headline inflation if prices remain elevated."
)


def article_html(*, stamp="2026-03-12T08:00:00+05:30", extra="", body=BODY):
    meta = f'<meta property="article:published_time" content="{stamp}">' if stamp else ""
    return f'<html><head>{meta}<meta property="og:title" content="Crude and rupee">{extra}</head><body><nav>Noise</nav><article><p>{body}</p><p>{body}</p></article></body></html>'


@pytest.fixture(autouse=True)
def semantic_html_only(monkeypatch):
    # Extraction backend is optional; these assertions test our contract, not its heuristics.
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **kw: None))


def test_normalisation_preserves_paragraphs_and_unicode():
    assert normalise_paragraphs([" Cafe\u0301\t₹100  ", "", " A\n B "]) == "Café ₹100\n\nA B"


def test_repeated_paragraphs_have_distinct_exact_offsets():
    doc = parse_html(article_html(), source="mint", url="https://www.livemint.com/a")
    passages = chunk_document(doc)
    assert len(passages) == 2
    assert passages[0].text == passages[1].text
    assert passages[0].char_start == 0
    assert passages[1].char_start == len(passages[0].text) + 2
    for p in passages:
        assert doc.text[p.char_start : p.char_end] == p.text
        assert Passage.model_validate_json(p.model_dump_json()) == p
    assert "Noise" not in doc.text


def test_normalised_document_is_frozen_and_rejects_bad_text():
    with pytest.raises(ValueError, match="normalised"):
        Document(
            doc_id="x",
            source="mint",
            url="https://www.livemint.com/a",
            published_at=datetime(2026, 3, 12),
            title="x",
            text="bad  spacing",
            licence_note="test",
        )


@pytest.mark.parametrize("stamp", ["2026-02-28T23:00:00+05:30", "2026-10-01"])
def test_ingestion_rejects_out_of_window(stamp):
    with pytest.raises(ValueError, match="frozen corpus"):
        parse_html(article_html(stamp=stamp), source="mint", url="https://www.livemint.com/a")


def test_timezone_is_indian_publication_day():
    assert publication_time("2026-02-28T22:00:00Z").date().isoformat() == "2026-03-01"
    assert publication_time("Thu, 12 Mar 2026 08:00:00 +0530").hour == 8
    assert publication_time("2026-03-12").utcoffset().total_seconds() == 19800


def test_modified_date_cannot_substitute_for_publication():
    modified = '<script type="application/ld+json">{"@type":"NewsArticle","dateModified":"2026-03-12"}</script>'
    with pytest.raises(ParseError, match="missing publication date"):
        parse_html(
            article_html(stamp=None, extra=modified),
            source="mint",
            url="https://www.livemint.com/a",
        )


def test_jsonld_graph_date_and_explicit_paywall():
    record = {
        "@graph": [
            {"@type": ["NewsArticle"], "datePublished": "2026-03-12", "isAccessibleForFree": False}
        ]
    }
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    with pytest.raises(ParseError, match="paywall"):
        parse_html(article_html(extra=extra), source="mint", url="https://www.livemint.com/a")
    record["@graph"][0]["isAccessibleForFree"] = True
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    doc = parse_html(
        article_html(stamp=None, extra=extra), source="mint", url="https://www.livemint.com/a"
    )
    assert doc.published_at.date().isoformat() == "2026-03-12"


def test_short_body_is_rejected():
    with pytest.raises(ParseError, match="short article"):
        parse_html(
            article_html(body="Please subscribe"), source="mint", url="https://www.livemint.com/a"
        )


def test_explicit_related_links_cannot_become_evidence_or_change_offsets():
    extra = (
        "<p>ALSO READ | An unrelated future policy announcement</p>"
        "<p>Read more: Another market headline</p>"
        "<p>Also read: A linked inflation report</p>"
        "<p>Analysts also read the earlier inflation release before commenting.</p>"
    )
    html = article_html().replace("</article>", extra + "</article>")
    doc = parse_html(html, source="economic_times", url="https://economictimes.indiatimes.com/a")
    assert "unrelated future" not in doc.text
    assert "Another market headline" not in doc.text
    assert "linked inflation report" not in doc.text
    assert "Analysts also read the earlier" in doc.text
    for passage in chunk_document(doc):
        assert doc.text[passage.char_start : passage.char_end] == passage.text


def test_invisible_metadata_characters_do_not_discard_visible_source_text():
    body = BODY.replace("oil shipping", "oil\u2060 shipping").replace(
        "lift headline", "lift\u200c headline"
    )
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": body,
    }
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    doc = parse_html(
        article_html(extra=extra),
        source="economic_times",
        url="https://economictimes.indiatimes.com/a",
    )
    assert doc.text == BODY + "\n\n" + BODY
    assert "\u2060" not in doc.text


def test_visible_lead_is_recovered_without_copying_metadata_or_recommendations():
    lead = "Mumbai: " + BODY
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": lead + " " + BODY,
    }
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    html = article_html(extra=extra).replace(
        "<article>",
        f'<div class="artText">{lead}<br><p>Unrelated recommendation</p></div><article>',
    )
    doc = parse_html(html, source="economic_times", url="https://economictimes.indiatimes.com/a")
    assert doc.text.startswith(lead + "\n\n")
    assert "Unrelated recommendation" not in doc.text
    assert doc.text.count("Mumbai:") == 1


def test_unmatched_visible_lead_cannot_be_added_to_current_story():
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": BODY,
    }
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    html = article_html(extra=extra).replace(
        "<article>", f'<div class="artText">Unrelated story: {BODY}<br></div><article>'
    )
    doc = parse_html(html, source="economic_times", url="https://economictimes.indiatimes.com/a")
    assert "Unrelated story" not in doc.text


def test_visible_body_recovers_middle_and_end_across_widgets_and_lists(monkeypatch):
    middle = 'A trader said, "Dollar demand from arbitrage positions pressured the rupee."'
    ending = "If oil pressure persists, the recovery in foreign bond flows could dissipate."
    bullet = "Refiners sought alternative crude suppliers."
    body = BODY + middle + bullet + ending
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": body + " Metadata-only fact.",
    }
    extra = f'<script type="application/ld+json">{json.dumps(record)}</script>'
    html = article_html(extra=extra).replace(
        "<article>",
        f'<div class="artText">{BODY}<br><div class="advert">Unrelated ad</div>'
        f"{middle}<br><script>Fake instruction</script><ol><li>{bullet}</li></ol>"
        f'<div style="display:none">Metadata-only fact.</div>{ending}</div><article>',
    )
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: BODY))
    doc = parse_html(html, source="economic_times", url="https://example.com/a")
    assert doc.text.split("\n\n") == [BODY, middle, bullet, ending]
    assert "Unrelated ad" not in doc.text and "Metadata-only" not in doc.text
    assert "Fake instruction" not in doc.text
    assert all(doc.text[p.char_start : p.char_end] == p.text for p in chunk_document(doc))


def test_mint_brand_suffix_cannot_disable_body_guard_or_admit_author_bio(monkeypatch):
    bio = "Reporter covers monetary policy, inflation, trade and the rupee. " * 3
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": BODY,
    }
    html = article_html(extra=f'<script type="application/ld+json">{json.dumps(record)}</script>')
    html = html.replace('content="Crude and rupee"', 'content="Crude and rupee | Mint"')
    monkeypatch.setitem(
        sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: BODY + "\n" + bio)
    )
    doc = parse_html(html, source="mint", url="https://www.livemint.com/a")
    assert doc.text == BODY


def test_declared_body_cannot_admit_a_custom_related_story_link(monkeypatch):
    related = "India exports goods under a new trade agreement"
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": BODY + related,
    }
    html = article_html(extra=f'<script type="application/ld+json">{json.dumps(record)}</script>')
    html = html.replace(
        "<article>",
        f'<div class="artText">{BODY}<br><a data-type="tilCustomLink" '
        f'href="/different-story">{related}</a></div><article>',
    )
    monkeypatch.setitem(
        sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: BODY + "\n" + related)
    )
    doc = parse_html(html, source="economic_times", url="https://example.com/a")
    assert doc.text == BODY


def test_publisher_promotion_is_not_evidence_without_a_declared_body(monkeypatch):
    promotion = "More stories like this are available on bloomberg.com"
    monkeypatch.setitem(
        sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **k: BODY + "\n" + promotion)
    )
    doc = parse_html(article_html(), source="businessline", url="https://example.com/a")
    assert doc.text == BODY


def test_custom_link_is_removed_before_a_backend_can_merge_it_into_prose(monkeypatch):
    related = "Unrelated trade headline repeated inside the publisher declared article body"
    ending = "The central bank said it would monitor incoming data before making further policy decisions."
    record = {
        "@type": "NewsArticle",
        "headline": "Crude and rupee",
        "datePublished": "2026-03-12",
        "articleBody": BODY + related + ending,
    }
    html = article_html(extra=f'<script type="application/ld+json">{json.dumps(record)}</script>')
    html = html.replace(
        "<article>",
        f'<div class="artText">{BODY}<br><a data-type="tilCustomLink" href="/other"><span>{related}</span></a><br>{ending}</div><article>',
    )

    def extract(cleaned, **kwargs):
        assert 'data-type="tilCustomLink"' not in cleaned
        assert related in cleaned  # Original JSON-LD declaration remains intact.
        return BODY + "\n" + ending

    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=extract))
    doc = parse_html(html, source="economic_times", url="https://example.com/a")
    assert doc.text.split("\n\n") == [BODY, ending]


def test_custom_link_filter_preserves_all_other_html_including_bare_ampersands():
    from corpus.parser import CustomLinkFilter

    anchor = '<a data-type="tilCustomLink" href="/other"><span>Other headline</span></a>'
    html = (
        "<!DOCTYPE html>\n<P>S&P/ASX &amp; oil &#8377 without rewriting.</P>"
        + anchor
        + '<script>{"articleBody":"S&P/ASX"}</script>'
    )
    cleaned = CustomLinkFilter()
    cleaned.feed(html)
    assert "".join(cleaned.output) == html.replace(anchor, "<br>")


def test_rebuild_pipeline_only_uses_accepted_payloads(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    from scripts.fetch.client import Response
    from scripts.fetch.collect import collect
    from scripts.fetch.sources import SOURCES

    class FakeClient:
        source = SOURCES["mint"]

        def get(self, url):
            body = (
                article_html(body="A cricket score " * 40).replace(
                    "Crude and rupee", "Cricket scores"
                )
                if url.endswith("sport")
                else article_html()
            )
            return Response(url, body.encode(), "text/html", "utf-8")

    raw = tmp_path / "raw"
    output = tmp_path / "interim"
    collect(
        FakeClient(),
        ["https://www.livemint.com/macro", "https://www.livemint.com/sport"],
        raw / "mint",
        max_articles=10,
    )
    monkeypatch.setattr(sys, "argv", ["corpus", "--raw", str(raw), "--output", str(output)])
    main()
    docs = [
        Document.model_validate_json(line)
        for line in (output / "documents.jsonl").read_text().splitlines()
    ]
    passages = [
        Passage.model_validate_json(line)
        for line in (output / "articles.jsonl").read_text().splitlines()
    ]
    assert len(docs) == 1
    assert len(passages) == 2
    assert all(docs[0].text[p.char_start : p.char_end] == p.text for p in passages)
    assert "topic match" in (output / "parse_errors.jsonl").read_text()
