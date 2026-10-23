"""The alias layer: `data/aliases.yaml` and its loader.

Track A owns the file from task A6. These tests pin the two things Track B's
rule layer needs from it - that it keeps covering the fixture variables, and
that extending it cannot break the loader.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from schema import Graph, load_ontology
from verify import ALIASES_PATH, AliasTable, load_aliases


@pytest.fixture(scope="module")
def aliases() -> AliasTable:
    return load_aliases()


def write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# --- the shipped starter table ---------------------------------------------


def test_the_starter_table_is_where_the_loader_looks():
    assert ALIASES_PATH.exists(), f"expected the alias table at {ALIASES_PATH}"


def test_starter_table_covers_every_variable_in_the_fixture_graph(
    aliases: AliasTable, graph: Graph
):
    # The rule layer fails closed on an uncovered variable, so an edge in the
    # fixture graph would start failing for a missing alias rather than for a
    # real grounding problem.
    for node in graph.nodes:
        assert node.var in aliases, f"{node.var} has no surface forms"


def test_every_covered_variable_is_in_the_closed_ontology(aliases: AliasTable):
    ontology = load_ontology()
    for var_id in aliases.covered_variables():
        assert var_id in ontology


def test_surface_forms_are_non_empty_and_normalised(aliases: AliasTable):
    for var_id in aliases.covered_variables():
        forms = aliases[var_id]
        assert forms, var_id
        for form in forms:
            assert form == form.strip()
            assert "  " not in form
            assert form, var_id
        assert len(set(forms)) == len(forms), f"{var_id} repeats a surface form"


def test_bare_fuel_is_deliberately_not_an_atf_alias(aliases: AliasTable):
    # "fuel" reads equally as ATF_PRICE, FUEL_PRICES or CPI_FUEL_LIGHT. Letting
    # it match all three would make "mentions both variables" meaningless across
    # the whole energy group. See the header of data/aliases.yaml.
    assert "fuel" not in aliases["ATF_PRICE"]
    assert not aliases.mentions("ATF_PRICE", "Fuel accounts for 40 per cent of the cost")


# --- matching semantics -----------------------------------------------------


def test_matching_is_case_insensitive(aliases: AliasTable):
    assert aliases.mentions("INR_USD", "The rupee weakened to 88.12")
    assert aliases.mentions("INR_USD", "the RUPEE weakened to 88.12")


def test_matching_is_whole_word(aliases: AliasTable):
    assert aliases.mentions("ATF_PRICE", "ATF prices rose")
    assert not aliases.mentions("ATF_PRICE", "ATFX prices rose")
    assert not aliases.mentions("CRR", "the aCRRued interest")


def test_plural_and_possessive_suffixes_are_tolerated(aliases: AliasTable):
    # The suffix is tolerated on the end of a whole form, not inside it, so the
    # table still has to carry the forms a journalist actually writes.
    assert aliases.mentions("AIRLINE_COSTS", "an Indian carrier's operating costs")
    assert aliases.mentions("AIRLINE_SHARES", "airline share prices slid")
    assert aliases.mentions("INDIAN_BASKET", "the Indian basket's rise")


def test_a_form_may_span_a_line_break(aliases: AliasTable):
    # Paragraphs extracted from RBI and PPAC PDFs wrap mid-phrase.
    assert aliases.mentions("CPI_HEADLINE", "an upside risk to headline\ninflation")


def test_first_mention_reports_the_most_specific_form(aliases: AliasTable):
    assert aliases.first_mention("INDIAN_BASKET", "The Indian basket of crude rose") == (
        "Indian basket of crude"
    )


def test_first_mention_is_none_when_absent(aliases: AliasTable):
    assert aliases.first_mention("GDP_GROWTH", "The rupee weakened to 88.12") is None


def test_curly_apostrophes_match_straight_ones(aliases: AliasTable):
    assert aliases.mentions("AIRLINE_COSTS", "an Indian carrier\u2019s operating cost")


# --- loader tolerance -------------------------------------------------------


def test_loader_accepts_both_entry_shapes(tmp_path: Path):
    table = load_aliases(
        write(
            tmp_path,
            "both_shapes.yaml",
            """
            version: "9.9.9"
            aliases:
              INR_USD: [rupee, the local unit]
              BRENT:
                surface_forms: [Brent, crude]
                expand_for_bm25: true
                boost: 1.4
            """,
        )
    )
    assert table.version == "9.9.9"
    assert table["INR_USD"] == ("rupee", "the local unit")
    assert table["BRENT"] == ("Brent", "crude")


def test_loader_ignores_unknown_top_level_keys(tmp_path: Path):
    # A6 is expected to hang retrieval metadata off this file.
    table = load_aliases(
        write(
            tmp_path,
            "extra_keys.yaml",
            """
            version: "1.0.0"
            updated_on: "2026-10-25"
            owner: Track A
            stemmer: snowball
            stopwords: [the, a]
            aliases:
              INR_USD: [rupee]
            """,
        )
    )
    assert table.owner == "Track A"
    assert table.updated_on == "2026-10-25"
    assert table.covered_variables() == ("INR_USD",)


def test_an_uncovered_variable_falls_back_to_its_id_and_fails_closed(tmp_path: Path):
    table = load_aliases(
        write(tmp_path, "sparse.yaml", 'version: "1"\naliases:\n  INR_USD: [rupee]\n')
    )
    assert "CPI_HEADLINE" in table.missing_variables()
    assert table.forms_for("CPI_HEADLINE") == ("CPI_HEADLINE", "CPI HEADLINE")
    # The fallback does not occur in running prose, so the mention rule fails
    # rather than passing by accident.
    assert not table.mentions("CPI_HEADLINE", "retail inflation stood at 6.4 per cent")
    assert table.mentions("CPI_HEADLINE", "the CPI_HEADLINE variable")


def test_loader_rejects_a_variable_outside_the_closed_ontology(tmp_path: Path):
    path = write(tmp_path, "typo.yaml", 'version: "1"\naliases:\n  INR_USDD: [rupee]\n')
    with pytest.raises(ValueError, match="INR_USDD"):
        load_aliases(path)
    # ...and can be told to carry on, for a half-finished edit.
    assert load_aliases(path, strict=False).covered_variables() == ()


def test_loader_reports_a_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="A6"):
        load_aliases(tmp_path / "not_here.yaml")


def test_loader_rejects_a_file_that_is_not_a_mapping(tmp_path: Path):
    with pytest.raises(ValueError, match="mapping"):
        load_aliases(write(tmp_path, "list.yaml", "- rupee\n- brent\n"))


def test_loader_tolerates_an_empty_alias_section(tmp_path: Path):
    table = load_aliases(write(tmp_path, "empty.yaml", 'version: "1"\n'))
    assert table.covered_variables() == ()
    assert len(table.missing_variables()) == len(load_ontology().ids())
