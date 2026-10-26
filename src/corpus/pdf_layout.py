"""Conservative narrative-only PDF evidence with page/bounding-box provenance.

Tables, charts, headers and short fragments stay in the original PDF, outside
the text evidence index. This mode never invents column labels or repairs
misread decimal points. It is a scoped extraction, not a full-text rendition.
"""

from __future__ import annotations

import re

from .documents import normalise_paragraphs
from .parser import ParseError

CLAUSE = re.compile(
    r"\b(?:is|are|was|were|has|have|had|may|could|would|will|should|"
    r"increased|decreased|recorded|released|estimated|remained|compiled|"
    r"constituted|includes?|measures?|represents?|provides?|comprises?)\b",
    re.IGNORECASE,
)


def narrative_reason(text: str) -> str | None:
    if "embargoed against" in text.lower():
        return "embargo/release furniture; date retained in source metadata"
    words = re.findall(r"[A-Za-z]{2,}", text)
    if len(text) < 100 or len(words) < 12:
        return "short heading, label or numeric fragment"
    if sum(c.isalpha() for c in text) / len(text) < 0.55:
        return "numeric/table-like block"
    if not CLAUSE.search(text) or not re.search(r"[.;:]\s*$", text):
        return "no self-contained narrative clause"
    if "http" in text.lower() and len(words) < 25:
        return "URL/print furniture"
    return None


def _join_continuation_lines(blocks, tables):
    """Rejoin adjacent full-width prose lines; never cross a table or page.

    Some OEA PDFs store each printed prose line as a separate text block. A
    continuation must be close in y, share the text column and contain prose.
    Sentence endings, numbered/bullet starts and table regions end the group.
    """
    import pymupdf

    result, pending = [], None
    for block in blocks:
        if block[6] != 0 or not block[4].strip():
            continue
        box = pymupdf.Rect(block[:4])
        text = normalise_paragraphs([block[4]])
        prose_line = (
            len(text) >= 40
            and box.width >= 200
            and sum(c.isalpha() for c in text) / len(text) >= 0.55
            and not text.isupper()
            and not any(box.intersects(table) for table in tables)
        )
        new_item = bool(re.match(r"^(?:\(?[ivx]{1,4}\)|\d+[.)]|[•])\s", text, re.I))
        short_tail = (
            len(re.findall(r"[A-Za-z]{2,}", text)) >= 2
            and len(text) >= 8
            and not text.isupper()
            and not any(box.intersects(table) for table in tables)
        )
        split_year_tail = (
            pending is not None
            and pending["text"].endswith("-")
            and bool(re.fullmatch(r"\d{1,4}[.]?", text))
        )
        can_join = (
            pending is not None
            and (prose_line or short_tail or split_year_tail)
            and pending["prose_line"]
            and not new_item
            and not re.search(r"[.;:]\s*$", pending["text"])
            and -0.4 * min(box.height, pending["bbox"].height) <= box.y0 - pending["bbox"].y1 <= 24
            and abs(box.x0 - pending["bbox"].x0) <= 70
        )
        if can_join:
            pending["text"] += " " + text
            pending["bbox"] |= box
            pending["native_blocks"].append(list(block[:4]))
        else:
            if pending is not None:
                result.append(pending)
            pending = {
                "bbox": box,
                "text": text,
                "prose_line": prose_line,
                "native_blocks": [list(block[:4])],
            }
    if pending is not None:
        result.append(pending)
    return result


def extract_narrative(payload: bytes) -> tuple[list[str], list[dict]]:
    if not payload.startswith(b"%PDF-"):
        raise ParseError("payload is not a PDF")
    import pymupdf

    retained, audit = [], []
    with pymupdf.open(stream=payload, filetype="pdf") as document:
        if document.needs_pass or document.page_count > 500:
            raise ParseError("encrypted or oversized PDF")
        for number, page in enumerate(document, 1):
            # A table cell is not standalone evidence, even if it is a sentence.
            tables = [pymupdf.Rect(table.bbox) for table in page.find_tables().tables]
            lines = []
            for native in page.get_text("dict", sort=True)["blocks"]:
                if native["type"] != 0:
                    continue
                for line in native["lines"]:
                    text = "".join(span["text"] for span in line["spans"])
                    lines.append((*line["bbox"], text, len(lines), 0))
            # Split mixed table/prose blocks before masking. A food-inflation
            # paragraph can share a native block with the final numeric row.
            for block in _join_continuation_lines(lines, tables):
                text, bbox = block["text"], block["bbox"]
                reason = narrative_reason(text)
                if bbox.y1 < 50 or bbox.y0 > page.rect.height - 45:
                    reason = "page header/footer"
                if any(bbox.intersects(table) for table in tables):
                    reason = "table region; column context not certified"
                # Captions/statistical fragments are never silently concatenated.
                index = len(retained) if reason is None else None
                if reason is None:
                    retained.append(text)
                audit.append(
                    {
                        "page": number,
                        "bbox": [round(v, 3) for v in bbox],
                        "native_blocks": block["native_blocks"],
                        "text": text,
                        "retained_index": index,
                        "reason": reason,
                    }
                )
    if sum(len(text) for text in retained) < 200:
        raise ParseError("no adequate narrative; retain original outside text evidence index")
    return retained, audit
