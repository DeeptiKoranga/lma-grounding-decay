"""Loader for `data/aliases.yaml`: the surface forms each ontology variable goes by.

**Track A owns `data/aliases.yaml` from task A6 onward** (PLAN_MIDSUB.md, track ownership table).
Track B wrote the starter table and this loader as part of B6, because the
verifier rule layer cannot ask "does this passage mention both variables of the
edge?" without one: the ontology ids are `INR_USD` and `CPI_HEADLINE`, while the
copy says "the rupee", "the local unit" and "retail inflation".

Extending the file is expected and needs no change here. The loader tolerates:

* new variables and new surface forms;
* a variable given as a plain list of forms **or** as a mapping with a
  `surface_forms` key, so A6 can hang retrieval-only metadata off the same entry;
* unknown top-level keys and unknown per-variable keys, which are ignored;
* variables left out entirely - `missing_variables()` lists them, and an
  uncovered variable simply fails the mention rule, which is the safe direction.

It does *not* tolerate a variable id that is not in the closed ontology: with a
closed list that is a typo, not an extension, so `load_aliases` raises and names
the offending ids. Pass `strict=False` to downgrade that to silence.

Matching is case-insensitive, whole-word, tolerant of a plural or possessive
suffix, and runs over presentation-normalised text so a curly apostrophe matches
a straight one. Case-insensitivity here is **not** the relaxation that span
matching refuses (`verify.normalise`, docs/decisions.md D-13): whether a passage
talks about the rupee at all is a different question from whether a quote
attributed to it is faithful.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from schema import load_ontology

from .normalise import normalise_presentation

__all__ = ["ALIASES_PATH", "AliasTable", "load_aliases"]

# The wheel includes the same tracked source table; no second editable copy.
_REPOSITORY_ALIASES = Path(__file__).resolve().parents[2] / "data" / "aliases.yaml"
ALIASES_PATH = (
    Path(__file__).with_name("aliases.yaml")
    if Path(__file__).with_name("aliases.yaml").is_file()
    else _REPOSITORY_ALIASES
)

#: Tolerated after a surface form: "carrier" matches "carriers" and "carrier's".
_SUFFIX = r"(?:'s|es|s)?"
#: Whole-word boundaries that do not treat a hyphen or slash as part of a word.
_LEFT = r"(?<![0-9A-Za-z_])"
_RIGHT = r"(?![0-9A-Za-z_])"


@lru_cache(maxsize=4096)
def _form_pattern(form: str) -> re.Pattern[str]:
    """One surface form, as a whole-word pattern whose spaces match any whitespace."""
    body = r"\s+".join(re.escape(token) for token in form.split())
    return re.compile(_LEFT + body + _SUFFIX + _RIGHT, re.IGNORECASE)


@lru_cache(maxsize=1024)
def _ordered(forms: tuple[str, ...]) -> tuple[str, ...]:
    """Longest form first, so `first_mention` reports the most specific match."""
    return tuple(sorted(forms, key=lambda form: (-len(form), form)))


class AliasTable(BaseModel):
    """The surface forms of every covered variable, plus where they came from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(description="`version` from the YAML file.")
    updated_on: str | None = None
    owner: str | None = None
    source_path: str | None = Field(
        default=None, description="Where this table was loaded from, for error messages."
    )
    surface_forms: dict[str, tuple[str, ...]] = Field(
        default_factory=dict,
        description="Ontology variable id -> its surface forms, presentation-normalised.",
    )

    # -- coverage ---------------------------------------------------------

    def __contains__(self, var_id: object) -> bool:
        return var_id in self.surface_forms

    def __getitem__(self, var_id: str) -> tuple[str, ...]:
        return self.forms_for(var_id)

    def covered_variables(self) -> tuple[str, ...]:
        return tuple(sorted(self.surface_forms))

    def missing_variables(self) -> tuple[str, ...]:
        """Ontology variables with no entry. Track A closes this gap in A6."""
        return tuple(var_id for var_id in load_ontology().ids() if var_id not in self.surface_forms)

    def forms_for(self, var_id: str) -> tuple[str, ...]:
        """Surface forms for a variable, falling back to forms derived from its id.

        The fallback (`CPI_HEADLINE`, `CPI HEADLINE`) almost never occurs in
        running prose, so an uncovered variable fails the mention rule rather
        than passing it by accident.
        """
        configured = self.surface_forms.get(var_id)
        if configured:
            return configured
        return (var_id, var_id.replace("_", " "))

    # -- matching ----------------------------------------------------------

    def mentions(self, var_id: str, text: str) -> bool:
        """True when any surface form of `var_id` appears in `text` as a whole word."""
        return self.first_mention(var_id, text) is not None

    def first_mention(self, var_id: str, text: str) -> str | None:
        """The most specific surface form of `var_id` found in `text`, or None.

        Returns the form as the table holds it, which is what a failure message
        or a tool result should quote - not the raw slice of the passage.
        """
        haystack = normalise_presentation(text)
        for form in _ordered(self.forms_for(var_id)):
            if _form_pattern(form).search(haystack):
                return form
        return None


def _forms_of(entry: object) -> tuple[str, ...]:
    """Read one variable's entry in either accepted shape."""
    if isinstance(entry, str):
        raw: Iterable[object] = [entry]
    elif isinstance(entry, Mapping):
        raw = entry.get("surface_forms") or entry.get("aliases") or []
    elif isinstance(entry, Iterable):
        raw = entry
    else:
        raw = []

    forms: list[str] = []
    for item in raw:
        form = normalise_presentation(str(item))
        if form and form not in forms:
            forms.append(form)
    return tuple(forms)


@lru_cache(maxsize=8)
def load_aliases(path: Path | None = None, *, strict: bool = True) -> AliasTable:
    """Parse and cache `data/aliases.yaml` (or another file, for tests)."""
    source = path or ALIASES_PATH
    if not source.exists():
        raise FileNotFoundError(
            f"alias table not found at {source}. It is tracked in git (see .gitignore); "
            "Track A extends it in task A6."
        )

    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{source} must contain a YAML mapping, found {type(raw).__name__}")

    entries = raw.get("aliases") or {}
    if not isinstance(entries, Mapping):
        raise ValueError(f"{source}: `aliases` must be a mapping of variable id -> surface forms")

    ontology = load_ontology()
    unknown = [var_id for var_id in entries if var_id not in ontology]
    if unknown and strict:
        raise ValueError(
            f"{source} has aliases for {len(unknown)} variable(s) that are not in the closed "
            f"ontology: {', '.join(sorted(unknown))}. With a closed list that is a typo rather "
            "than an extension - fix the id, or add the variable to src/schema/ontology.yaml "
            "(a shared-file change: announce it first)."
        )

    surface_forms = {
        var_id: forms
        for var_id, entry in entries.items()
        if var_id in ontology and (forms := _forms_of(entry))
    }

    return AliasTable(
        version=str(raw.get("version", "0.0.0")),
        updated_on=None if raw.get("updated_on") is None else str(raw["updated_on"]),
        owner=None if raw.get("owner") is None else str(raw["owner"]),
        source_path=str(source),
        surface_forms=surface_forms,
    )
