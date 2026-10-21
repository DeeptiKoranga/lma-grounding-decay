"""Overlapping network reads cannot race request pacing or exceed the budget."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from pathlib import Path
from types import SimpleNamespace


def test_request_reservations_share_pacing_and_budget(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    module = importlib.import_module("scripts.fetch.client")
    source = importlib.import_module("scripts.fetch.sources").SOURCES["mint"]
    client = module.Client(source, delay=2, max_requests=4)
    fake_time = SimpleNamespace(now=100.0)
    monkeypatch.setattr(module.time, "monotonic", lambda: fake_time.now)
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: setattr(fake_time, "now", fake_time.now + seconds)
    )
    headers = Message()
    headers["Content-Type"] = "text/html"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, n):
            return b"small page"

    response = Response()
    response.headers = headers
    client.opener = SimpleNamespace(open=lambda *args, **kwargs: response)

    def fetch(index):
        try:
            return client._request(f"https://www.livemint.com/{index}")
        except module.FetchError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, range(8)))
    assert sum(r is not None for r in results) == 4
    assert client.requests == 4
    assert fake_time.now == 106.0
