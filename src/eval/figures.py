"""Export graph figures and reviewed-only UER charts as standalone artifacts."""

from __future__ import annotations

import argparse
import json
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


def uer_figure(reviewed: dict, output: Path):
    if reviewed.get("status") != "reviewed development results; directional only":
        raise ValueError("UER figures require completed independent support review")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.4))
    for offset, condition in enumerate(("B1", "M")):
        values = [
            reviewed["aggregate"][condition][bucket]["uer"]["mean"] for bucket in ("1", "2", "3+")
        ]
        if any(value is None for value in values):
            raise ValueError("cannot draw missing hop denominators as zero UER")
        ax.bar([i + (offset - 0.5) * 0.32 for i in range(3)], values, width=0.3, label=condition)
    ax.set(
        xticks=range(3),
        xticklabels=["1", "2", "3+"],
        xlabel="Hop from anchor",
        ylabel="Unsupported established-edge rate",
        ylim=(0, 1),
        title="Reviewed development results — directional only",
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
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
        payload = json.loads(args.graph.read_text())
        graph_figure(Graph.model_validate(payload.get("graph", payload)), args.output)
    else:
        uer_figure(json.loads(args.reviewed_scores.read_text()), args.output)


if __name__ == "__main__":
    main()
