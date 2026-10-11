from ...infrastructure.store import Store
from ...services.progress import SILENT, Progress
from ..terminal.text_layout import TextView
from ..terminal.views.agent_connections import AgentConnectionsView
from ..terminal.views.diagnostics import DiagnosticsView, ModelSetupView
from .response import ControllerResponse


def doctor(project: str, model: str) -> ControllerResponse:
    from ...services.diagnostics import diagnose

    diagnostics = diagnose(model, Store(), project)
    return ControllerResponse(diagnostics.to_json(), [DiagnosticsView(diagnostics)])


def setup(
    model: str, source: str | None, progress: Progress, connect_agents_to: str | None = None
) -> ControllerResponse:
    from ...services.model_installation import set_up

    installed = set_up(model, source, progress, connect_agents_to)
    views: list[TextView] = [ModelSetupView(installed)]
    if installed.agents is not None:
        views.append(AgentConnectionsView(installed.agents))
    return ControllerResponse(installed.to_json(), views)


def connect(command: str, agents: list[str], progress: Progress = SILENT) -> ControllerResponse:
    from ...services.agent_connections import connect_agents

    connected = connect_agents(command, agents, progress)
    return ControllerResponse(connected.to_json(), [AgentConnectionsView(connected.connections)])


def disconnect(command: str, agents: list[str]) -> ControllerResponse:
    from ...services.agent_connections import disconnect_agents

    disconnected = disconnect_agents(command, agents)
    return ControllerResponse(disconnected.to_json(), [AgentConnectionsView(disconnected.connections)])
