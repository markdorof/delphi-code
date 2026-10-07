from dataclasses import asdict

from ..domain.agent_connection import AgentConnection
from ..infrastructure.store import Store
from ..services.progress import SILENT, Progress
from ..ui.text_layout import TextView
from ..ui.views.agent_connections import AgentConnectionsView
from ..ui.views.diagnostics import DiagnosticsView, ModelSetupView
from .response import ControllerResponse


def doctor(project: str, model: str) -> ControllerResponse:
    from ..services.diagnostics import diagnose

    diagnostics = diagnose(model, Store(), project)
    return ControllerResponse(diagnostics, [DiagnosticsView(diagnostics)])


def setup(
    model: str, source: str | None, progress: Progress, connect_agents_to: str | None = None
) -> ControllerResponse:
    from ..services.model_installation import provision

    provisioned = provision(model, source, progress)
    views: list[TextView] = [
        ModelSetupView(
            provisioned["model"], provisioned["index_root"], provisioned["reused"], provisioned["diagnostics"]
        )
    ]
    if connect_agents_to is not None:
        connected = connect(connect_agents_to, [], progress)
        provisioned["agents"] = connected.data["agents"]
        views.extend(connected.views)
    return ControllerResponse(provisioned, views)


def connect(command: str, agents: list[str], progress: Progress = SILENT) -> ControllerResponse:
    from ..services.agent_connections import connect_agents

    return _agent_connections_response(command, connect_agents(command, agents, progress))


def disconnect(command: str, agents: list[str]) -> ControllerResponse:
    from ..services.agent_connections import disconnect_agents

    return _agent_connections_response(command, disconnect_agents(command, agents))


def _agent_connections_response(command: str, connections: list[AgentConnection]) -> ControllerResponse:
    data = [asdict(connection) for connection in connections]
    return ControllerResponse({"command": command, "agents": data}, [AgentConnectionsView(data)])
