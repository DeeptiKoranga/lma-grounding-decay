"""Plot observed corpus counts; no relevance or human support labels are inferred."""

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output prefix for PNG and SVG")
    args = parser.parse_args()
    docs = [json.loads(line) for line in args.documents.read_text().splitlines()]
    months = [f"2026-{month:02}" for month in range(3, 10)]
    counts = Counter((d["source"], d["published_at"][:7]) for d in docs)
    panels = [
        (
            "News",
            [
                ("economic_times", "Economic Times"),
                ("businessline", "BusinessLine"),
                ("mint", "Mint"),
                ("business_standard", "Business Standard"),
            ],
        ),
        (
            "Official",
            [
                ("mospi", "MoSPI"),
                ("ppac", "PPAC"),
                ("eaindustry", "OEA (added source)"),
                ("rbi", "RBI"),
                ("pib", "PIB (deduplicated)"),
            ],
        ),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.4), gridspec_kw={"height_ratios": [4, 5]})
    for ax, (title, sources) in zip(axes, panels, strict=True):
        values = np.array([[counts[(source, month)] for month in months] for source, _ in sources])
        ax.imshow(
            np.log1p(values),
            cmap="Greens",
            aspect="auto",
            vmin=0,
            vmax=np.log1p(max(values.max(), 1)),
        )
        ax.set(
            xticks=range(7),
            xticklabels=["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            yticks=range(len(sources)),
            yticklabels=[label for _, label in sources],
        )
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=8)
        for i in range(len(sources)):
            for j in range(7):
                ax.text(
                    j,
                    i,
                    str(values[i, j]),
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=(
                        "white"
                        if np.log1p(values[i, j]) > np.log1p(max(values.max(), 1)) * 0.6
                        else "#173d2a"
                    ),
                )
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0, pad=7)
    fig.suptitle(
        "Corpus source coverage · March\u2013September 2026",
        x=0.03,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    news = sum(d["source_kind"] == "news" for d in docs)
    fig.text(
        0.03,
        0.015,
        f"{len(docs):,} documents · {news:,} news · {len(docs) - news:,} official\nLocal development snapshot; independent extraction/source acceptance pending. Counts do not establish source balance.",
        fontsize=9,
        color="#4c5952",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94), h_pad=1.6)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output.with_suffix(".png"), dpi=180)
    fig.savefig(args.output.with_suffix(".svg"))
    plt.close(fig)


if __name__ == "__main__":
    main()
