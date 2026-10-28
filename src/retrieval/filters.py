"""Shared query validation and eligibility checks for Track A retrievers."""

from __future__ import annotations

import math
from datetime import date
from typing import Protocol

from schema import Passage
from schema.tools import SearchCorpusArgs

from .bm25 import Aliases, Hit


class Retriever(Protocol):
    passages: tuple[Passage, ...]
    aliases: Aliases

    def search(
        self,
        query: str,
        *,
        as_of: date,
        k: int = 10,
        source_kind: str = "any",
        must_mention: list[str] | None = None,
    ) -> list[Hit]: ...


def validate_query(query, *, as_of, k, source_kind, must_mention, aliases) -> SearchCorpusArgs:
    args = SearchCorpusArgs(
        query=query, as_of=as_of, k=k, source_kind=source_kind, must_mention=must_mention or []
    )
    for variable in args.must_mention:
        aliases.forms(variable)
    return args


def eligible(passage: Passage, args: SearchCorpusArgs, aliases: Aliases) -> bool:
    return (
        passage.visible_at(args.as_of)
        and (args.source_kind == "any" or passage.source_kind.value == args.source_kind)
        and all(aliases.mentions(passage.text, var) for var in args.must_mention)
    )


def checked_hits(hits, corpus: dict[str, Passage], args, aliases) -> list[Hit]:
    """Re-check backend output using trusted corpus records before fusion/reranking."""
    result, seen = [], set()
    for hit in hits:
        passage = corpus.get(hit.passage.passage_id)
        if passage is None or passage != hit.passage:
            raise ValueError("retriever returned a passage outside its corpus snapshot")
        if not math.isfinite(hit.score):
            raise ValueError("retriever returned a non-finite score")
        if passage.passage_id not in seen and eligible(passage, args, aliases):
            result.append(hit)
            seen.add(passage.passage_id)
    return result
