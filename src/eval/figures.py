"""Export graph figures and reviewed-only UER charts as standalone artifacts."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

from schema import Graph


def graph_figure(graph: Graph, output: Path):
    lines = [
        "digraph explanation {",
        "rankdir=LR;",
        'graph [bgcolor="white", pad="0.3"];',
        'node [shape=box, style="rounded,filled", fillcolor="#edf4ef", fontname="Helvetica"];',
        'edge [fontname="Helvetica", fontsize=10];',
    ]
    for node in graph.nodes:
        label = node.var.replace("_", " ") + f" ({node.direction})"
        lines.append(f"{json.dumps(node.var)} [label={json.dumps(label)}];")
    for edge in graph.edges:
        label = f"{edge.direction} | {edge.strength} | hop {edge.hop}"
        style = "solid" if edge.is_asserted else "dashed"
        lines.append(
            f'{json.dumps(edge.src_var)} -> {json.dumps(edge.dst_var)} [label={json.dumps(label)}, style="{style}"];'
        )
    caption = (
        f"{graph.query_id} | cutoff {graph.as_of}\n"
        "Development example: model labels; independent review pending\n"
        "Solid: source_asserted; dashed: model_inferred"
    )
    lines.append(f"label={json.dumps(caption)}; labelloc=b; }}")
    output.parent.mkdir(parents=True, exist_ok=True)
    dot = output.with_suffix(".dot")
    dot.write_text("\n".join(lines) + "\n")
    subprocess.run(["dot", "-Tsvg", str(dot), "-o", str(output)], check=True)


def uer_plot_data(reviewed: dict) -> dict:
    """Validate query-macro means and preserve missing denominators as missing."""
    if reviewed.get("status") != "reviewed development results; directional only":
        raise ValueError("UER figures require completed independent support review")
    output = {}
    for condition in ("B1", "M"):
        values = []
        for bucket in ("1", "2", "3+"):
            try:
                row = reviewed["aggregate"][condition][bucket]["uer"]
                value = row["mean"]
                count = row["queries_with_denominator"]
                missing = row["queries_without_denominator"]
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    "UER chart requires B1/M means and denominator coverage for every hop"
                ) from exc
            if any(type(n) is not int or n < 0 for n in (count, missing)):
                raise ValueError("denominator query counts must be nonnegative integers")
            if value is None:
                if count:
                    raise ValueError("missing UER cannot have nonzero denominator coverage")
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
                or not count
            ):
                raise ValueError("UER must be finite within 0..1 with a nonzero denominator")
            values.append(
                {"hop": bucket, "mean": value, "queries": count, "total_queries": count + missing}
            )
        totals = {row["total_queries"] for row in values}
        if len(totals) != 1 or not next(iter(totals)):
            raise ValueError("hop groups must cover the same nonempty query set")
        output[condition] = values
    if output["B1"][0]["total_queries"] != output["M"][0]["total_queries"]:
        raise ValueError("B1 and M must cover the same number of queries")
    if not any(row["mean"] is not None for rows in output.values() for row in rows):
        raise ValueError("no established-edge denominators available for a UER figure")
    return output


def uer_figure(reviewed: dict, output: Path):
    data = uer_plot_data(reviewed)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter

    with plt.rc_context({"svg.fonttype": "none", "font.size": 10}):
        fig, ax = plt.subplots(figsize=(8, 4.8))
        legend_handles = []
        for offset, rows in enumerate(data.values()):
            color = ("#4267a9", "#168277")[offset]
            label = ("Prose baseline (B1)", "Full method (M)")[offset]
            legend_handles.append(Patch(facecolor=color, label=label))
            for index, row in enumerate(rows):
                position = index + (offset - 0.5) * 0.34
                value = row["mean"]
                if value is None:
                    ax.text(
                        position,
                        0.025,
                        "N/A",
                        ha="center",
                        va="bottom",
                        color="#666666",
                        fontsize=9,
                    )
                else:
                    ax.bar(position, value, width=0.3, color=color, zorder=3)
                    ax.text(
                        position,
                        value + 0.015,
                        f"{value:.0%}",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )
                ax.text(
                    position,
                    -0.09,
                    f"n={row['queries']}/{row['total_queries']}",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    fontsize=9,
                    color="#555555",
                )
        ax.set(
            xticks=range(3),
            xticklabels=["Hop 1", "Hop 2", "Hop 3+"],
            ylabel="Unsupported established-edge rate",
            ylim=(0, 1.12),
            title="Reviewed development results — directional only",
        )
        ax.set_yticks([i / 5 for i in range(6)])
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="y", color="#e5e7eb", zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(handles=legend_handles, frameon=False, loc="upper right")
        fig.text(
            0.12,
            0.035,
            "n = queries with established claims / total queries. N/A = no denominator.\n"
            "Bars show query-macro means; missing groups are excluded, not scored as zero.",
            fontsize=9,
            color="#555555",
        )
        fig.tight_layout(rect=(0, 0.13, 1, 1))
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            fig.savefig(output, dpi=220)
        finally:
            plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--reviewed-scores", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.graph) == bool(args.reviewed_scores):
        parser.error("choose exactly one of --graph or --reviewed-scores")
    if args.graph:
        payload = json.loads(args.graph.read_text(encoding="utf-8"))
        graph_figure(Graph.model_validate(payload.get("graph", payload)), args.output)
    else:
        uer_figure(json.loads(args.reviewed_scores.read_text(encoding="utf-8")), args.output)


if __name__ == "__main__":
    main()
