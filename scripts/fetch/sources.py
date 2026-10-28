"""Publisher identities. Sitemap locations are discovered from robots.txt."""

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Source:
    name: str
    root: str
    hosts: tuple[str, ...]

    def accepts(self, url: str) -> bool:
        parts = urlsplit(url)
        return (
            parts.scheme in {"http", "https"}
            and parts.hostname in self.hosts
            and parts.port in {None, 80, 443}
            and parts.username is None
            and parts.password is None
        )


SOURCES = {
    "businessline": Source(
        "businessline",
        "https://www.thehindubusinessline.com",
        ("www.thehindubusinessline.com", "thehindubusinessline.com"),
    ),
    "economic_times": Source(
        "economic_times",
        "https://economictimes.indiatimes.com",
        ("economictimes.indiatimes.com",),
    ),
    "business_standard": Source(
        "business_standard",
        "https://www.business-standard.com",
        ("www.business-standard.com", "business-standard.com"),
    ),
    "mint": Source("mint", "https://www.livemint.com", ("www.livemint.com", "livemint.com")),
}
