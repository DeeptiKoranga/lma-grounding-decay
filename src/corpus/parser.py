"""Conservative HTML ingestion. Unknown dates and explicit paywalls are rejected."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from schema import SourceKind

from .documents import Document, document_id, normalise_paragraphs

INDIA = ZoneInfo("Asia/Kolkata")
ARTICLE_TYPES = {"NewsArticle", "Article", "ReportageNewsArticle", "AnalysisNewsArticle"}


class ParseError(ValueError):
    """The payload cannot safely become evidence."""


def is_navigation_paragraph(text: str) -> bool:
    """Recognise explicit related-story labels, without matching body mentions."""
    return bool(re.match(r"^\s*(?:also\s+read|read\s+more)\s*[:|]", text, re.IGNORECASE))


def is_publisher_promotion(text: str) -> bool:
    return bool(
        re.match(
            r"^\s*(?:More stories like this are available on bloomberg\.com|"
            r"Subscribe Now\s*$|Elevate your knowledge with|"
            r"Unlock exclusive stories|Get access to exclusive stories)",
            text,
            re.IGNORECASE,
        )
    )


def _body_key(value: str) -> str:
    # ET removes quotation marks in JSON-LD while retaining them in its visible
    # article. This is a comparison key only; archived evidence stays verbatim.
    value = "".join(
        char
        for char in unicodedata.normalize("NFC", unescape(value))
        if unicodedata.category(char) != "Cf"
    )
    return re.sub(r"""[\s"'\u201c\u201d\u2018\u2019]""", "", value)


class LeadingArticleText(HTMLParser):
    """Read ET's visible text before its first body break, preserving punctuation.

    ET places this text directly in div.artText instead of a paragraph. Some
    extraction backends omit it. Only a prefix matching the declared current
    article body is admitted by the caller; JSON-LD is never copied as evidence.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.finished = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self.finished:
            return
        if self.active and tag in {
            "br",
            "p",
            "div",
            "script",
            "style",
            "aside",
            "ul",
            "ol",
            "table",
        }:
            self.active, self.finished = False, True
        elif tag == "div" and "artText" in dict(attrs).get("class", "").split():
            self.active = True

    def handle_endtag(self, tag):
        if self.active and tag == "div":
            self.active, self.finished = False, True

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


class VisibleArticleBlocks(HTMLParser):
    """Read ET's visible body across widget boundaries without executing scripts."""

    BREAKS = {"br", "p", "div", "h1", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "table"}
    SKIP = {"script", "style", "nav", "aside", "footer", "iframe", "figure"}
    VOID = {
        "br",
        "hr",
        "img",
        "input",
        "meta",
        "link",
        "source",
        "wbr",
        "embed",
        "area",
        "col",
        "param",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.paragraphs = []
        self.started = False
        self.finished = False
        self.related_links = []
        self._related_parts = None

    def flush(self):
        text = " ".join("".join(self.parts).split())
        if text:
            self.paragraphs.append(text)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.started:
            if tag == "div" and "artText" in attrs.get("class", "").split():
                self.started = True
                self.stack.append((tag, False))
            return
        if self.finished:
            return
        if tag == "a" and attrs.get("data-type") == "tilCustomLink":
            self.flush()
            self._related_parts = []
        skipped = self.stack[-1][1] if self.stack else False
        if tag in self.BREAKS and not skipped:
            self.flush()
        hidden = "hidden" in attrs or bool(
            re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", attrs.get("style", ""), re.I)
        )
        if tag not in self.VOID:
            self.stack.append(
                (tag, skipped or hidden or tag in self.SKIP or self._related_parts is not None)
            )

    def handle_endtag(self, tag):
        if not self.stack or self.finished:
            return
        matches = [i for i, (name, _) in enumerate(self.stack) if name == tag]
        if not matches:
            return
        if tag == "a" and self._related_parts is not None:
            self.related_links.append(" ".join("".join(self._related_parts).split()))
            self._related_parts = None
        if tag in self.BREAKS and not self.stack[-1][1]:
            self.flush()
        self.stack = self.stack[: matches[-1]]
        if not self.stack:
            self.flush()
            self.finished = True

    def handle_data(self, data):
        if self._related_parts is not None:
            self._related_parts.append(data)
        if self.stack and not self.stack[-1][1]:
            self.parts.append(data)


def _headline_key(value: str, source: str) -> str:
    if source == "mint":
        value = re.sub(r"\s*\|\s*(?:Mint|Stock Market News|Today News)\s*$", "", value)
    return " ".join(value.split())


def publication_time(value: str) -> datetime:
    """Publication date, never sitemap lastmod/dateModified or a guessed URL date."""
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            stamp = parsedate_to_datetime(value)
        except (TypeError, ValueError) as exc:
            raise ParseError(f"unrecognised publication date: {value!r}") from exc
    # A date with no timezone from an Indian publisher is interpreted in India.
    return stamp.replace(tzinfo=INDIA) if stamp.tzinfo is None else stamp.astimezone(INDIA)


def _articles(value):
    if isinstance(value, list):
        for item in value:
            yield from _articles(item)
    elif isinstance(value, dict):
        kinds = value.get("@type", [])
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if set(kinds) & ARTICLE_TYPES:
            yield value
        for key in ("@graph", "mainEntity"):
            if key in value:
                yield from _articles(value[key])


class ArticleHTML(HTMLParser):
    """Read metadata and semantic article paragraphs without executing page scripts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.jsonld: list[str] = []
        self.paragraphs: list[str] = []
        self._scope: list[str] = []
        self._skip = 0
        self._p: list[str] | None = None
        self._script: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (
                attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or ""
            ).lower()
            self.meta[key] = attrs.get("content") or ""
        if tag in {"article", "main"}:
            self._scope.append(tag)
        if tag in {"script", "style", "nav", "footer", "aside"}:
            self._skip += 1
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._script = []
        if tag == "p" and self._scope and not self._skip:
            self._p = []
        if tag == "br" and self._p is not None:
            self._p.append(" ")

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.jsonld.append("".join(self._script))
            self._script = None
        if tag in {"script", "style", "nav", "footer", "aside"}:
            self._skip = max(0, self._skip - 1)
        if tag == "p" and self._p is not None:
            self.paragraphs.append("".join(self._p))
            self._p = None
        if tag in {"article", "main"} and tag in self._scope:
            self._scope.pop()

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
        if self._p is not None and not self._skip:
            self._p.append(data)


def parse_html(
    html: str,
    *,
    source: str,
    url: str,
    source_kind: SourceKind = SourceKind.NEWS,
    min_chars: int = 200,
) -> Document:
    page = ArticleHTML()
    page.feed(html)
    articles = []
    for script in page.jsonld:
        try:
            articles.extend(_articles(json.loads(script)))
        except (ValueError, TypeError):
            continue
    if any(item.get("isAccessibleForFree") in (False, "false", "False") for item in articles):
        raise ParseError("explicit subscription/paywall metadata; excluded")
    # Meta publication timestamps describe the fetched page. JSON-LD is a fallback.
    published = next(
        (
            page.meta[key]
            for key in ("article:published_time", "datepublished", "pubdate")
            if page.meta.get(key)
        ),
        None,
    )
    if published is None:
        published = next((a["datePublished"] for a in articles if a.get("datePublished")), None)
    if not isinstance(published, str):
        raise ParseError("missing publication date; lastmod/dateModified is not publication")
    published_stamp = publication_time(published)
    modified = page.meta.get("article:modified_time") or page.meta.get("og:updated_time")
    if not modified:
        modified = next(
            (
                a.get("dateModified")
                for a in articles
                if a.get("datePublished") == published and a.get("dateModified")
            ),
            None,
        )
    title = page.meta.get("og:title") or next(
        (a["headline"] for a in articles if isinstance(a.get("headline"), str)), ""
    )
    if not title.strip():
        raise ParseError("missing article title")

    # Optional heavy extra improves body extraction on publishers without <article>.
    try:
        import trafilatura
    except ImportError:
        extracted = None
    else:
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False, favor_precision=True
        )
    paragraphs = extracted.splitlines() if extracted else page.paragraphs
    # Some publisher pages place today's recommended-story summaries inside
    # <article>. When the publisher declares this story's body, use it to screen
    # extraction without replacing the source paragraph boundaries with one blob.
    bodies = {
        _body_key(a["articleBody"])
        for a in articles
        if isinstance(a.get("articleBody"), str)
        and len(a["articleBody"]) >= min_chars
        and isinstance(a.get("headline"), str)
        and _headline_key(a["headline"], source) == _headline_key(title, source)
        and a.get("datePublished")
        and publication_time(a["datePublished"]).date() == published_stamp.date()
    }
    if len(bodies) > 1:
        raise ParseError("conflicting declared bodies for the same article")
    if bodies:
        body = next(iter(bodies))
        paragraphs = [
            p for p in paragraphs if _body_key(p) in body and not is_navigation_paragraph(p)
        ]
        if source == "economic_times":
            visible = VisibleArticleBlocks()
            visible.feed(html)
            related_keys = {_body_key(p) for p in visible.related_links}
            paragraphs = [p for p in paragraphs if _body_key(p) not in related_keys]
            blocks = [
                p
                for p in visible.paragraphs
                if _body_key(p) and _body_key(p) in body and not is_navigation_paragraph(p)
            ]
            joined = _body_key(normalise_paragraphs(blocks))
            narrative_body = body
            for key in related_keys:
                narrative_body = narrative_body.replace(key, "")
            for paragraph in visible.paragraphs:
                if is_navigation_paragraph(paragraph):
                    narrative_body = narrative_body.replace(_body_key(paragraph), "")
            # Replace the backend only when the visible body retains all of its
            # admitted content and recovers additional source text. Never copy
            # missing JSON-LD text into evidence.
            if (
                len(joined) > len(_body_key(normalise_paragraphs(paragraphs)))
                and len(joined) >= 0.9 * len(narrative_body)
                and all(_body_key(p) in joined for p in paragraphs)
            ):
                paragraphs = blocks
            lead = LeadingArticleText()
            lead.feed(html)
            text = " ".join("".join(lead.parts).split())
            key = _body_key(text)
            if (
                len(text) >= 80
                and body.startswith(key)
                and not any(key in _body_key(p) for p in paragraphs)
            ):
                paragraphs.insert(0, text)
    paragraphs = [
        p
        for p in paragraphs
        if not is_navigation_paragraph(p)
        and not is_publisher_promotion(p)
        and not p.strip()
        .lstrip("(")
        .startswith(
            (
                "Catch all the Business News",
                "Subscribe to The Economic Times Prime",
                "Join our ETWealth WhatsApp channel",
                "What's moving Sensex and Nifty",
                "Subscribe to ET Prime and read",
                "Top Trending Stocks:",
                "Listen to this article in summarized format",
                "Catch all the US News, UK News",
                "Download The Economic Times News App",
            )
        )
        and not (source == "businessline" and p.strip().startswith("Published on "))
    ]
    text = normalise_paragraphs(paragraphs)
    if len(text) < min_chars:
        raise ParseError("missing/short article body; possible paywall or extraction failure")
    return Document(
        doc_id=document_id(source, url),
        source=source,
        source_kind=source_kind,
        url=url,
        published_at=published_stamp,
        modified_at=publication_time(modified) if modified else None,
        title=" ".join(title.split()),
        text=text,
        licence_note="Copyright retained by publisher; research use, no redistribution licence assumed.",
    )
