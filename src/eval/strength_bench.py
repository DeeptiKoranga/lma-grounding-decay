"""B10 - strength and direction checks against public causal-language data.

The proposal uses FinCausal (Mariko et al., 2020) and the causal-language data
of Yu et al. (2019) as 200-item checks of causal detection and strength. Neither
is used for training; both are diagnostics on labelled text that nobody on this
project wrote, which is what makes them worth running.

Yu et al.'s four classes map onto our three strength levels **exactly**, because
Table 2 of the proposal adapted its scheme from that paper. The mapping is not
the obvious one, and getting it backwards would invert every number:

======  =============================  ===================
label   Yu et al. (2019)               our `Strength`
======  =============================  ===================
0       No relationship                *excluded* (1,356)
1       Direct causal                  ``direct`` (494)
2       Conditional causal             ``conditional`` (213)
3       Correlational                  ``correlational`` (998)
======  =============================  ===================

Note that 1 is *direct* and 3 is *correlational*, not the other way round. The
counts are from the published README and are asserted on load, so a reordered
or re-released file cannot silently change the mapping.

The cue baseline
----------------
`cue_strength` is a deterministic classifier built from the cue lists in
proposal Table 2 - "caused, due to, driven by" for direct, "could, may, if" for
conditional, "amid, as, after" for correlational. It exists so the LLM verifier
has something to beat. A verifier that cannot beat a word list on strength is
not doing the work the project credits it with, and that is a reportable
finding rather than an embarrassment.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from schema import Strength

__all__ = [
    "CUES",
    "YU_EXPECTED_COUNTS",
    "YU_LABEL_TO_STRENGTH",
    "ClassScore",
    "ScoreReport",
    "cue_strength",
    "score",
    "yu_strength",
]

#: Yu et al. (2019) label -> our strength. 0 (no relationship) has no strength.
YU_LABEL_TO_STRENGTH: dict[int, Strength] = {
    1: Strength.DIRECT,
    2: Strength.CONDITIONAL,
    3: Strength.CORRELATIONAL,
}

#: Published class counts, asserted on load so a re-release cannot shift the mapping.
YU_EXPECTED_COUNTS: dict[int, int] = {0: 1356, 1: 494, 2: 213, 3: 998}

#: Cue lists from proposal Table 2. Order matters: the first match wins, and
#: hedging outranks causal wording because "may have been caused by" is
#: conditional, not direct.
CUES: dict[Strength, tuple[str, ...]] = {
    Strength.CONDITIONAL: (
        r"\bcould\b",
        r"\bmay\b",
        r"\bmight\b",
        r"\bappears? to\b",
        r"\bseems? to\b",
        r"\bsuggests?\b",
        r"\bpotentially\b",
        r"\blikely to\b",
        r"\bif\b",
        r"\bupside risk\b",
        r"\bexpected to\b",
        r"\bcan\b",
    ),
    Strength.DIRECT: (
        r"\bcaused?\b",
        r"\bcausing\b",
        r"\bdue to\b",
        r"\bdriven by\b",
        r"\bweighed on\b",
        r"\bled to\b",
        r"\bresulted? in\b",
        r"\bbecause of\b",
        r"\bowing to\b",
        r"\bimproves?\b",
        r"\breduces?\b",
        r"\bincreases?\b",
        r"\beffective at\b",
    ),
    Strength.CORRELATIONAL: (
        r"\bassociated with\b",
        r"\bcorrelat",
        r"\bamid\b",
        r"\balongside\b",
        r"\blinked to\b",
        r"\brelated to\b",
        r"\bpredict",
        r"\bafter\b",
        r"\bas\b",
    ),
}

#: Tried in this order, so hedging beats causal wording and both beat association.
_CUE_ORDER: tuple[Strength, ...] = (
    Strength.CONDITIONAL,
    Strength.DIRECT,
    Strength.CORRELATIONAL,
)

_COMPILED: dict[Strength, list[re.Pattern[str]]] = {
    strength: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for strength, patterns in CUES.items()
}


def yu_strength(label: int | str) -> Strength | None:
    """Map a Yu et al. label onto our scheme. None for 'no relationship'."""
    return YU_LABEL_TO_STRENGTH.get(int(label))


def cue_strength(sentence: str) -> Strength | None:
    """The non-AI baseline: first matching cue class wins, else None."""
    for strength in _CUE_ORDER:
        if any(pattern.search(sentence) for pattern in _COMPILED[strength]):
            return strength
    return None


class ClassScore(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    support: int
    precision: float
    recall: float
    f1: float


class ScoreReport(BaseModel):
    """Macro-averaged scores plus the confusion matrix, for a report table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n: int
    accuracy: float
    macro_f1: float
    per_class: tuple[ClassScore, ...]
    confusion: dict[str, dict[str, int]] = Field(
        description="confusion[gold][predicted] = count; 'none' is an abstention.",
    )
    abstentions: int = 0

    def row(self, label: str) -> ClassScore:
        return next(c for c in self.per_class if c.label == label)


def _f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def score(
    gold: Sequence[Strength],
    predicted: Sequence[Strength | None],
    *,
    labels: Iterable[Strength] = (),
) -> ScoreReport:
    """Per-class precision, recall and F1, macro-averaged.

    An abstention (`None`) counts against recall for its gold class and is never
    credited as correct, so a classifier cannot buy precision by declining the
    hard cases.
    """
    if len(gold) != len(predicted):
        raise ValueError(f"gold has {len(gold)} items, predicted has {len(predicted)}")
    if not gold:
        raise ValueError("cannot score an empty benchmark")

    classes = tuple(labels) or tuple(Strength)
    confusion: dict[str, dict[str, int]] = {
        str(g): {str(p): 0 for p in (*classes, "none")} for g in classes
    }
    for g, p in zip(gold, predicted, strict=True):
        confusion[str(g)][str(p) if p is not None else "none"] += 1

    support = Counter(str(g) for g in gold)
    per_class: list[ClassScore] = []
    for cls in classes:
        name = str(cls)
        tp = confusion[name][name]
        predicted_as = sum(1 for p in predicted if p is not None and str(p) == name)
        precision = tp / predicted_as if predicted_as else 0.0
        recall = tp / support[name] if support[name] else 0.0
        per_class.append(
            ClassScore(
                label=name,
                support=support[name],
                precision=precision,
                recall=recall,
                f1=_f1(precision, recall),
            )
        )

    correct = sum(
        1 for g, p in zip(gold, predicted, strict=True) if p is not None and str(p) == str(g)
    )
    return ScoreReport(
        n=len(gold),
        accuracy=correct / len(gold),
        macro_f1=sum(c.f1 for c in per_class) / len(per_class),
        per_class=tuple(per_class),
        confusion=confusion,
        abstentions=sum(1 for p in predicted if p is None),
    )
