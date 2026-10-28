"""Archive URL hints only plan the crawl; publisher dates admit documents."""

import importlib
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest


@pytest.fixture
def discovery(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("scripts.fetch.discovery")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/sitemap_2026-March.xml", date(2026, 3, 1)),
        ("https://example.com/sitemap-2026-03.xml.gz", date(2026, 3, 1)),
        ("https://example.com/archive/2026/9/sitemap.xml", date(2026, 9, 1)),
        ("https://example.com/archive_2026_Sept.xml", date(2026, 9, 1)),
        ("https://example.com/archive_2026-SEPTEMBER-30.xml", date(2026, 9, 1)),
        ("https://example.com/archive/2026%2F04/sitemap.xml", date(2026, 4, 1)),
        ("https://example.com/archive.xml?year=2026&month=05", date(2026, 5, 1)),
        ("https://example.com/archive.xml?year=2026&month=June", date(2026, 6, 1)),
        ("https://example.com/sitemap-2026.xml", None),
        ("https://example.com/sitemap202603.xml", None),
        ("https://example.com/sitemap/archive/all/20260312_1.xml", date(2026, 3, 1)),
        ("https://example.com/sitemap/archive/all/20260230_1.xml", None),
        ("https://example.com/sitemap-2026-13.xml", None),
        ("https://example.com/sitemap-2026-035.xml", None),
        ("https://example.com/sitemap-2026-Marchandise.xml", None),
        ("https://example.com/sitemap.xml?lastmod=2026-10-01", None),
        ("https://example.com/archive-2026-02_2026-04.xml", None),
    ],
)
def test_explicit_archive_months(discovery, url, expected):
    assert discovery.archive_month(url) == expected


def fake_client(discovery, documents):
    calls = []

    def get(url):
        calls.append(url)
        body = documents[url]
        if isinstance(body, Exception):
            raise body
        return discovery.Response(url, body.encode(), "application/xml", "utf-8")

    return (
        SimpleNamespace(
            source=SimpleNamespace(accepts=lambda url: url.startswith("https://example.com/")),
            get=get,
        ),
        calls,
    )


def sitemap_index(*feeds):
    return (
        "<sitemapindex>"
        + "".join(
            f"<sitemap><loc>{escape(feed)}</loc><lastmod>2026-10-21</lastmod></sitemap>"
            for feed in feeds
        )
        + "</sitemapindex>"
    )


def test_initial_feed_priority_preserves_budget_for_window(discovery):
    root = "https://example.com/sitemap.xml"
    feeds = [
        root,
        "https://example.com/sitemap-2026-October.xml",
        "https://example.com/sitemap-2026-September.xml",
        "https://example.com/sitemap-2026-March.xml",
        "https://example.com/sitemap-2025-March.xml",
    ]
    client, calls = fake_client(discovery, dict.fromkeys(feeds, "<urlset/>"))
    assert discovery.discover(client, feeds, max_feeds=2, on_error=pytest.fail) == []
    assert calls == [feeds[3], feeds[2]]


def test_child_feeds_reordered_with_window_and_unknown_kept(discovery):
    root = "https://example.com/sitemap.xml"
    unknown = "https://example.com/archive_opaque.xml"
    march = "https://example.com/sitemap_2026-March.xml"
    september = "https://example.com/sitemap_2026-09.xml"
    out = "https://example.com/sitemap_2026-October.xml"
    client, calls = fake_client(
        discovery,
        {
            root: sitemap_index(out, unknown, september, march, march),
            march: "<urlset/>",
            september: "<urlset/>",
            unknown: "<urlset/>",
        },
    )
    discovery.discover(client, [root], max_feeds=10, on_error=pytest.fail)
    assert calls == [root, march, september, unknown]


def test_feed_lastmod_and_article_url_dates_do_not_establish_publication(discovery):
    root = "https://example.com/sitemap.xml"
    march = "https://example.com/sitemap-2026-03.xml"
    old_article = "https://example.com/2025-01/old-story.html"
    future_article = "https://example.com/2026-10/future-story.html"
    client, calls = fake_client(
        discovery,
        {
            root: sitemap_index(march),
            march: f"<urlset><url><loc>{old_article}</loc><lastmod>2026-10-21</lastmod></url>"
            f"<url><loc>{future_article}</loc><lastmod>2026-03-01</lastmod></url></urlset>",
        },
    )
    assert discovery.discover(client, [root], max_feeds=2, on_error=pytest.fail) == sorted(
        [old_article, future_article]
    )
    assert calls == [root, march]


def test_discovery_order_is_deterministic_across_permutations(discovery):
    feeds = [
        "https://example.com/z.xml",
        "https://example.com/a.xml",
        "https://example.com/2026-06-a.xml",
        "https://example.com/2026-06-z.xml",
    ]
    expected = [feeds[2], feeds[3], feeds[1], feeds[0]]
    for order in (feeds, list(reversed(feeds)), [feeds[1], feeds[3], feeds[0], feeds[2]]):
        client, calls = fake_client(discovery, dict.fromkeys(feeds, "<urlset/>"))
        discovery.discover(client, order, max_feeds=4, on_error=pytest.fail)
        assert calls == expected


def test_failed_feeds_and_loops_still_count_toward_request_bound(discovery):
    root = "https://example.com/sitemap.xml"
    march = "https://example.com/2026-03.xml"
    april = "https://example.com/2026-04.xml"
    client, calls = fake_client(
        discovery,
        {
            root: sitemap_index(root, march, april),
            march: OSError("unavailable"),
            april: "<urlset/>",
        },
    )
    errors = []
    discovery.discover(client, [root], max_feeds=2, on_error=lambda *args: errors.append(args))
    assert calls == [root, march]
    assert errors == [(march, "unavailable")]


def test_zero_budget_and_only_out_of_window_feeds_make_no_requests(discovery):
    feeds = ["https://example.com/2026-10.xml", "https://example.com/2026-02.xml"]
    client, calls = fake_client(discovery, {})
    assert discovery.discover(client, feeds, max_feeds=2, on_error=pytest.fail) == []
    assert (
        discovery.discover(
            client, ["https://example.com/sitemap.xml"], max_feeds=0, on_error=pytest.fail
        )
        == []
    )
    assert calls == []
    with pytest.raises(ValueError, match="nonnegative"):
        discovery.discover(client, [], max_feeds=-1, on_error=pytest.fail)


def test_businessline_urlset_of_daily_sitemaps_is_followed(discovery):
    root = "https://example.com/sitemap/archive.xml"
    old = "https://example.com/sitemap/archive/all/20101202_1.xml"
    march = "https://example.com/sitemap/archive/all/20260312_1.xml"
    article = "https://example.com/economy/oil/article123.ece"
    client, calls = fake_client(
        discovery,
        {
            root: f"<urlset><url><loc>{old}</loc></url><url><loc>{march}</loc></url></urlset>",
            march: f"<urlset><url><loc>{article}</loc></url></urlset>",
        },
    )
    assert discovery.discover(client, [root], max_feeds=3, on_error=pytest.fail) == [article]
    assert calls == [root, march]
