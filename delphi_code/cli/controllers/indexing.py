from ...domain.indexing_outcomes import SyncedProject
from ...domain.selection import FileSelection
from ...domain.tracking_report import TrackingReport
from ...services.application import DelphiCode
from ..terminal.progress import TerminalProgress
from ..terminal.text_layout import Message, TextView
from ..terminal.views.indexing import IndexingOutcomesSummaryView, IndexingOutcomeView
from ..terminal.views.tracking import TRACK_A_PROJECT_HINT, NewlyTrackedProjectsView, UntrackedProjectView
from . import repository_picking
from .repository_picking import Prompts
from .response import ControllerResponse


def index(app: DelphiCode, project: str, selection: FileSelection, progress: TerminalProgress) -> ControllerResponse:
    outcome = app.index(project, selection, progress)
    view = IndexingOutcomeView(outcome, shows_headline=not progress.showed_outcome_lines)
    return ControllerResponse(outcome.to_json(), [view])


def sync(app: DelphiCode, projects: list[str], progress: TerminalProgress) -> ControllerResponse:
    synced = app.sync(projects, progress)
    if failure := synced.failure_if_any_failed():
        raise failure
    if not synced.projects:
        return ControllerResponse(synced.to_json(), [Message("No projects are tracked.", TRACK_A_PROJECT_HINT)])
    return ControllerResponse(synced.to_json(), [_indexing_outcomes_view(synced.projects, progress)])


def add(
    app: DelphiCode,
    sources: list[str],
    ref: str | None,
    selection: FileSelection,
    sync_now: bool,
    progress: TerminalProgress,
    prompts: Prompts,
) -> ControllerResponse:
    if sources:
        added = app.add(sources, ref, selection, sync_now, progress)
    else:
        added = repository_picking.add_picked(app, ref, selection, sync_now, progress, prompts)
    if failure := added.failure_if_any_failed():
        raise failure
    return ControllerResponse(added.to_json(), _tracking_change_views(added, progress))


def _tracking_change_views(added: TrackingReport, progress: TerminalProgress) -> list[TextView]:
    if added.cancelled:
        return [Message("Cancelled; nothing changed")]
    untracked = added.untracked or []
    synced = added.sync.projects if added.sync else []
    if not (synced or added.tracked) and not untracked:
        return [Message("Nothing changed")]
    views: list[TextView] = [
        _indexing_outcomes_view(synced, progress)
        if synced
        else NewlyTrackedProjectsView([source.key for source in added.tracked])
    ]
    views.extend(UntrackedProjectView(project.key, True, project.deleted_index) for project in untracked)
    return views


def _indexing_outcomes_view(projects: list[SyncedProject], progress: TerminalProgress) -> TextView:
    return IndexingOutcomesSummaryView(projects, lists_each_outcome=not progress.showed_outcome_lines)
