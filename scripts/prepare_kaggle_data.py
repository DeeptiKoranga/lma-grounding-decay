"""Package the separately distributed frozen v7 data and pinned index for Kaggle."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from conditions.provenance import digest, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/kaggle_data_v7_20261030.zip")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("reports/kaggle_data_manifest_20261030.json")
    )
    args = parser.parse_args()
    files = [
        Path("data/processed/articles.jsonl"),
        Path("data/aliases.yaml"),
        Path("data/interim/corpus_v7_index_20261026/bge_m3_vectors.json"),
        *sorted(Path("data/series").glob("*.csv")),
    ]
    manifest = {
        "version": 1,
        "scope": "frozen v7 development inputs; no model weights",
        "files": {p.as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size} for p in files},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".zip.part")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path in files:
            archive.write(path, path.as_posix())
        archive.writestr("bundle_manifest.json", json.dumps(manifest, indent=2) + "\n")
    temporary.replace(args.output)
    write_json(
        args.manifest,
        {
            **manifest,
            "archive": {
                "path": args.output.as_posix(),
                "sha256": digest(args.output),
                "bytes": args.output.stat().st_size,
            },
        },
    )
    print(
        json.dumps(
            {
                "archive": str(args.output),
                "sha256": digest(args.output),
                "files": len(files),
                "index": manifest["files"][files[2].as_posix()],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
