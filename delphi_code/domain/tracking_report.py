from dataclasses import dataclass

from .errors import Failure
from .indexing_outcomes import SyncReport, sync_failure


@dataclass(frozen=True)
class TrackedSource:
    source: str
    key: str

    def to_json(self) -> dict:
        return {"source": self.source, "key": self.key}


@dataclass(frozen=True)
class UntrackedProject:
    key: str
    deleted_index: str | None

    def to_json(self) -> dict:
        return {"key": self.key, "deleted_index": self.deleted_index}


@dataclass(frozen=True)
class TrackingReport:
    registry: str
    tracked: list[TrackedSource]
    sync: SyncReport | None = None
    untracked: list[UntrackedProject] | None = None
    cancelled: bool | None = None

    def to_json(self) -> dict:
        if self.sync is not None:
            report = self.sync.to_json()
        else:
            report = {"registry": self.registry, "repos": [source.to_json() for source in self.tracked]}
        if self.untracked is not None:
            report["removed"] = [project.to_json() for project in self.untracked]
        if self.cancelled is not None:
            report["cancelled"] = self.cancelled
        return report

    def failure_if_any_failed(self) -> Failure | None:
        return sync_failure(self.sync.projects, self.to_json()) if self.sync else None


@dataclass(frozen=True)
class ProjectRemoval:
    key: str
    untracked: bool
    deleted_index: str | None

    def to_json(self) -> dict:
        return {"key": self.key, "untracked": self.untracked, "deleted_index": self.deleted_index}
