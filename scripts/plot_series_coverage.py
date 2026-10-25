"""Plot observation counts, separating historical vintages from later snapshots."""

import argparse
from collections import Counter
from pathlib import Path

from corpus.series import SeriesStore


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=Path("data/series"))
    parser.add_argument("--snapshot", type=Path, default=Path("data/series/retrospective_20261025"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    series = [
        ("brent_usd_bbl", "Brent"),
        ("indian_basket_usd_bbl", "Indian basket"),
        ("gsec_10y_pct", "10-year yield"),
        ("fpi_flows_usd_mn", "FPI"),
        ("inr_usd", "USD/INR"),
        ("cpi_headline_yoy", "CPI headline"),
    ]
    panels = [
        ("Original publication-dated observations · 161 points", args.canonical),
        ("Retrospective snapshot · 317 points", args.snapshot),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(9.8, 7.3))
    for ax, (title, root) in zip(axes, panels, strict=True):
        store = SeriesStore.from_directory(root)
        counts = Counter((sid, r.on.month) for sid, rows in store.series.items() for r in rows)
        values = np.array([[counts[(sid, m)] for m in range(2, 10)] for sid, _ in series])
        ax.imshow(np.log1p(values), cmap="Blues", vmin=0, vmax=np.log1p(23), aspect="auto")
        ax.set(
            xticks=range(8),
            xticklabels=["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            yticks=range(len(series)),
            yticklabels=[name for _, name in series],
        )
        for i in range(len(series)):
            for j in range(8):
                ax.text(
                    j,
                    i,
                    str(values[i, j]),
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="white" if values[i, j] >= 7 else "#1c405c",
                )
        ax.set_title(title, loc="left", fontsize=12, weight="bold", pad=10)
        ax.tick_params(length=0, pad=7)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.suptitle(
        "Macro-series coverage by observation month · 2026",
        x=0.025,
        ha="left",
        fontsize=16,
        weight="bold",
    )
    fig.text(
        0.025,
        0.025,
        "Cells count stored observations; zero means no data, not zero value. No interpolation.\n"
        "New retrospective histories were captured 22\u201325 October and are hidden from March\u2013September queries.\n"
        "Brent and yield definitions differ between stores; basket, yield and FPI backfills are monthly. CPI/FX are unchanged.",
        fontsize=9,
        color="#465663",
        linespacing=1.5,
    )
    fig.tight_layout(rect=(0, 0.11, 1, 0.95), h_pad=2.0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".svg"):
        path = args.output.with_suffix(suffix)
        fig.savefig(path, dpi=180, facecolor="white")
        if suffix == ".svg":
            path.write_text(
                "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
            )
    plt.close(fig)


if __name__ == "__main__":
    main()
