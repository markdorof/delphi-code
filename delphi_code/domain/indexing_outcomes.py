from dataclasses import asdict, dataclass

from .errors import Failure, FailureKind
from .index_state import IndexCounts
from .manifest import IndexedRevision


@dataclass(frozen=True)
class FileChanges:
    num_execution_starts: int = 0
    num_unchanged: int = 0
    num_adds: int = 0
    num_deletes: int = 0
    num_reprocesses: int = 0
    num_errors: int = 0

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class IndexingOutcome:
    project: str | None
    key: str
    index_directory: str
    revision: IndexedRevision
    counts: IndexCounts
    skipped: int
    changes: FileChanges | None

    def to_json(self) -> dict:
        return {
            "project": self.project,
            "key": self.key,
            "index_directory": self.index_directory,
            **self.revision.to_json(),
            **self.counts.to_json(),
            "skipped": self.skipped,
            "incremental": self.changes.to_json() if self.changes else {},
        }


@dataclass(frozen=True)
class ProjectUpToDate:
    key: str
    index_directory: str
    revision: IndexedRevision

    def to_json(self) -> dict:
        return {"project": None, "key": self.key, "index_directory": self.index_directory, **self.revision.to_json()}


@dataclass(frozen=True)
class SyncedProject:
    source: str
    result: IndexingOutcome | ProjectUpToDate | Failure

    @property
    def failed(self) -> bool:
        return isinstance(self.result, Failure)

    def to_json(self) -> dict:
        if isinstance(self.result, Failure):
            return {"source": self.source, "ok": False, "error": self.result.to_json()}
        unchanged = isinstance(self.result, ProjectUpToDate)
        return {"source": self.source, "ok": True, "unchanged": unchanged, **self.result.to_json()}


@dataclass(frozen=True)
class SyncReport:
    registry: str
    projects: list[SyncedProject]

    def to_json(self) -> dict:
        return {"registry": self.registry, "repos": [project.to_json() for project in self.projects]}

    def failure_if_any_failed(self) -> Failure | None:
        return sync_failure(self.projects, self.to_json())


def sync_failure(projects: list[SyncedProject], report: dict) -> Failure | None:
    failed = [project.source for project in projects if project.failed]
    if not failed:
        return None
    return Failure(
        "sync_failed",
        f"{len(failed)} of {len(projects)} tracked projects failed: {', '.join(failed)}",
        FailureKind.OPERATION_FAILED,
        report,
    )
