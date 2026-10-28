"""A missing hop denominator is not a measured zero unsupported-edge rate."""

import copy

import pytest

from eval.figures import uer_plot_data


def reviewed_fixture():
    return {
        "status": "reviewed development results; directional only",
        "aggregate": {
            condition: {
                bucket: {
                    "uer": {
                        "mean": value,
                        "queries_with_denominator": count,
                        "queries_without_denominator": 6 - count,
                    }
                }
                for bucket, value, count in [("1", 0, 6), ("2", 0.5, 2), ("3+", None, 0)]
            }
            for condition in ("B1", "M")
        },
    }


def test_missing_and_zero_uer_stay_distinct():
    data = uer_plot_data(reviewed_fixture())
    assert data["B1"][0]["mean"] == 0 and data["B1"][0]["queries"] == 6
    assert data["B1"][2]["mean"] is None and data["B1"][2]["queries"] == 0


@pytest.mark.parametrize(
    "value,count",
    [(float("nan"), 1), (float("inf"), 1), (-0.1, 1), (1.1, 1), (0, 0), (None, 2), (False, 1)],
)
def test_inconsistent_or_invalid_uer_cannot_be_plotted(value, count):
    fixture = reviewed_fixture()
    fixture["aggregate"]["B1"]["1"]["uer"].update(mean=value, queries_with_denominator=count)
    with pytest.raises(ValueError):
        uer_plot_data(fixture)


def test_mismatched_query_populations_and_all_missing_scores_fail():
    fixture = reviewed_fixture()
    changed = copy.deepcopy(fixture)
    changed["aggregate"]["B1"]["2"]["uer"]["queries_without_denominator"] = 0
    with pytest.raises(ValueError, match="same nonempty query set"):
        uer_plot_data(changed)
    for condition in fixture["aggregate"].values():
        for bucket in condition.values():
            bucket["uer"].update(
                mean=None, queries_with_denominator=0, queries_without_denominator=6
            )
    with pytest.raises(ValueError, match="no established-edge"):
        uer_plot_data(fixture)
