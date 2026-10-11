from ...services.application import DelphiCode
from ...services.progress import SILENT, Progress
from ..terminal.text_layout import TextView
from ..terminal.views.agent_connections import AgentConnectionsView
from ..terminal.views.diagnostics import DiagnosticsView, ModelSetupView
from .response import ControllerResponse


def doctor(app: DelphiCode, project: str) -> ControllerResponse:
    diagnostics = app.diagnose(project)
    return ControllerResponse(diagnostics.to_json(), [DiagnosticsView(diagnostics)])


def setup(
    app: DelphiCode, source: str | None, progress: Progress, connect_agents_to: str | None = None
) -> ControllerResponse:
    installed = app.set_up(source, progress, connect_agents_to)
    views: list[TextView] = [ModelSetupView(installed)]
    if installed.agents is not None:
        views.append(AgentConnectionsView(installed.agents))
    return ControllerResponse(installed.to_json(), views)


def connect(app: DelphiCode, command: str, agents: list[str], progress: Progress = SILENT) -> ControllerResponse:
    connected = app.connect_agents(command, agents, progress)
    return ControllerResponse(connected.to_json(), [AgentConnectionsView(connected.connections)])


def disconnect(app: DelphiCode, command: str, agents: list[str]) -> ControllerResponse:
    disconnected = app.disconnect_agents(command, agents)
    return ControllerResponse(disconnected.to_json(), [AgentConnectionsView(disconnected.connections)])
