"""Dependency-light BM25 with structural as-of and source/variable filtering."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from schema import Passage, load_ontology
from schema.tools import SearchCorpusArgs

TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def phrase_present(text: str, phrase: str) -> bool:
    # Compare full tokens: 'CPI' must not match the middle of an unrelated word.
    needle = tokens(phrase)
    haystack = tokens(text)
    return bool(needle) and any(
        haystack[i : i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1)
    )


class Aliases:
    def __init__(self, mapping: dict[str, list[str]]):
        ontology = load_ontology()
        unknown = set(mapping) - set(ontology.ids())
        if unknown:
            raise ValueError(f"unknown alias variables: {sorted(unknown)}")
        if any(
            not isinstance(forms, list)
            or not forms
            or any(not isinstance(form, str) or not tokens(form) for form in forms)
            for forms in mapping.values()
        ):
            raise ValueError("aliases must be nonempty lists of nonempty surface forms")
        self.mapping = {key: tuple(dict.fromkeys([key, *forms])) for key, forms in mapping.items()}

    @classmethod
    def load(cls, path: str | Path) -> Aliases:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("alias file must contain a mapping")
        entries = raw.get("aliases", raw.get("variables"))
        if not isinstance(entries, dict):
            raise ValueError("alias file must contain an aliases mapping")
        mapping = {
            key: value.get("surface_forms") if isinstance(value, dict) else value
            for key, value in entries.items()
        }
        table = cls(mapping)
        table.no_expand = {
            key
            for key, value in entries.items()
            if isinstance(value, dict) and value.get("expand_for_bm25") is False
        }
        return table

    def forms(self, variable: str) -> tuple[str, ...]:
        if variable not in load_ontology():
            raise ValueError(f"unknown variable: {variable}")
        return self.mapping.get(variable, (variable,))

    def mentions(self, text: str, variable: str) -> bool:
        return any(phrase_present(text, form) for form in self.forms(variable))

    def expand(self, query: str) -> list[str]:
        expanded = tokens(query)
        for variable, forms in self.mapping.items():
            if variable in getattr(self, "no_expand", set()):
                continue
            if any(phrase_present(query, form) for form in forms):
                for form in self.forms(variable):
                    expanded.extend(tokens(form))
        # Each term counts once: many aliases must not inflate one variable's weight.
        return list(dict.fromkeys(expanded))


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


class BM25Retriever:
    """A6/A11. Every query requires an as-of date; no unfiltered public search path.

    IDF and length statistics are calculated on the date-visible corpus so future
    documents cannot influence earlier rankings. Source/mention filters narrow
    candidates without changing the date-visible scoring population.
    """

    def __init__(
        self,
        passages: list[Passage],
        *,
        aliases: Aliases | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        ids = [p.passage_id for p in passages]
        if len(ids) != len(set(ids)):
            raise ValueError("passage ids must be unique")
        self.passages = tuple(passages)
        self.aliases = aliases or Aliases({})
        self.k1, self.b = k1, b
        self.term_counts = [Counter(tokens(p.title + " " + p.text)) for p in self.passages]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.postings: dict[str, set[int]] = defaultdict(set)
        for index, counts in enumerate(self.term_counts):
            for term in counts:
                self.postings[term].add(index)

    @classmethod
    def from_jsonl(cls, path: str | Path, **kwargs) -> BM25Retriever:
        with Path(path).open(encoding="utf-8") as stream:
            return cls(
                [Passage.model_validate_json(line) for line in stream if line.strip()], **kwargs
            )

    def search(
        self,
        query: str,
        *,
        as_of: date,
        k: int = 10,
        source_kind: str = "any",
        must_mention: list[str] | None = None,
        expand_aliases: bool = True,
    ) -> list[Hit]:
        args = SearchCorpusArgs(
            query=query, as_of=as_of, k=k, source_kind=source_kind, must_mention=must_mention or []
        )
        for variable in args.must_mention:
            self.aliases.forms(variable)  # validate even if corpus is empty
        terms = (
            self.aliases.expand(args.query)
            if expand_aliases
            else list(dict.fromkeys(tokens(query)))
        )
        visible = {i for i, p in enumerate(self.passages) if p.visible_at(args.as_of)}
        if not visible or not terms:
            return []
        average_length = sum(self.lengths[i] for i in visible) / len(visible)
        scores: dict[int, float] = defaultdict(float)
        for term in terms:
            matches = self.postings.get(term, set()) & visible
            idf = math.log(1 + (len(visible) - len(matches) + 0.5) / (len(matches) + 0.5))
            for index in matches:
                passage = self.passages[index]
                if args.source_kind != "any" and passage.source_kind.value != args.source_kind:
                    continue
                # Evidence must mention both variables in the paragraph itself.
                if not all(self.aliases.mentions(passage.text, v) for v in args.must_mention):
                    continue
                tf = self.term_counts[index][term]
                normalisation = 1 - self.b + self.b * self.lengths[index] / average_length
                scores[index] += idf * tf * (self.k1 + 1) / (tf + self.k1 * normalisation)
        ranked = sorted(scores, key=lambda i: (-scores[i], self.passages[i].passage_id))
        return [Hit(passage=self.passages[i], score=scores[i]) for i in ranked[: args.k]]

    def save(self, path: str | Path) -> None:
        """Portable Passage JSONL; rebuild postings on load, no unsafe pickle state."""
        with Path(path).open("w", encoding="utf-8") as stream:
            for passage in self.passages:
                stream.write(passage.model_dump_json() + "\n")


def serialise_hits(hits: list[Hit]) -> str:
    return json.dumps(
        {
            "passages": [h.passage.model_dump(mode="json") for h in hits],
            "scores": [h.score for h in hits],
        },
        ensure_ascii=False,
        indent=2,
    )
