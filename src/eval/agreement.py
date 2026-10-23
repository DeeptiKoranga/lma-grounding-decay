"""Cohen's kappa for paired independent labels; undefined chance agreement stays null."""

from collections import Counter


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
    return {
        "items": count,
        "observed_agreement": observed,
        "chance_agreement": expected,
        "kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
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
