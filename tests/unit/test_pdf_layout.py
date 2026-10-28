"""A table region cannot become an unlabelled numerical evidence passage."""

import pytest

from corpus.pdf_layout import _join_continuation_lines, extract_narrative, narrative_reason


def test_pdf_narrative_preserves_qualifications_and_quarantines_table_cells():
    pdf = pytest.importorskip("pymupdf")
    narrative = (
        "The provisional inflation estimate increased during the reporting month. "
        "The figures may be revised when the remaining source data are received. "
        "Food prices were affected by supply disruptions, while other components remained stable."
    )
    after_table = (
        "Food inflation for the reference month is 4.78 percent, based on the provisional "
        "consumer food price index. The corresponding rural and urban rates are reported separately."
    )
    with pdf.open() as document:
        page = document.new_page()
        page.insert_textbox(pdf.Rect(50, 80, 550, 180), narrative, fontsize=10)
        for x in [50, 250, 500]:
            page.draw_line((x, 220), (x, 340))
        for y in [220, 260, 300, 340]:
            page.draw_line((50, y), (500, y))
        page.insert_text((60, 240), "Measure")
        page.insert_text((260, 240), "Value")
        page.insert_text((60, 280), "Food inflation")
        page.insert_text((260, 280), "4.78")
        page.insert_text((60, 320), "Food index")
        page.insert_text((260, 320), "105.35")
        page.insert_textbox(pdf.Rect(50, 345, 550, 440), after_table, fontsize=10)
        page.insert_text((50, 820), "Printed report page 1")
        payload = document.tobytes()
    paragraphs, records = extract_narrative(payload)
    assert " ".join(narrative.split()) in paragraphs
    assert " ".join(after_table.split()) in paragraphs
    assert all("105.35" not in p and "Food index" not in p for p in paragraphs)
    assert all("Printed report" not in p for p in paragraphs)
    assert any(r["reason"] == "table region; column context not certified" for r in records)
    assert all(r["page"] == 1 and len(r["bbox"]) == 4 for r in records)


def test_overlapping_prose_lines_reconstruct_a_sentence_without_borrowing_numeric_cells():
    pytest.importorskip("pymupdf")
    lines = [
        "The National Statistics Office, Ministry of Statistics and Programme",
        "Implementation has released the annual publication for the reference year.",
    ]
    # Coordinates reproduce overlapping font boxes in the Energy Statistics PDF.
    blocks = [
        (95, 250, 560, 274, lines[0], 0, 0),
        (59, 270, 560, 294, lines[1], 1, 0),
        (59, 300, 85, 324, "4.78", 2, 0),
    ]
    merged = _join_continuation_lines(blocks, [])
    assert merged[0]["text"] == " ".join(lines)
    assert narrative_reason(merged[0]["text"]) is None
    assert merged[1]["text"] == "4.78"
    assert narrative_reason(merged[1]["text"]) is not None
