from ...domain.indexing_outcomes import SyncedProject
from ...domain.selection import FileSelection
from ...domain.tracking_report import TrackingReport
from ...infrastructure.registry import Registry
from ...infrastructure.store import Store
from ...services import indexing, tracking
from ...services.progress import Progress
from ..terminal.text_layout import Message, TextView
from ..terminal.views.indexing import IndexingOutcomesSummaryView, IndexingOutcomeView
from ..terminal.views.tracking import TRACK_A_PROJECT_HINT, NewlyTrackedProjectsView, UntrackedProjectView
from . import repository_picking
from .repository_picking import Prompts
from .response import ControllerResponse


def index(project: str, selection: FileSelection, model: str, progress: Progress) -> ControllerResponse:
    outcome = indexing.index_local_project(Store(), project, selection, model, progress)
    view = IndexingOutcomeView(outcome, shows_headline=not progress.showed_outcome_lines)
    return ControllerResponse(outcome.to_json(), [view])


def sync(model: str, progress: Progress) -> ControllerResponse:
    synced = indexing.sync_tracked(Store(), Registry(), model, progress)
    if failure := synced.failure_if_any_failed():
        raise failure
    if not synced.projects:
        return ControllerResponse(synced.to_json(), [Message("No projects are tracked.", TRACK_A_PROJECT_HINT)])
    return ControllerResponse(synced.to_json(), [_indexing_outcomes_view(synced.projects, progress)])


def add(
    sources: list[str],
    ref: str | None,
    selection: FileSelection,
    model: str,
    sync_now: bool,
    progress: Progress,
    prompts: Prompts,
) -> ControllerResponse:
    if sources:
        added = tracking.add_sources(Store(), Registry(), sources, ref, selection, model, sync_now, progress)
    else:
        added = repository_picking.add_picked(ref, selection, model, sync_now, progress, prompts)
    if failure := added.failure_if_any_failed():
        raise failure
    return ControllerResponse(added.to_json(), _tracking_change_views(added, progress))


def _tracking_change_views(added: TrackingReport, progress: Progress) -> list[TextView]:
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


def _indexing_outcomes_view(projects: list[SyncedProject], progress: Progress) -> TextView:
    return IndexingOutcomesSummaryView(projects, lists_each_outcome=not progress.showed_outcome_lines)
