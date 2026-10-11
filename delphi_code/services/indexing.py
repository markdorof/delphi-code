from __future__ import annotations

import asyncio
import logging

from ..domain.errors import Failure, FailureKind
from ..domain.indexing_outcomes import IndexingOutcome, ProjectUpToDate, SyncedProject, SyncReport
from ..domain.manifest import Manifest
from ..domain.selection import FileSelection
from ..infrastructure.model import LocalModel
from ..infrastructure.offline import without_network
from ..infrastructure.registry import Entry, Registry
from ..infrastructure.sources import Checkout, GitRemoteSource
from ..infrastructure.store import Store
from .local_model import open_model
from .progress import SILENT, Progress, Stage
from .project_catalog import optional_path_text

logger = logging.getLogger(__name__)


@without_network()
def index_local_project(
    store: Store, name: str, selection: FileSelection, model_location: str, progress: Progress = SILENT
) -> IndexingOutcome:
    project, key, index = store.resolve(name)
    if index and index.project is None:
        raise Failure(
            "usage", f"{key} is a remote repository; update it with delphi-code sync", FailureKind.INVALID_REQUEST
        )
    if project is None or not project.is_dir():
        raise Failure("project_missing", f"Project directory does not exist: {project}", FailureKind.NOT_FOUND)
    model = open_model(model_location)
    checkout = Checkout(project, project, {"kind": "local", "key": key})
    progress.repository_started(key, 1, 1)
    try:
        result = index_checkout(store, checkout, selection, model, progress)
    except Exception as exc:
        progress.repository_failed(Failure.from_exception(exc))
        raise
    progress.repository_finished(result)
    return result


@without_network()
def index_checkout(
    store: Store, checkout: Checkout, selection: FileSelection, model: LocalModel, progress: Progress
) -> IndexingOutcome:
    from ..infrastructure.files import collect
    from ..infrastructure.vector_index import build_index

    index = store.get_or_create(checkout.key, checkout.project)
    with index.lock(True):
        index.read_manifest_compatible_with(model)
        progress.stage_started(Stage.READING_FILES)
        collected = collect(checkout.directory, selection, excluded=model.directory)
        logger.info("Indexing %s: %d files selected, %d skipped", checkout.key, len(collected.files), collected.skipped)
        manifest = Manifest.for_build(checkout.project, checkout.provenance, selection, model)
        index.write_manifest(manifest)
        total = len(collected.files)
        progress.files_embedded(0, total)
        changes = asyncio.run(
            build_index(
                index.directory,
                collected.files,
                model,
                on_files_done=lambda done: progress.files_embedded(done, total),
            )
        )
        progress.stage_started(Stage.SAVING)
        manifest = manifest.completed()
        counts = index.counts()
        index.write_manifest(manifest)
    logger.info("Indexed %s (changes: %s): %s", checkout.key, changes, counts)
    return IndexingOutcome(
        optional_path_text(manifest.project),
        checkout.key,
        str(index.directory),
        manifest.revision,
        counts,
        collected.skipped,
        changes,
    )


def sync_tracked(store: Store, registry: Registry, model_location: str, progress: Progress = SILENT) -> SyncReport:
    return sync(store, registry, registry.entries(), model_location, progress)


def sync(
    store: Store, registry: Registry, entries: list[Entry], model_location: str, progress: Progress = SILENT
) -> SyncReport:
    if not entries:
        return SyncReport(str(registry.path), [])
    model = open_model(model_location)
    projects = []
    for position, entry in enumerate(entries, start=1):
        progress.repository_started(entry.current_key(), position, len(entries))
        try:
            result = _sync_entry(store, entry, model, progress)
            projects.append(SyncedProject(entry.source, result))
            progress.repository_finished(result)
        except Exception as exc:
            logger.exception("Syncing %s failed", entry.source)
            failure = Failure.from_exception(exc)
            projects.append(SyncedProject(entry.source, failure))
            progress.repository_failed(failure)
    return SyncReport(str(registry.path), projects)


def _sync_entry(store: Store, entry: Entry, model: LocalModel, progress: Progress) -> IndexingOutcome | ProjectUpToDate:
    origin = entry.origin
    progress.stage_started(Stage.CHECKING_FOR_CHANGES)
    revision = origin.latest_revision(entry.ref)
    index = store.get(origin.key) if revision else None
    if revision and index and index.manifest.holds(revision.commit, entry.selection, model):
        logger.info("%s is unchanged at %s", index.key, revision.commit)
        return ProjectUpToDate(index.key, str(index.directory), index.manifest.revision)
    if isinstance(origin, GitRemoteSource):
        progress.stage_started(Stage.CLONING)
    with origin.checkout(entry.ref, revision) as checkout:
        return index_checkout(store, checkout, entry.selection, model, progress)
