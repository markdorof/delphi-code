from dataclasses import asdict, dataclass
from enum import StrEnum


class Outcome(StrEnum):
    ADDED = "added"
    ALREADY_CONFIGURED = "already_configured"
    REMOVED = "removed"
    NOT_CONFIGURED = "not_configured"
    KEPT = "kept"
    NOT_FOUND = "not_found"
    FAILED = "failed"


@dataclass(frozen=True)
class AgentConnection:
    agent: str
    title: str
    outcome: Outcome
    config: str | None = None
    detail: str | None = None
    skill: str | None = None
    plugin_brings_the_skill: bool = False


@dataclass(frozen=True)
class AgentConnectionsReport:
    command: str
    connections: list[AgentConnection]

    def to_json(self) -> dict:
        return {"command": self.command, "agents": [asdict(connection) for connection in self.connections]}
