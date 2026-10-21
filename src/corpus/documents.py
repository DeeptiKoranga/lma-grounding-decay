"""Normalised documents and exact paragraph offsets (Track A, A3/A5)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schema import CORPUS_END, CORPUS_START, Passage, SourceKind


def normalise_paragraphs(paragraphs: list[str]) -> str:
    """Store this text alongside passages; offsets refer to this representation."""
    cleaned = [" ".join(unicodedata.normalize("NFC", p).split()) for p in paragraphs]
    return "\n\n".join(p for p in cleaned if p)


def document_id(source: str, url: str) -> str:
    return f"{source}-{hashlib.sha256(url.encode()).hexdigest()[:20]}"


class Document(BaseModel):
    """Track A's parent text; the shared Passage contract remains unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_kind: SourceKind = SourceKind.NEWS
    url: str
    published_at: datetime
    modified_at: datetime | None = None
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    licence_note: str

    @model_validator(mode="after")
    def _check(self):
        if not CORPUS_START <= self.published_at.date() <= CORPUS_END:
            raise ValueError("publication is outside the frozen corpus window")
        if self.text != normalise_paragraphs(self.text.split("\n\n")):
            raise ValueError("document text must be normalised before chunking")
        return self


def chunk_document(document: Document) -> list[Passage]:
    """Never find paragraphs by their contents: repeated paragraphs have distinct offsets."""
    return [
        Passage(
            passage_id=f"{document.doc_id}#p{index}",
            doc_id=document.doc_id,
            source=document.source,
            source_kind=document.source_kind,
            url=document.url,
            published_at=document.published_at,
            title=document.title,
            text=match.group(),
            para_idx=index,
            char_start=match.start(),
            char_end=match.end(),
            licence_note=document.licence_note,
        )
        for index, match in enumerate(re.finditer(r"[^\n]+", document.text))
    ]
