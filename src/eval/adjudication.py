"""Blind double-annotation of the gold evidence graphs (#15, #37).

The gold graphs on disk are machine-drafted (D-20). Adjudicating them means two
people independently deciding, for each edge, three things the rule layer cannot
check: whether the cited span **asserts** the relation at all, which way the
causation runs, and whether the strength label matches the language.

Why this module exists rather than a markdown sheet
---------------------------------------------------
`data/eval/gold/dev/ADJUDICATION.md` prints the drafter's own labels. Two people
working from it would be agreeing with the draft, not with each other, and
Cohen's kappa on that is not an agreement measurement — it is a measurement of
how persuasive the draft is. So the worksheets here carry the span, the two
variables and the dates, and **no label**. Item ids are opaque so a worksheet row
cannot be casually looked up in the draft record.

Two annotators, independently, then reconcile. Agreement is computed between the
two humans; agreement with the draft is reported separately, because that is a
different question (how good was the draft) and must not be confused with the
first.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path as FsPath
from random import Random
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schema import Direction, Graph, Strength

from .agreement import kappa

__all__ = [
    "BLANK_COLUMNS",
    "FILLED_COLUMNS",
    "VERDICTS",
    "AdjudicationLabel",
    "DimensionAgreement",
    "WorksheetItem",
    "against_draft",
    "build_items",
    "item_id",
    "load_worksheet",
    "score",
    "worksheet_rows",
]

#: Pre-filled on the worksheet: everything the annotator needs and nothing more.
FILLED_COLUMNS: tuple[str, ...] = (
    "item_id",
    "anchor",
    "as_of",
    "src_var",
    "dst_var",
    "passage_id",
    "published",
    "span",
)

#: Left blank for the annotator.
BLANK_COLUMNS: tuple[str, ...] = ("asserts", "direction", "strength", "verdict", "note")

VERDICTS: tuple[str, ...] = ("keep", "fix", "drop")


def item_id(query_id: str, edge_id: str) -> str:
    """Opaque, stable id. Opaque so a worksheet row does not point straight at
    the drafter's label in ADJUDICATION.md; stable so two worksheets and the
    draft can be reconciled afterwards."""
    return hashlib.sha256(f"{query_id}/{edge_id}".encode()).hexdigest()[:10]


class WorksheetItem(BaseModel):
    """One edge, stripped of every label an annotator is being asked to supply."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    query_id: str
    edge_id: str
    anchor: str
    as_of: str
    src_var: str
    dst_var: str
    passage_id: str
    published: str
    span: str


class AdjudicationLabel(BaseModel):
    """What one annotator decided about one edge."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    asserts: bool
    direction: Direction | None = None
    strength: Strength | None = None
    verdict: str
    note: str = ""

    @model_validator(mode="after")
    def _verdict_known(self) -> Self:
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}, got {self.verdict!r}")
        return self

    @model_validator(mode="after")
    def _labels_match_the_asserts_decision(self) -> Self:
        """An edge whose span asserts nothing has no direction or strength to
        read off it, and it cannot be kept."""
        if self.asserts:
            missing = [
                name
                for name, value in (("direction", self.direction), ("strength", self.strength))
                if value is None
            ]
            if missing:
                raise ValueError(f"item {self.item_id}: asserts=yes needs {' and '.join(missing)}")
            if self.verdict == "drop":
                raise ValueError(
                    f"item {self.item_id}: asserts=yes with verdict 'drop' is contradictory; "
                    "use 'fix' if the relation holds but a label is wrong"
                )
        else:
            if self.direction is not None or self.strength is not None:
                raise ValueError(
                    f"item {self.item_id}: asserts=no cannot carry a direction or strength"
                )
            if self.verdict != "drop":
                raise ValueError(
                    f"item {self.item_id}: asserts=no must be verdict 'drop', got {self.verdict!r}"
                )
        return self


def build_items(graphs: Mapping[str, Graph] | Iterable[Graph]) -> tuple[WorksheetItem, ...]:
    """One worksheet item per gold edge, in (query_id, edge_id) order."""
    sequence = list(graphs.values()) if isinstance(graphs, Mapping) else list(graphs)
    items: list[WorksheetItem] = []
    for graph in sorted(sequence, key=lambda g: g.query_id):
        anchor = (
            f"{graph.anchor.var} {graph.anchor.direction.value} - "
            f"{graph.anchor.event} ({graph.anchor.event_date})"
        )
        for edge in graph.edges:
            if not edge.evidence_span:
                raise ValueError(f"{graph.query_id}/{edge.edge_id} has no span to adjudicate")
            items.append(
                WorksheetItem(
                    item_id=item_id(graph.query_id, edge.edge_id),
                    query_id=graph.query_id,
                    edge_id=edge.edge_id,
                    anchor=anchor,
                    as_of=str(graph.as_of),
                    src_var=edge.src_var,
                    dst_var=edge.dst_var,
                    passage_id=edge.evidence_passage_id or "",
                    published=(
                        str(edge.evidence_published_at.date()) if edge.evidence_published_at else ""
                    ),
                    span=edge.evidence_span,
                )
            )
    return tuple(items)


def worksheet_rows(
    items: Sequence[WorksheetItem], annotator: str, *, seed: int
) -> list[dict[str, str]]:
    """Rows for one annotator's worksheet.

    Graph blocks are shuffled, and edges within each block are shuffled, with a
    seed derived from the annotator's name: two people meet the same evidence in
    different orders, so a shared position effect cannot masquerade as agreement.
    Blocks are kept intact rather than shuffling everything together, because
    reading four episodes interleaved costs more in annotation quality than the
    extra randomisation buys.
    """
    rng = Random(f"{seed}:{annotator.strip().lower()}")
    by_query: dict[str, list[WorksheetItem]] = {}
    for item in items:
        by_query.setdefault(item.query_id, []).append(item)

    blocks = sorted(by_query)
    rng.shuffle(blocks)
    rows: list[dict[str, str]] = []
    for query_id in blocks:
        block = list(by_query[query_id])
        rng.shuffle(block)
        for item in block:
            row = {column: getattr(item, column) for column in FILLED_COLUMNS}
            rows.append({**row, **dict.fromkeys(BLANK_COLUMNS, "")})
    return rows


def _boolean(raw: str, item: str) -> bool:
    value = raw.strip().lower()
    if value in {"y", "yes", "true", "1"}:
        return True
    if value in {"n", "no", "false", "0"}:
        return False
    raise ValueError(f"item {item}: asserts must be yes or no, got {raw!r}")


def load_worksheet(path: FsPath | str) -> dict[str, AdjudicationLabel]:
    """Read one completed worksheet. Refuses a partly filled one rather than
    scoring the rows that happen to be done."""
    with FsPath(path).open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path} has no rows")

    labels: dict[str, AdjudicationLabel] = {}
    blank: list[str] = []
    for row in rows:
        key = (row.get("item_id") or "").strip()
        if not key:
            raise ValueError(f"{path}: a row has no item_id")
        if not (row.get("asserts") or "").strip():
            blank.append(key)
            continue
        asserts = _boolean(row["asserts"], key)
        direction = (row.get("direction") or "").strip().lower() or None
        strength = (row.get("strength") or "").strip().lower() or None
        labels[key] = AdjudicationLabel(
            item_id=key,
            asserts=asserts,
            direction=Direction(direction) if direction else None,
            strength=Strength(strength) if strength else None,
            verdict=(row.get("verdict") or "").strip().lower(),
            note=(row.get("note") or "").strip(),
        )
    if blank:
        raise ValueError(
            f"{path} is incomplete: {len(blank)} row(s) have no 'asserts' value "
            f"(first: {blank[0]}). Agreement on the finished half of a sheet is "
            "not agreement on the sheet."
        )
    if len(labels) != len(rows):
        raise ValueError(f"{path} has duplicate item_ids")
    return labels


class DimensionAgreement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: str
    items: int
    observed_agreement: float
    chance_agreement: float
    kappa: float | None
    standard_error: float | None = None
    ci95: tuple[float, float] | None = None
    paradox_warning: bool = Field(
        default=False,
        description=(
            "High raw agreement with a low kappa, which skewed marginals produce. "
            "Report the raw agreement alongside, or the kappa misleads."
        ),
    )
    note: str | None = None


def _dimension(
    name: str,
    left: dict[str, str],
    right: dict[str, str],
    *,
    note: str | None = None,
) -> DimensionAgreement:
    if not left:
        return DimensionAgreement(
            dimension=name,
            items=0,
            observed_agreement=0.0,
            chance_agreement=0.0,
            kappa=None,
            note=note or "no items both annotators labelled on this dimension",
        )
    result = kappa(left, right)
    return DimensionAgreement(
        dimension=name,
        items=result["items"],
        observed_agreement=result["observed_agreement"],
        chance_agreement=result["chance_agreement"],
        kappa=result["kappa"],
        standard_error=result["standard_error"],
        ci95=result["ci95"],
        paradox_warning=result["paradox_warning"],
        note=note,
    )


def score(
    first: Mapping[str, AdjudicationLabel],
    second: Mapping[str, AdjudicationLabel],
) -> tuple[DimensionAgreement, ...]:
    """Agreement between two annotators, per dimension.

    `asserts` is scored over every item. `direction` and `strength` are scored
    only over items **both** annotators said do assert the relation, because
    neither read a direction off a span they rejected — scoring those as
    agreement on a null label would inflate every number with the easy cases.
    """
    if set(first) != set(second):
        raise ValueError("the two worksheets cover different items")

    shared = sorted(set(first))
    asserts = _dimension(
        "asserts",
        {key: str(first[key].asserts) for key in shared},
        {key: str(second[key].asserts) for key in shared},
    )

    both = [key for key in shared if first[key].asserts and second[key].asserts]
    skipped = len(shared) - len(both)
    note = (
        f"{skipped} of {len(shared)} item(s) excluded: at least one annotator said the "
        "span asserts no relation, so there is no label to compare"
        if skipped
        else None
    )
    direction = _dimension(
        "direction",
        {key: first[key].direction.value for key in both},
        {key: second[key].direction.value for key in both},
        note=note,
    )
    strength = _dimension(
        "strength",
        {key: first[key].strength.value for key in both},
        {key: second[key].strength.value for key in both},
        note=note,
    )
    return (asserts, direction, strength)


def against_draft(
    labels: Mapping[str, AdjudicationLabel], items: Sequence[WorksheetItem], graphs: Mapping
) -> dict[str, float]:
    """How often one annotator's labels match the machine draft.

    Reported separately from `score`, and never as agreement: this measures how
    good the draft was, which is a different question. Mixing the two would let
    a persuasive draft look like two people agreeing.
    """
    by_item = {item.item_id: item for item in items}
    drafted = {
        item_id(graph.query_id, edge.edge_id): edge
        for graph in (graphs.values() if isinstance(graphs, Mapping) else graphs)
        for edge in graph.edges
    }
    kept = [key for key in labels if labels[key].asserts and key in drafted]
    if not kept:
        return {"items": 0, "direction_match": 0.0, "strength_match": 0.0, "dropped": 0.0}
    return {
        "items": len(kept),
        "direction_match": sum(labels[key].direction == drafted[key].direction for key in kept)
        / len(kept),
        "strength_match": sum(labels[key].strength == drafted[key].strength for key in kept)
        / len(kept),
        "dropped": sum(not label.asserts for label in labels.values()) / len(labels),
        "unknown_items": sum(1 for key in labels if key not in by_item),
    }
