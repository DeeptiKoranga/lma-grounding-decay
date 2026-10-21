"""Small bounded HTTP client with per-origin robots checks and request pacing."""

from __future__ import annotations

import ssl
import time
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .sources import Source

USER_AGENT = "LmaGroundingResearch/0.1 (+https://github.com/DeeptiKoranga/lma-grounding-decay)"
ROBOT_AGENT = "LmaGroundingResearch"


class FetchError(ValueError):
    pass


@dataclass(frozen=True)
class Response:
    url: str
    body: bytes
    content_type: str
    charset: str


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, source: Source, *, delay: float = 2, max_requests: int = 80):
        if delay < 0 or max_requests < 1:
            raise ValueError("delay must be nonnegative and max_requests positive")
        self.source = source
        self.delay = delay
        self.max_requests = max_requests
        self.requests = 0
        context = ssl.create_default_context()
        # Python.org macOS installs may lack system CAs. The extraction extra
        # supplies certifi; add its CA bundle without disabling TLS verification.
        try:
            import certifi
        except ImportError:
            pass
        else:
            context.load_verify_locations(certifi.where())
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
        self.robots: dict[str, RobotFileParser] = {}
        self.last_request: dict[str, float] = {}
        self.backoff: dict[str, float] = {}

    def _request(self, url: str) -> Response:
        if not self.source.accepts(url):
            raise FetchError("URL is outside this source's allowed hosts")
        if self.requests >= self.max_requests:
            raise FetchError("request budget exhausted")
        origin = self._origin(url)
        policy = self.robots.get(origin)
        crawl_delay = policy.crawl_delay(ROBOT_AGENT) if policy else None
        interval = max(self.delay, crawl_delay or 0)
        rate = policy.request_rate(ROBOT_AGENT) if policy else None
        if rate:
            interval = max(interval, rate.seconds / rate.requests)
        remaining = (
            max(
                self.last_request.get(origin, 0) + interval,
                self.backoff.get(origin, 0),
            )
            - time.monotonic()
        )
        if remaining > 0:
            time.sleep(remaining)
        self.requests += 1
        self.last_request[origin] = time.monotonic()
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
        with self.opener.open(req, timeout=25) as response:
            body = response.read(12_000_001)
            if len(body) > 12_000_000:
                raise FetchError("response exceeds 12 MB limit")
            return Response(
                url=url,
                body=body,
                content_type=response.headers.get_content_type(),
                charset=response.headers.get_content_charset() or "utf-8",
            )

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    def policy(self, url: str) -> RobotFileParser:
        origin = self._origin(url)
        if origin not in self.robots:
            policy = RobotFileParser(origin + "/robots.txt")
            try:
                response = self._request(policy.url)
                policy.parse(response.body.decode(response.charset, errors="replace").splitlines())
            except HTTPError as exc:
                if exc.code != 404:
                    raise FetchError(
                        f"robots.txt unavailable (HTTP {exc.code}); collection stopped"
                    ) from exc
                policy.parse([])
            self.robots[origin] = policy
        return self.robots[origin]

    def get(self, url: str) -> Response:
        """Check every redirect target as well as the originally requested page."""
        for _ in range(6):
            if not self.source.accepts(url):
                raise FetchError("redirect or URL is outside this publisher")
            if not self.policy(url).can_fetch(ROBOT_AGENT, url):
                raise FetchError("robots.txt disallows this URL")
            try:
                return self._request(url)
            except HTTPError as exc:
                if exc.code in {301, 302, 303, 307, 308} and exc.headers.get("Location"):
                    url = urljoin(url, exc.headers["Location"])
                    continue
                if exc.code == 429:
                    # End this attempt; subsequent requests respect Retry-After.
                    retry = exc.headers.get("Retry-After", "60")
                    seconds = float(retry) if retry.isdigit() else 60
                    self.backoff[self._origin(url)] = time.monotonic() + seconds
                raise
        raise FetchError("too many redirects")

    def sitemaps(self) -> list[str]:
        return self.policy(self.source.root).site_maps() or [self.source.root + "/sitemap.xml"]
