"""Seven declared conditions over the same pipeline and resource objects."""

from dataclasses import dataclass

from schema import Condition


@dataclass(frozen=True)
class Settings:
    retrieve: bool = True
    prose: bool = False
    rerank: bool = False
    self_labels: bool = False
    verify: bool = False
    loop: bool = False


SETTINGS = {
    Condition.B0: Settings(retrieve=False, prose=True),
    Condition.B1: Settings(prose=True),
    Condition.B1_R: Settings(rerank=True, prose=True),
    Condition.B2: Settings(self_labels=True),
    Condition.A_NOVERIFY: Settings(self_labels=True, loop=True),
    Condition.A_NOLOOP: Settings(verify=True),
    Condition.M: Settings(verify=True, loop=True),
}
