"""Track A corpus ingestion and exact paragraph chunking."""

from .documents import Document, chunk_document, normalise_paragraphs
from .parser import ParseError, parse_html

__all__ = ["Document", "ParseError", "chunk_document", "normalise_paragraphs", "parse_html"]
