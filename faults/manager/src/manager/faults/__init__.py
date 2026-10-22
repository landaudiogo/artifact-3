from dataclasses import dataclass
from typing import TypeAlias

@dataclass(frozen=True)
class NamespaceRestart:
    name: str

@dataclass(frozen=True)
class HostRestart:
    pass

ExpectedRestarts: TypeAlias = None | NamespaceRestart | HostRestart

class FaultTrait:

    def prepare(self):
        pass

    def execute(self):
        pass

    def recover(self):
        pass

    def expected_restarts(self) -> ExpectedRestarts:
        return None
