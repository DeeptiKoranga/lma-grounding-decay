"""Explicit, reproducible topic screening for the research corpus.

These are acquisition heuristics, not support or causal judgements. Raw payloads
remain available for review. The version screen applies to every source; topic
screening applies to news, while official topics are curated in the seed manifest.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from schema import SourceKind

from .documents import Document

MACRO_TOPIC = re.compile(
    r"\b(brent|crude|oil|rupee|forex|foreign exchange|dollar|inflation|CPI(?!\s*\(\s*M\s*\))|WPI|"
    r"import(?:s|ed|ing)?|exports?|trade deficit|current account|fiscal|monetary|"
    r"repo(?: rate)?|bond yields?|g-sec|government borrowing|liquidity|FPI|FII|"
    r"foreign portfolio|GDP|economic growth|ATF|aviation turbine fuel|LPG|"
    r"fuel prices?|petrol|diesel|natural gas|LNG)\b",
    re.IGNORECASE,
)
PERSONAL_PATH = re.compile(r"/(?:wealth|personal-finance|mutual-funds|etwealth)/", re.IGNORECASE)
SPONSORED = re.compile(
    r"\b(?:published by ET Spotlight|generated and published by ET Spotlight|"
    r"sponsored content|brand post|paid promotion|advertorial|"
    r"company press release that is not part of editorial content)\b",
    re.IGNORECASE,
)


def rejection_reason(document: Document) -> str | None:
    if document.modified_at and document.modified_at.date() > document.published_at.date():
        return "version screen: later-day updated copy cannot stand in for the original publication; retrieve an archived original"
    if document.source_kind is SourceKind.OFFICIAL:
        return None
    if PERSONAL_PATH.search(urlsplit(document.url).path):
        return "topic screen: personal-finance section outside macro-news acquisition scope"
    if SPONSORED.search(document.text):
        return "topic screen: explicitly labelled sponsored/promotional copy"
    # A late navigation recommendation mentioning RBI/oil cannot admit a page.
    if not MACRO_TOPIC.search(document.title + "\n" + document.text[:1500]):
        return "topic screen: no macro topic in title or first 1500 text characters"
    return None
