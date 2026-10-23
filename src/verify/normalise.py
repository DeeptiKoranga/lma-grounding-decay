"""Presentation-only text normalisation for the verifier (B6).

This module is one decision, written down once: **exactly how much a quoted
evidence span may differ from the passage and still count as verbatim.**
`docs/decisions.md` row D-13 is the authority; this docstring is the summary.

The rule layer always tries an exact match first. Only if that fails does it
retry through `normalise_presentation`, and the result records which of the two
matched, so a stricter caller can insist on `SpanMatchKind.EXACT`.

What `normalise_presentation` collapses - all of it typography, none of it
meaning:

* runs of any whitespace (including newlines, tabs, non-breaking and thin
  spaces) become one ASCII space, and the ends are stripped. A span copied out
  of a PDF-extracted passage wraps where the PDF wrapped; a span pasted through
  a chat window loses the wrap. Neither changes what was said.
* curly quotes and apostrophes become straight ones. "carrier's" typed on a
  laptop and "carrier\u2019s" smart-quoted by a CMS are the same word.
* en dashes, em dashes, figure dashes, non-breaking hyphens and the Unicode
  minus sign become an ASCII hyphen. "20\u201330 basis points" and "20-30 basis
  points" are the same range.
* the ellipsis character becomes three dots.
* soft hyphens and zero-width characters are deleted outright. They are
  invisible, so a human reviewer comparing span to passage cannot see them.

What it deliberately does **not** touch, because each of these can change what a
source asserted:

* **case** - "The rupee fell" and "the Rupee fell" are the same sentence, but
  casing is also how the ontology's variable names and proper nouns (Brent, RBI,
  CPI, ATF) are written, and a verifier that lower-cased everything could accept
  a span that quietly renamed a variable. Alias *mention* detection is separately
  case-insensitive, which is a different question: whether a passage talks about
  a variable at all, not whether a quote is faithful.
* **digits, units and magnitudes** - "$98.4" is not "$98,4" and not "$984".
* **hedging and modality** - "could", "may", "is expected to", "poses an upside
  risk" are the whole reason the strength label exists (Direct / Conditional /
  Correlational). A normaliser that dropped or equated them would let a
  conditional claim be quoted as a direct one, which is precisely the strength
  inflation the project is trying to measure.
* **stemming, stopwords, punctuation generally** - no plural folding, no comma
  or full-stop removal, no accent stripping. Commas carry clause structure, and
  a span that gains or loses one is a different quote.

`collapse_whitespace` is exported separately for callers that want only the
whitespace half (Track A's parser normalises paragraph whitespace at ingest).
"""

from __future__ import annotations

import re

__all__ = [
    "INVISIBLE_CHARS",
    "PUNCTUATION_FOLDS",
    "collapse_whitespace",
    "normalise_presentation",
]

#: Deleted outright: invisible to a human comparing a span with its passage.
INVISIBLE_CHARS: tuple[str, ...] = (
    "\u00ad",  # soft hyphen
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\u2060",  # word joiner
    "\ufeff",  # byte-order mark / zero-width no-break space
)

#: Folded to their ASCII equivalent: same character, different typography.
PUNCTUATION_FOLDS: dict[str, str] = {
    # apostrophes and single quotes
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u02bc": "'",
    "\u00b4": "'",
    # double quotes
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2033": '"',
    # dashes and hyphens
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
    # ellipsis
    "\u2026": "...",
}

_TRANSLATION: dict[int, str | None] = {
    **{ord(char): None for char in INVISIBLE_CHARS},
    **{ord(char): replacement for char, replacement in PUNCTUATION_FOLDS.items()},
}

#: Python's `\s` is Unicode-aware for str patterns, so this covers NBSP, thin
#: spaces, line and paragraph separators and the ideographic space as well.
_WHITESPACE_RUN = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:
    """Collapse every run of whitespace to one ASCII space and strip the ends."""
    return _WHITESPACE_RUN.sub(" ", text).strip()


def normalise_presentation(text: str) -> str:
    """Fold typography-only differences. See the module docstring for the policy."""
    return collapse_whitespace(text.translate(_TRANSLATION))
