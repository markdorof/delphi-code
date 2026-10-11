from ...services.application import DelphiCode
from ..terminal.text_layout import Message
from ..terminal.views.index_state import IndexStateView
from ..terminal.views.project_table import ProjectTableView
from ..terminal.views.tracking import TRACK_A_PROJECT_HINT, UntrackedProjectView
from .response import ControllerResponse


def status(app: DelphiCode, project: str) -> ControllerResponse:
    state = app.status(project)
    return ControllerResponse(state.to_json(), [IndexStateView(state)])


def list_tracked(app: DelphiCode, only_indexed: bool) -> ControllerResponse:
    listing = app.list_projects(only_indexed)
    if not listing.projects:
        nothing_listed = "No projects are indexed yet." if only_indexed else "No projects are tracked or indexed yet."
        return ControllerResponse(listing.to_json(), [Message(nothing_listed, TRACK_A_PROJECT_HINT)])
    return ControllerResponse(listing.to_json(), [ProjectTableView(listing.projects)])


def remove(app: DelphiCode, name: str, keep_index: bool) -> ControllerResponse:
    removal = app.remove(name, keep_index)
    view = UntrackedProjectView(removal.key, removal.untracked, removal.deleted_index)
    return ControllerResponse(removal.to_json(), [view])
