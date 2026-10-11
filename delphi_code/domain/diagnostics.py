from dataclasses import asdict, dataclass

from .agent_connection import AgentConnection


@dataclass(frozen=True)
class Diagnostics:
    version: str
    project: str | None
    key: str
    index_directory: str | None
    model: str
    model_sha256: str
    dimensions: int
    self_distance: float
    device: str
    cocoindex_storage: str
    offline: bool
    network_guard: str
    sqlite: str
    dependencies: dict[str, str]

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ModelSetup:
    model: str
    index_root: str
    reused: bool
    diagnostics: Diagnostics
    agents: list[AgentConnection] | None = None

    def to_json(self) -> dict:
        report = {
            "model": self.model,
            "index_root": self.index_root,
            "reused": self.reused,
            "diagnostics": self.diagnostics.to_json(),
        }
        if self.agents is not None:
            report["agents"] = [asdict(connection) for connection in self.agents]
        return report
