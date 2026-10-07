from dataclasses import dataclass
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
