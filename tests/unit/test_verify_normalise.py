"""The span-normalisation policy (docs/decisions.md D-13), asserted both ways.

Every relaxation we allow gets a test, and so does every relaxation we refuse.
The refusals are the load-bearing half: if someone later reaches for
`casefold()` or a stemmer to make a flaky span match pass, these fail first.
"""

from __future__ import annotations

import pytest

from verify import collapse_whitespace, normalise_presentation

# --- what the policy folds -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a  b", "a b"),
        ("a\nb", "a b"),
        ("a\n   b", "a b"),
        ("a\tb", "a b"),
        ("a\u00a0b", "a b"),  # non-breaking space
        ("a\u2009b", "a b"),  # thin space
        ("a\u202fb", "a b"),  # narrow no-break space
        ("  padded  ", "padded"),
    ],
)
def test_whitespace_runs_collapse(raw: str, expected: str):
    assert normalise_presentation(raw) == expected
    assert collapse_whitespace(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("carrier\u2019s", "carrier's"),  # right single quote
        ("\u2018quoted\u2019", "'quoted'"),
        ("\u201cquoted\u201d", '"quoted"'),
        ("20\u201330", "20-30"),  # en dash
        ("oil \u2014 and gas", "oil - and gas"),  # em dash
        ("non\u2011breaking", "non-breaking"),
        ("minus \u2212100", "minus -100"),
        ("and so on\u2026", "and so on..."),
        ("soft\u00adhyphen", "softhyphen"),
        ("zero\u200bwidth", "zerowidth"),
        ("\ufeffbom", "bom"),
    ],
)
def test_presentation_characters_fold_to_ascii(raw: str, expected: str):
    assert normalise_presentation(raw) == expected


def test_collapse_whitespace_leaves_punctuation_alone():
    # The whitespace half is exported on its own for Track A's parser, which
    # must not silently rewrite a document's quotation marks at ingest.
    assert collapse_whitespace("carrier\u2019s  cost") == "carrier\u2019s cost"


# --- what the policy refuses to fold ---------------------------------------


@pytest.mark.parametrize(
    "span",
    [
        "The rupee weakened",  # casing
        "Brent crude",
        "$98.4 a barrel",  # digits and magnitudes
        "6.2 per cent",
        "could slow the pace",  # hedging
        "may have to consider",
        "poses an upside risk",
        "is expected to widen",
        "widen by about $2.5 billion, traders said",  # clause punctuation
    ],
)
def test_meaningful_content_survives_untouched(span: str):
    assert normalise_presentation(span) == span


@pytest.mark.parametrize(
    ("one", "other"),
    [
        ("the rupee fell", "The rupee fell"),  # case is meaning-adjacent: see D-13
        ("inflation could rise", "inflation will rise"),  # hedging
        ("rose to $98.4", "rose to $984"),  # magnitude
        ("rose 14 basis points", "rose 40 basis points"),
        ("prices rose", "price rose"),  # no plural folding
        ("widen, traders said", "widen traders said"),  # no punctuation stripping
    ],
)
def test_pairs_that_must_stay_different(one: str, other: str):
    assert normalise_presentation(one) != normalise_presentation(other)
