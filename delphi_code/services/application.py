from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..domain.agent_connection import AgentConnectionsReport
from ..domain.diagnostics import Diagnostics, ModelSetup
from ..domain.index_state import IndexState
from ..domain.indexing_outcomes import IndexingOutcome, SyncReport
from ..domain.project_listing import ProjectListing
from ..domain.search_hits import SearchHits
from ..domain.search_request import SearchRequest
from ..domain.selection import FileSelection
from ..domain.tracking_changes import TrackingChanges
from ..domain.tracking_report import ProjectRemoval, TrackingReport
from ..infrastructure.paths import model_directory
from ..infrastructure.registry import Registry
from ..infrastructure.store import Store
from . import indexing, project_catalog, remote_repositories, searching, tracking
from .progress import SILENT, Progress

if TYPE_CHECKING:
    from ..infrastructure.hosts import Owner, Repository, RepositoryHost


class DelphiCode:
    def __init__(self, model_location: str, store: Store, registry: Registry):
        self._model_location = model_location
        self._store = store
        self._registry = registry

    @classmethod
    def from_environment(cls) -> DelphiCode:
        return cls(str(model_directory()), Store(), Registry())

    def search(self, project: str | None, request: SearchRequest) -> SearchHits:
        return searching.search(self._store, project, request, self._model_location)

    def index(self, project: str, selection: FileSelection, progress: Progress = SILENT) -> IndexingOutcome:
        return indexing.index_local_project(self._store, project, selection, self._model_location, progress)

    def sync(self, progress: Progress = SILENT) -> SyncReport:
        return indexing.sync_tracked(self._store, self._registry, self._model_location, progress)

    def add(
        self,
        sources: list[str],
        ref: str | None,
        selection: FileSelection,
        sync_now: bool,
        progress: Progress = SILENT,
    ) -> TrackingReport:
        return tracking.add_sources(
            self._store, self._registry, sources, ref, selection, self._model_location, sync_now, progress
        )

    def remove(self, name: str, keep_index: bool) -> ProjectRemoval:
        return tracking.remove_project(self._store, self._registry, name, keep_index)

    def status(self, project: str) -> IndexState:
        return project_catalog.status(self._store, project)

    def list_projects(self, only_indexed: bool) -> ProjectListing:
        return project_catalog.list_projects(self._store, self._registry, only_indexed)

    def diagnose(self, project: str) -> Diagnostics:
        from .diagnostics import diagnose

        return diagnose(self._model_location, self._store, project)

    def set_up(
        self, import_from: str | None, progress: Progress = SILENT, connect_agents_to: str | None = None
    ) -> ModelSetup:
        from .model_installation import set_up

        return set_up(self._model_location, import_from, progress, connect_agents_to)

    def connect_agents(self, command: str, agents: list[str], progress: Progress = SILENT) -> AgentConnectionsReport:
        from .agent_connections import connect_agents

        return connect_agents(command, agents, progress)

    def disconnect_agents(self, command: str, agents: list[str]) -> AgentConnectionsReport:
        from .agent_connections import disconnect_agents

        return disconnect_agents(command, agents)

    def hosts_with_credentials(self) -> Sequence[RepositoryHost]:
        return remote_repositories.hosts_with_credentials()

    def tracked_keys(self) -> set[str]:
        return remote_repositories.tracked_keys(self._registry)

    def owners_if_listable(self, host: RepositoryHost, progress: Progress = SILENT) -> list[Owner] | None:
        return remote_repositories.owners_if_listable(host, progress)

    def repositories_of_owner(self, host: RepositoryHost, owner: str, progress: Progress = SILENT) -> list[Repository]:
        return remote_repositories.repositories_of_owner(host, owner, progress)

    def apply_picked_changes(
        self,
        changes: TrackingChanges | None,
        ref: str | None,
        selection: FileSelection,
        sync_now: bool,
        progress: Progress = SILENT,
    ) -> TrackingReport:
        return remote_repositories.apply_picked_changes(
            self._store, self._registry, changes, ref, selection, self._model_location, sync_now, progress
        )
