from dataclasses import dataclass

from .manifest import IndexedRevision


@dataclass(frozen=True)
class ListedProject:
    key: str
    tracked: bool
    source: str | None
    project: str | None
    index_directory: str | None
    ready: bool
    indexed_at: str | None
    revision: IndexedRevision

    def to_json(self) -> dict:
        return {
            "key": self.key,
            "tracked": self.tracked,
            "source": self.source,
            "project": self.project,
            "index_directory": self.index_directory,
            "ready": self.ready,
            "indexed_at": self.indexed_at,
            **self.revision.to_json(),
        }


@dataclass(frozen=True)
class ProjectListing:
    registry: str
    projects: list[ListedProject]

    def to_json(self) -> dict:
        return {"registry": self.registry, "repos": [project.to_json() for project in self.projects]}
