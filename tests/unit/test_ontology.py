"""The closed ontology must stay closed, complete and internally consistent."""

from __future__ import annotations

import pytest

from schema import Direction, load_ontology, variable_ids

#: Named explicitly in the Phase 0 brief. If one of these disappears, a query in
#: data/eval/queries.jsonl stops being expressible.
REQUIRED = {
    "BRENT",
    "INDIAN_BASKET",
    "INR_USD",
    "CPI_HEADLINE",
    "CPI_CORE",
    "REPO_RATE",
    "GSEC_10Y",
    "FPI_FLOWS",
    "ATF_PRICE",
    "IMPORT_BILL",
    "IMPORTED_INFLATION",
    "LPG_IMPORTS",
    "FUEL_PRICES",
    "RATE_HIKE_EXPECTATIONS",
    "AIRLINE_COSTS",
}


def test_required_variables_present():
    assert set(variable_ids()) >= REQUIRED


def test_ontology_is_about_forty_variables():
    # The proposal says "a closed list of about 40 variables". Drifting far from
    # that is a design change, not a tweak.
    assert 35 <= len(variable_ids()) <= 55


def test_variable_ids_are_screaming_snake_case():
    import re

    for var_id in variable_ids():
        assert re.fullmatch(r"[A-Z][A-Z0-9_]*", var_id), var_id


@pytest.mark.parametrize("var_id", load_ontology().ids())
def test_every_variable_is_fully_specified(var_id: str):
    spec = load_ontology()[var_id]
    assert spec.gloss.strip() and spec.gloss.endswith("."), f"{var_id} needs a one-line gloss"
    assert spec.group.strip()
    assert spec.unit.strip()
    assert spec.allowed_directions, f"{var_id} allows no direction at all"
    assert len(set(spec.allowed_directions)) == len(spec.allowed_directions)


def test_every_variable_allows_up_and_down():
    # `stable` is restricted on latent constructs, but a variable that cannot move
    # either way could never appear in a causal edge.
    for var_id in variable_ids():
        spec = load_ontology()[var_id]
        assert Direction.UP in spec.allowed_directions
        assert Direction.DOWN in spec.allowed_directions


def test_lookup_of_unknown_variable_is_a_clear_error():
    with pytest.raises(KeyError, match="closed ontology"):
        load_ontology()["CRUDE_VIBES"]


def test_groups_are_a_small_closed_set():
    groups = load_ontology().by_group()
    assert set(groups) == {
        "energy",
        "external",
        "prices",
        "policy",
        "rates",
        "banking",
        "fiscal",
        "markets",
        "sectors",
        "real",
    }


#: The seven latent constructs that may not take `stable`. Kept in step with
#: docs/decisions.md row D-08 — if you widen one, close or amend that row.
STABLE_WITHHELD = {
    "AIRLINE_COSTS",
    "FUEL_SUBSIDY",
    "IMPORTED_INFLATION",
    "INFLATION_EXPECTATIONS",
    "OMC_MARGINS",
    "RATE_HIKE_EXPECTATIONS",
    "RBI_FX_INTERVENTION",
}


def test_stable_is_withheld_from_exactly_the_documented_variables():
    ontology = load_ontology()
    withheld = {
        var_id
        for var_id in ontology.ids()
        if Direction.STABLE not in ontology[var_id].allowed_directions
    }
    assert withheld == STABLE_WITHHELD


def test_every_variable_with_a_series_id_names_it_in_snake_case():
    import re

    for var_id in variable_ids():
        series_id = load_ontology()[var_id].series_id
        if series_id is not None:
            assert re.fullmatch(r"[a-z][a-z0-9_]*", series_id), (var_id, series_id)
