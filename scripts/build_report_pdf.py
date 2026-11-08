"""Render reports/academic_report.md as a typeset PDF.

    python scripts/build_report_pdf.py [--source F] [--output F]

Needs `reportlab`, which is deliberately **not** a project dependency: it is
used once to typeset a document and has no place in the environment the
experiments run in. Install it into a throwaway virtualenv:

    python -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install reportlab
    PYTHONPATH=src /tmp/pdfenv/bin/python scripts/build_report_pdf.py

The Markdown source is the artefact under version control; the PDF is generated
from it, so the two cannot drift. Supported subset, which is all the report
uses: `%` metadata lines, `##`/`###` headings, paragraphs, `-` bullets, pipe
tables, and inline `**bold**`, `*italic*` and `` `code` ``.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "reports/academic_report.md"
OUTPUT = REPO / "reports/academic_report.pdf"

INK = colors.HexColor("#111111")
RULE = colors.HexColor("#999999")
BAND = colors.HexColor("#ECECEC")


def _styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=17,
            leading=21,
            spaceAfter=10,
            textColor=INK,
        ),
        "byline": ParagraphStyle(
            "byline",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=15,
            alignment=TA_CENTER,
            textColor=INK,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=16,
            spaceAfter=6,
            textColor=INK,
            keepWithNext=1,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=11,
            spaceAfter=4,
            textColor=INK,
            keepWithNext=1,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14.2,
            alignment=TA_JUSTIFY,
            spaceAfter=7,
            textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14.2,
            alignment=TA_JUSTIFY,
            leftIndent=11,
            bulletIndent=2,
            spaceAfter=4,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=8.6,
            leading=11.2,
            spaceAfter=0,
            textColor=INK,
        ),
    }
    s["ref"] = ParagraphStyle(
        "ref",
        parent=s["body"],
        fontSize=9.2,
        leading=12.4,
        leftIndent=14,
        firstLineIndent=-14,
        spaceAfter=3.5,
        alignment=0,
    )
    s["caption"] = ParagraphStyle(
        "caption",
        parent=s["body"],
        fontSize=9,
        leading=11.5,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=10,
        textColor=colors.HexColor("#444444"),
    )
    s["cellhead"] = ParagraphStyle("cellhead", parent=s["cell"], fontName="Times-Bold")
    s["cellnum"] = ParagraphStyle("cellnum", parent=s["cell"], alignment=2)
    return s


def inline(text: str) -> str:
    """Markdown emphasis to reportlab markup, escaping XML first."""
    out = escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", out)
    out = re.sub(r"`(.+?)`", r'<font face="Courier" size="8.8">\1</font>', out)
    return out


def _row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _column_widths(rows: list[list[str]], total: float) -> list[float]:
    """Size columns from their content.

    Every column is first given enough room for its longest single word, so a
    header like "Unsupported edges" cannot be broken mid-word; whatever space is
    left over is then shared out in proportion to how much text each column
    actually holds. A fixed split looked fine on two-column tables and fell
    apart on the seven-column model comparison.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    def plain(cell: str) -> str:
        return re.sub(r"[*`]", "", cell)

    n = len(rows[0])
    pad = 10.0
    longest_word, longest_cell = [0.0] * n, [0.0] * n
    for row in rows:
        for i, cell in enumerate(row[:n]):
            text = plain(cell)
            if set(text) <= set("-: "):
                continue
            font = "Times-Bold" if row is rows[0] else "Times-Roman"
            longest_cell[i] = max(longest_cell[i], stringWidth(text, font, 8.8))
            for word in text.split():
                longest_word[i] = max(longest_word[i], stringWidth(word, font, 8.8))

    floors = [w + pad for w in longest_word]
    if sum(floors) >= total:  # pathological; fall back to equal shares
        return [total / n] * n

    spare = total - sum(floors)
    demand = [max(0.0, c + pad - f) for c, f in zip(longest_cell, floors, strict=True)]
    if sum(demand) <= spare:  # everything fits on one line; pad out evenly
        extra = (spare - sum(demand)) / n
        return [f + d + extra for f, d in zip(floors, demand, strict=True)]
    scale = spare / sum(demand)
    return [f + d * scale for f, d in zip(floors, demand, strict=True)]


def _table(rows: list[list[str]], st, width: float) -> Table:
    aligns = [False] * len(rows[0])
    if len(rows) > 1 and all(set(c) <= set("-: ") for c in rows[1]):
        aligns = [c.strip().endswith(":") for c in rows[1]]
        rows = [rows[0], *rows[2:]]

    data = [
        [
            Paragraph(
                inline(cell),
                st["cellhead"] if r == 0 else (st["cellnum"] if aligns[i] else st["cell"]),
            )
            for i, cell in enumerate(row)
        ]
        for r, row in enumerate(rows)
    ]
    widths = _column_widths(rows, width)

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BAND),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, INK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.6, INK),
                ("INNERGRID", (0, 1), (-1, -1), 0.25, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _figure(path: str, caption: str, st, width: float, source: Path):
    """A `![caption](path)` line. The image is scaled to the frame width, never
    up past its own size, and capped at half a page so a wide figure cannot
    push its caption onto the next one. Image and caption travel together."""
    target = (source.parent / path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"{source}: figure {path!r} does not exist at {target}")
    image = Image(str(target))
    scale = min(width / image.imageWidth, 1.0)
    cap_height = (A4[1] - 38 * mm) * 0.5
    if image.imageHeight * scale > cap_height:
        scale = cap_height / image.imageHeight
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return KeepTogether([image, Paragraph(inline(caption), st["caption"])])


def build(source: Path, output: Path) -> int:
    st = _styles()
    margin = 20 * mm
    width = A4[0] - 2 * margin

    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Does Grounding Decay with Distance?",
        author="Patil, Bhansali, Koranga",
    )

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(A4[0] / 2, 12 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.addPageTemplates(
        [
            PageTemplate(
                id="body", frames=[Frame(margin, 20 * mm, width, A4[1] - 38 * mm)], onPage=footer
            )
        ]
    )

    story, meta, pending, table_rows = [], [], [], []
    in_references = False

    def flush_para():
        if pending:
            story.append(Paragraph(inline(" ".join(pending)), st["body"]))
            pending.clear()

    def flush_table():
        if not table_rows:
            return
        table = _table(list(table_rows), st, width)
        block = [Spacer(1, 6), table, Spacer(1, 13)]
        if len(table_rows) > 12:
            story.extend(block)
            table_rows.clear()
            return

        # A short table that splits two rows before a page break reads badly,
        # so keep it whole. Carry its heading and one-line introduction down
        # with it too: a heading left stranded above a half-page of white,
        # with its table overleaf, is the worse of the two faults.
        # Carry a heading down with the table only when it sits directly on it,
        # with no body text in between - that is the case where leaving the
        # table behind strands the heading above white space. A heading that
        # already has its paragraph is not stranded, and dragging the whole
        # section down just moves the hole further up the page.
        carried = []
        while story and isinstance(story[-1], Paragraph) and story[-1].style.name in {"h1", "h2"}:
            carried.insert(0, story.pop())
        story.append(KeepTogether(carried + block))
        table_rows.clear()

    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()

        if line.startswith("% "):
            meta.append(line[2:].strip())
            continue
        if line.startswith("|"):
            flush_para()
            table_rows.append(_row(line))
            continue
        flush_table()

        if not line.strip():
            flush_para()
            continue
        if line.startswith("### "):
            flush_para()
            story.append(Paragraph(inline(line[4:]), st["h2"]))
            continue
        if line.startswith("## "):
            flush_para()
            heading = line[3:]
            # Each reference is its own line in the source; reflowing them into
            # one justified block, as the body rule would, makes the list
            # unreadable.
            in_references = heading.strip().lower().endswith("references")
            story.append(Paragraph(inline(heading), st["h1"]))
            continue
        figure = re.fullmatch(r"!\[(?P<caption>.*)\]\((?P<path>[^)]+)\)", line.strip())
        if figure:
            flush_para()
            story.append(_figure(figure["path"], figure["caption"], st, width, source))
            continue
        if line.startswith("- "):
            flush_para()
            story.append(Paragraph(inline(line[2:]), st["bullet"], bulletText="•"))
            continue
        if in_references:
            story.append(Paragraph(inline(line.strip()), st["ref"]))
            continue
        pending.append(line.strip())

    flush_para()
    flush_table()

    if meta:
        head = [Paragraph(inline(meta[0]), st["title"])]
        for row in meta[1:]:
            head.append(Paragraph(inline(row), st["byline"]))
        head.append(Spacer(1, 18))
        story = [KeepTogether(head), *story]

    doc.build(story)
    print(f"wrote {output}  ({output.stat().st_size // 1024} KB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"{args.source} not found")
    return build(args.source, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
