import shlex

from ..domain.errors import Failure, FailureKind
from ..domain.index_state import IndexState
from ..domain.manifest import IndexedRevision
from ..domain.project_listing import ListedProject, ProjectListing
from ..infrastructure.registry import Registry
from ..infrastructure.store import Index, ResolvedProject, Store


def resolve_existing(store: Store, name: str) -> ResolvedProject:
    resolved = store.resolve(name)
    directory_exists = resolved.project is not None and resolved.project.is_dir()
    if not directory_exists and resolved.index is None:
        raise Failure("project_missing", f"Project directory does not exist: {resolved.project}", FailureKind.NOT_FOUND)
    return resolved


def resolve_indexed(store: Store, name: str) -> tuple[str, Index]:
    project, key, index = resolve_existing(store, name)
    if index is None:
        raise Failure(
            "index_missing",
            f"No index exists; run delphi-code index -p {shlex.quote(str(project))}",
            FailureKind.INDEX_NOT_READY,
        )
    return key, index


def status(store: Store, name: str) -> IndexState:
    key, index = resolve_indexed(store, name)
    with index.lock(False):
        manifest = index.read_manifest()
        return IndexState(key, str(index.directory), manifest, index.counts() if manifest.ready else None)


def list_projects(store: Store, registry: Registry, only_indexed: bool = False) -> ProjectListing:
    tracked = {entry.current_key(): entry for entry in registry.entries()}
    stored = {index.key: index for index in store.all()}
    listed_keys = set(stored) if only_indexed else set(tracked) | set(stored)
    projects = []
    for key in sorted(listed_keys):
        index, entry = stored.get(key), tracked.get(key)
        manifest = index.manifest if index else None
        projects.append(
            ListedProject(
                key=key,
                tracked=entry is not None,
                source=entry.source if entry else None,
                project=optional_path_text(manifest.project) if manifest else None,
                index_directory=str(index.directory) if index else None,
                ready=manifest.ready if manifest else False,
                indexed_at=manifest.indexed_at if manifest else None,
                revision=manifest.revision if manifest else IndexedRevision(),
            )
        )
    return ProjectListing(str(registry.path), projects)


def optional_path_text(path) -> str | None:
    return str(path) if path else None
