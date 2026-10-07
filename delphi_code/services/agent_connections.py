from collections.abc import Callable

from ..domain.agent_connection import AgentConnection, Outcome
from ..domain.errors import ExitCode, Failure
from ..infrastructure.agent_configs import AgentConfig, supported_agents
from .progress import SILENT, Progress


def connect_agents(command: str, requested_names: list[str], progress: Progress = SILENT) -> list[AgentConnection]:
    progress.agents_connection_started()
    return _for_each_agent(requested_names, lambda agent: agent.connect(command))


def disconnect_agents(command: str, requested_names: list[str]) -> list[AgentConnection]:
    return _for_each_agent(requested_names, lambda agent: agent.disconnect(command))


def _for_each_agent(
    requested_names: list[str], change: Callable[[AgentConfig], AgentConnection]
) -> list[AgentConnection]:
    agents = supported_agents()
    if unknown := sorted(set(requested_names) - {agent.name for agent in agents}):
        supported = ", ".join(agent.name for agent in agents)
        raise Failure("usage", f"Unknown agent: {', '.join(unknown)}. Supported: {supported}", ExitCode.USAGE)
    if not requested_names:
        return [change(agent) for agent in agents if agent.installed()]
    return [
        change(agent) if agent.installed() else AgentConnection(agent.name, agent.title, Outcome.NOT_FOUND)
        for agent in agents
        if agent.name in requested_names
    ]
