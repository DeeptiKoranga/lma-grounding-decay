"""Loader and lookup for the closed variable ontology (`ontology.yaml`).

The ontology is loaded once and cached. Everything that needs to know whether a
variable exists, or which directions it may take, goes through here rather than
re-reading the YAML.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .enums import Direction

__all__ = ["ONTOLOGY_PATH", "Ontology", "VariableSpec", "load_ontology", "variable_ids"]

ONTOLOGY_PATH = Path(__file__).with_name("ontology.yaml")


class VariableSpec(BaseModel):
    """One macro variable in the closed list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    gloss: str
    group: str
    unit: str
    allowed_directions: tuple[Direction, ...] = Field(min_length=1)
    series_id: str | None = None

    def allows(self, direction: Direction) -> bool:
        return Direction(direction) in self.allowed_directions


class Ontology(BaseModel):
    """The whole closed list, keyed by variable id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    frozen_on: str
    variables: dict[str, VariableSpec]

    def __contains__(self, var_id: object) -> bool:
        return var_id in self.variables

    def __getitem__(self, var_id: str) -> VariableSpec:
        try:
            return self.variables[var_id]
        except KeyError:
            raise KeyError(
                f"{var_id!r} is not in the closed ontology "
                f"({len(self.variables)} variables, version {self.version})"
            ) from None

    def ids(self) -> tuple[str, ...]:
        return tuple(self.variables)

    def by_group(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for var_id, spec in self.variables.items():
            groups.setdefault(spec.group, []).append(var_id)
        return groups


@lru_cache(maxsize=1)
def load_ontology(path: Path | None = None) -> Ontology:
    """Parse and cache `ontology.yaml`."""
    source = path or ONTOLOGY_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    variables = {
        var_id: VariableSpec(id=var_id, **spec) for var_id, spec in raw["variables"].items()
    }
    return Ontology(version=raw["version"], frozen_on=str(raw["frozen_on"]), variables=variables)


def variable_ids() -> tuple[str, ...]:
    """Convenience for prompt construction and JSON-constrained decoding."""
    return load_ontology().ids()
