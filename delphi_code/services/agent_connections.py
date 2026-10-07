from collections.abc import Callable
from dataclasses import replace

from ..domain.agent_connection import AgentConnection, Outcome
from ..domain.errors import ExitCode, Failure
from ..infrastructure.agent_configs import AgentConfig, install_skill, remove_skill, supported_agents
from .progress import SILENT, Progress

OUTCOMES_WITH_A_WORKING_SERVER = {Outcome.ADDED, Outcome.ALREADY_CONFIGURED}
OUTCOMES_AFTER_WHICH_THE_SKILL_GOES = {Outcome.REMOVED, Outcome.NOT_CONFIGURED, Outcome.KEPT}


def connect_agents(command: str, requested_names: list[str], progress: Progress = SILENT) -> list[AgentConnection]:
    progress.agents_connection_started()
    return _for_each_agent(requested_names, lambda agent: _connect_with_skill(agent, command))


def disconnect_agents(command: str, requested_names: list[str]) -> list[AgentConnection]:
    # Codex and OpenCode read the same skills folder, so the skill stays while either keeps its server.
    staying = [agent for agent in supported_agents() if requested_names and agent.name not in requested_names]
    still_read = {
        agent.skills_directory
        for agent in staying
        if agent.skills_directory and agent.installed() and agent.configured()
    }
    return _for_each_agent(
        requested_names,
        lambda agent: _disconnect_with_skill(agent, command, remove_the_skill=agent.skills_directory not in still_read),
    )


def _connect_with_skill(agent: AgentConfig, command: str) -> AgentConnection:
    connection = agent.connect(command)
    if (
        agent.skills_directory is None
        or connection.outcome not in OUTCOMES_WITH_A_WORKING_SERVER
        or connection.plugin_brings_the_skill
    ):
        return connection
    try:
        return replace(connection, skill=str(install_skill(agent.skills_directory)))
    except OSError as exc:
        return replace(connection, outcome=Outcome.FAILED, detail=f"cannot install the skill: {exc}")


def _disconnect_with_skill(agent: AgentConfig, command: str, remove_the_skill: bool) -> AgentConnection:
    connection = agent.disconnect(command)
    if (
        agent.skills_directory is None
        or not remove_the_skill
        or connection.outcome not in OUTCOMES_AFTER_WHICH_THE_SKILL_GOES
    ):
        return connection
    try:
        removed = remove_skill(agent.skills_directory)
    except OSError as exc:
        return replace(connection, outcome=Outcome.FAILED, detail=f"cannot remove the skill: {exc}")
    return replace(connection, skill=str(removed) if removed else None)


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
