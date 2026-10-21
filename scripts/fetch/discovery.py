"""Sitemap indexes, urlsets, RSS and Atom; lastmod is never a publication date."""

from __future__ import annotations

import gzip
import io
import re
from datetime import date
from heapq import heappop, heappush
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from schema.models import CORPUS_END, CORPUS_START

from .client import FetchError, Response

MONTH_NAMES = {
    name: index
    for index, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}
MONTH_PATTERN = "|".join(sorted(MONTH_NAMES, key=lambda name: (-len(name), name)))
ARCHIVE_MONTH = re.compile(
    rf"(?<![a-z0-9])(?P<year>(?:19|20)\d{{2}})[-_/]"
    rf"(?P<month>0?[1-9]|1[0-2]|{MONTH_PATTERN})(?![a-z0-9])",
    re.IGNORECASE,
)
COMPACT_ARCHIVE_DAY = re.compile(r"(?<!\d)((?:19|20)\d{2})(0[1-9]|1[0-2])([0-3]\d)(?!\d)")


def archive_month(url: str) -> date | None:
    """Recognise explicit archive year/months only for crawl scheduling.

    Unknown or ambiguous patterns remain eligible. A sitemap's lastmod and an
    article URL never supply a document publication date; parse_html still has
    to validate publisher metadata before admitting any article to the corpus.
    """
    parts = urlsplit(url)
    months = set()
    for match in ARCHIVE_MONTH.finditer(unquote(parts.path)):
        month = match["month"].casefold()
        months.add(
            date(int(match["year"]), int(month) if month.isdigit() else MONTH_NAMES[month], 1)
        )
    for match in COMPACT_ARCHIVE_DAY.finditer(unquote(parts.path)):
        try:
            stamp = date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            continue
        months.add(stamp.replace(day=1))
    query = dict(parse_qsl(parts.query))
    year, month = query.get("year", ""), query.get("month", "").casefold()
    if re.fullmatch(r"(?:19|20)\d{2}", year):
        number = int(month) if month.isdigit() and len(month) <= 2 else MONTH_NAMES.get(month)
        if number is not None and 1 <= number <= 12:
            months.add(date(int(year), number, 1))
    return next(iter(months)) if len(months) == 1 else None


def _feed_priority(url: str) -> tuple[int, int, str] | None:
    month = archive_month(url)
    if month is None:
        return (1, 0, url)
    start = CORPUS_START.replace(day=1)
    end = CORPUS_END.replace(day=1)
    if not start <= month <= end:
        return None
    return (0, month.toordinal(), url)


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_") and k != "fbclid"]
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", query, ""))


def parse_feed(response: Response) -> tuple[list[str], list[str]]:
    raw = response.body
    if raw.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(24_000_001)
    if len(raw) > 24_000_000:
        raise FetchError("expanded feed exceeds 24 MB")
    root = ET.fromstring(raw)
    kind = root.tag.rsplit("}", 1)[-1]
    feeds, urls = [], []
    if kind in {"sitemapindex", "urlset"}:
        for entry in root:
            location = entry.find("{*}loc")
            if location is not None and location.text:
                location_url = location.text.strip()
                path = urlsplit(location_url).path.lower()
                # BusinessLine's archive index is a urlset of daily sitemap URLs.
                # Treat only explicit sitemap XML paths as nested discovery feeds.
                nested_sitemap = "sitemap" in path and path.endswith((".xml", ".xml.gz"))
                (feeds if kind == "sitemapindex" or nested_sitemap else urls).append(location_url)
    elif kind == "rss":
        urls = [e.text.strip() for e in root.findall("./channel/item/link") if e.text]
    elif kind == "feed":
        for entry in root.findall("{*}entry"):
            for link in entry.findall("{*}link"):
                if link.get("rel", "alternate") == "alternate" and link.get("href"):
                    urls.append(link.get("href"))
                    break
    else:
        raise FetchError(f"unsupported discovery document: {kind}")
    return feeds, urls


def discover(client, feeds: list[str], *, max_feeds: int, on_error) -> list[str]:
    if max_feeds < 0:
        raise ValueError("max_feeds must be nonnegative")
    queue = []
    scheduled, urls = set(), set()

    def schedule(candidates):
        for candidate in candidates:
            try:
                feed = canonical_url(candidate)
                if feed in scheduled or not client.source.accepts(feed):
                    continue
                priority = _feed_priority(feed)
            except ValueError as exc:
                on_error(candidate, str(exc))
                continue
            scheduled.add(feed)
            if priority is not None:
                heappush(queue, priority)

    schedule(feeds)
    attempted = 0
    while queue and attempted < max_feeds:
        _, _, feed = heappop(queue)
        attempted += 1
        try:
            children, articles = parse_feed(client.get(feed))
        except (ValueError, OSError, ET.ParseError) as exc:
            on_error(feed, str(exc))
            continue
        schedule(children)
        urls.update(canonical_url(url) for url in articles if client.source.accepts(url))
    return sorted(urls)
