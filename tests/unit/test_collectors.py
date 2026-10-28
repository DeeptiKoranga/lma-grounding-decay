"""Collector regression tests use fake transport; no network is needed."""

import gzip
import hashlib
import importlib
import json
import sys
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest


@pytest.fixture
def fetch(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=lambda *a, **kw: None))
    return SimpleNamespace(
        client=importlib.import_module("scripts.fetch.client"),
        discovery=importlib.import_module("scripts.fetch.discovery"),
        collect=importlib.import_module("scripts.fetch.collect"),
        sources=importlib.import_module("scripts.fetch.sources"),
    )


def test_source_allowlist_is_exact(fetch):
    source = fetch.sources.SOURCES["mint"]
    assert source.accepts("https://www.livemint.com/a")
    for url in (
        "https://www.livemint.com.evil.example/a",
        "file:///etc/passwd",
        "https://evil.example/a",
        "https://user@www.livemint.com/a",
        "https://www.livemint.com:123/a",
    ):
        assert not source.accepts(url)


@pytest.mark.parametrize("compressed", [True, False])
def test_sitemap_lastmod_is_not_used_as_publication_filter(fetch, compressed):
    raw = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://www.livemint.com/march</loc><lastmod>2026-10-21</lastmod></url></urlset>'
    if compressed:
        raw = gzip.compress(raw)
    response = fetch.client.Response(
        "https://www.livemint.com/sitemap.xml", raw, "application/xml", "utf-8"
    )
    feeds, urls = fetch.discovery.parse_feed(response)
    assert feeds == []
    assert urls == ["https://www.livemint.com/march"]


@pytest.mark.parametrize(
    "raw",
    [
        b"<rss><channel><item><link>https://www.livemint.com/a</link></item></channel></rss>",
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="https://www.livemint.com/a"/></entry></feed>',
    ],
)
def test_rss_and_atom(fetch, raw):
    assert fetch.discovery.parse_feed(
        fetch.client.Response("x", raw, "application/xml", "utf-8")
    ) == ([], ["https://www.livemint.com/a"])


def test_discovery_is_bounded_and_stays_on_publisher(fetch):
    calls = []
    response = fetch.client.Response(
        "x",
        b"<sitemapindex><sitemap><loc>https://www.livemint.com/loop.xml</loc></sitemap><sitemap><loc>https://evil.example/a</loc></sitemap></sitemapindex>",
        "application/xml",
        "utf-8",
    )
    client = SimpleNamespace(
        source=fetch.sources.SOURCES["mint"], get=lambda url: calls.append(url) or response
    )
    assert (
        fetch.discovery.discover(
            client,
            ["https://www.livemint.com/loop.xml"],
            max_feeds=5,
            on_error=lambda *a: pytest.fail(str(a)),
        )
        == []
    )
    assert len(calls) == 1


def test_robots_denial_prevents_article_request(fetch, monkeypatch):
    client = fetch.client.Client(fetch.sources.SOURCES["mint"], delay=0)
    calls = []

    def request(url):
        calls.append(url)
        return fetch.client.Response(
            url,
            b"User-agent: *\nDisallow: /blocked\nSitemap: https://www.livemint.com/archive.xml",
            "text/plain",
            "utf-8",
        )

    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(ValueError, match="disallows"):
        client.get("https://www.livemint.com/blocked")
    assert calls == ["https://www.livemint.com/robots.txt"]
    assert client.sitemaps() == ["https://www.livemint.com/archive.xml"]


def test_robot_unavailability_fails_closed(fetch, monkeypatch):
    client = fetch.client.Client(fetch.sources.SOURCES["mint"], delay=0)

    def request(url):
        raise HTTPError(url, 403, "Forbidden", Message(), None)

    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(ValueError, match=r"robots\.txt unavailable"):
        client.get("https://www.livemint.com/a")


def test_redirect_cannot_escape_source(fetch, monkeypatch):
    client = fetch.client.Client(fetch.sources.SOURCES["mint"], delay=0)
    calls = []

    def request(url):
        calls.append(url)
        if url.endswith("robots.txt"):
            return fetch.client.Response(url, b"User-agent: *\nAllow: /", "text/plain", "utf-8")
        headers = Message()
        headers["Location"] = "https://evil.example/private"
        raise HTTPError(url, 302, "Found", headers, None)

    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(ValueError, match="outside this publisher"):
        client.get("https://www.livemint.com/a")
    assert len(calls) == 2


def test_request_budget_is_enforced_before_transport(fetch):
    client = fetch.client.Client(fetch.sources.SOURCES["mint"], delay=0, max_requests=1)
    client.requests = 1
    with pytest.raises(ValueError, match="budget"):
        client._request("https://www.livemint.com/a")


def test_resuming_uses_checked_raw_cache_and_advances_to_new_urls(fetch, tmp_path):
    body = "Brent crude rose as import costs increased and the rupee weakened. " * 5
    html = f'<meta property="article:published_time" content="2026-03-12"><meta property="og:title" content="Oil and rupee"><article><p>{body}</p></article>'
    calls = []

    def get(url):
        calls.append(url)
        return fetch.client.Response(url, html.encode(), "text/html", "utf-8")

    client = SimpleNamespace(source=fetch.sources.SOURCES["mint"], get=get)
    urls = ["https://www.livemint.com/a", "https://www.livemint.com/b"]
    assert fetch.collect.collect(client, urls, tmp_path, max_articles=1)["accepted"] == 1
    counts = fetch.collect.collect(client, urls, tmp_path, max_articles=1)
    assert counts == {"cached": 1, "accepted": 2, "downloaded": 1}
    assert len(calls) == 2
    key = hashlib.sha256(urls[0].encode()).hexdigest()[:20]
    meta = json.loads((tmp_path / f"{key}.meta.json").read_text())
    assert meta["accepted"]
    assert meta["sha256"] == hashlib.sha256(html.encode()).hexdigest()
    (tmp_path / f"{key}.html").write_text("tampered")
    fetch.collect.collect(client, urls[:1], tmp_path, max_articles=1)
    events = [
        json.loads(line) for line in (tmp_path / "collection_log.jsonl").read_text().splitlines()
    ]
    assert events[-1]["status"] == "rejected"
    assert "checksum" in events[-1]["reason"]
