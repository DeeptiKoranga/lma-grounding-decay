"""The blind sample must read the review packet's actual serialized schema."""

import csv
import json

from scripts.sample_validate_support import draw, score


def test_draw_uses_nested_judgments_and_includes_attached_passage(tmp_path):
    packet_dir = tmp_path / "packet"
    packet_dir.mkdir()
    (packet_dir / "packet.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item_id": "edge-1",
                        "src_var": "BRENT",
                        "dst_var": "IMPORT_BILL",
                        "direction": "up",
                        "as_of": "2026-04-08",
                        "evidence_span": "higher oil raises import costs",
                        "passage": {
                            "passage_id": "doc#p1",
                            "published_at": "2026-04-01",
                            "text": "Higher oil raises import costs in India.",
                        },
                    }
                ]
            }
        )
    )
    (packet_dir / "judgments.json").write_text(
        json.dumps({"judgments": [{"item_id": "edge-1", "supported": True}]})
    )

    out = tmp_path / "sample"
    assert draw({"primary": packet_dir}, 1, out, 7)["size"] == 1
    with (out / "worksheet.csv").open(newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["claim"] == "BRENT -> IMPORT_BILL (up)"
    assert row["passage_text"] == "Higher oil raises import costs in India."
    assert row["published"] == "2026-04-01"
    assert row["passage_id"] == "doc#p1"
    assert row["supported"] == ""
    assert "arm" not in row
    assert "assistant_supported" not in row


def test_score_leads_with_informative_denominator(tmp_path):
    (tmp_path / "key.json").write_text(
        json.dumps(
            {
                "seed": 7,
                "rows": {
                    "v001": {"arm": "primary", "assistant_supported": "no"},
                    "v002": {"arm": "primary", "assistant_supported": "yes"},
                    "v003": {"arm": "sensitivity", "assistant_supported": "yes"},
                },
            }
        )
    )
    with (tmp_path / "worksheet.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "row_id",
                "supported",
                "evidence_strength",
                "evidence_span",
                "passage_text",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "row_id": "v001",
                    "supported": "no",
                    "evidence_strength": "",
                    "evidence_span": "",
                    "passage_text": "",
                },
                {
                    "row_id": "v002",
                    "supported": "no",
                    "evidence_strength": "",
                    "evidence_span": "span",
                    "passage_text": "EVIDENCE_SECRET",
                },
                {
                    "row_id": "v003",
                    "supported": "yes",
                    "evidence_strength": "direct",
                    "evidence_span": "span",
                    "passage_text": "EVIDENCE_SECRET",
                },
            ]
        )
    report = score(tmp_path, None)
    assert "| informative rows | 2 of 3 |" in report
    assert "| human rejected among informative rows | 1 of 2 |" in report
    assert "| informative raw agreement | 0.500 |" in report
    assert "| all-row raw agreement (includes 1 no-evidence rows) | 0.667 |" in report
    assert "Worksheet SHA-256:" in report
    assert "| primary | 1 | 1 / 0 | 0 / 1 | 1 | 0.000 |" in report
    assert "EVIDENCE_SECRET" not in report
