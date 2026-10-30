"""Cohen's kappa for paired independent labels; undefined chance agreement stays null.

Two things are reported alongside kappa because kappa alone misleads on the
sample sizes this project has:

* a **95% interval**, from the usual asymptotic standard error. At 20 items the
  interval is wide enough that a point estimate on its own invites a claim the
  data cannot support.
* a **paradox flag**. When one label dominates, chance agreement approaches the
  observed agreement and kappa collapses even though the annotators agreed on
  almost every item (Feinstein and Cicchetti, 1990). A gold set where nearly
  every span does assert its relation is exactly that situation, so the raw
  agreement has to be printed next to the kappa rather than instead of it.
"""

from collections import Counter
from math import sqrt

#: Raw agreement at or above this, with kappa below PARADOX_KAPPA, is the
#: skewed-marginal case rather than genuine disagreement.
PARADOX_AGREEMENT = 0.8
PARADOX_KAPPA = 0.4


def kappa(left: dict[str, str], right: dict[str, str]) -> dict:
    if not left or set(left) != set(right):
        raise ValueError("agreement requires the same nonempty item ids for both annotators")
    count = len(left)
    l_counts, r_counts = Counter(left.values()), Counter(right.values())
    observed = sum(left[key] == right[key] for key in left) / count
    expected = (
        sum(l_counts[label] * r_counts[label] for label in l_counts.keys() | r_counts.keys())
        / count**2
    )
    value = (observed - expected) / (1 - expected) if expected < 1 else None

    error = ci = None
    if value is not None:
        error = sqrt(observed * (1 - observed) / (count * (1 - expected) ** 2))
        # Clamped to kappa's own range. The asymptotic interval is not bounded
        # and happily runs past +-1 on small, skewed samples, which would print
        # an impossible figure; a clamped bound still says "this sample
        # constrains almost nothing", which is the honest reading.
        ci = (max(-1.0, value - 1.96 * error), min(1.0, value + 1.96 * error))

    return {
        "items": count,
        "observed_agreement": observed,
        "chance_agreement": expected,
        "kappa": value,
        "standard_error": error,
        "ci95": ci,
        "paradox_warning": (
            value is not None and observed >= PARADOX_AGREEMENT and value < PARADOX_KAPPA
        ),
    }


def strength_agreement(left: dict[str, str], right: dict[str, str]) -> dict:
    allowed = {"direct", "conditional", "correlational"}
    if not set(left.values()) | set(right.values()) <= allowed:
        raise ValueError("unknown strength label")
    result = kappa(left, right)
    result["collapse_triggered"] = result["kappa"] is not None and result["kappa"] < 0.5
    if result["collapse_triggered"]:

        def collapse(table):
            return {
                key: "direct" if value == "direct" else "hedged" for key, value in table.items()
            }

        result["direct_vs_hedged"] = kappa(collapse(left), collapse(right))
    return result
