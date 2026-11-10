"""The blind sample must read the review packet's actual serialized schema."""

import csv
import json

from scripts.sample_validate_support import draw


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
