from dataclasses import dataclass

from .manifest import IndexedRevision


@dataclass(frozen=True)
class HitProject:
    key: str
    project: str | None


@dataclass(frozen=True)
class SearchHit:
    path: str
    language: str
    text: str
    start_line: int
    end_line: int
    distance: float
    score: float
    url: str | None = None
    found_in: HitProject | None = None

    def to_json(self) -> dict:
        fields = {
            "path": self.path,
            "language": self.language,
            "text": self.text,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "distance": self.distance,
            "score": self.score,
        }
        if self.url is not None:
            fields["url"] = self.url
        if self.found_in is not None:
            fields |= {"key": self.found_in.key, "project": self.found_in.project}
        return fields


@dataclass(frozen=True)
class ProjectSearchHits:
    project: str | None
    key: str
    index_directory: str
    revision: IndexedRevision
    query: str
    hits: list[SearchHit]

    def to_json(self) -> dict:
        return {
            "project": self.project,
            "key": self.key,
            "index_directory": self.index_directory,
            **self.revision.to_json(),
            "query": self.query,
            "results": [hit.to_json() for hit in self.hits],
        }


@dataclass(frozen=True)
class CrossProjectSearchHits:
    projects: list[str]
    query: str
    hits: list[SearchHit]

    def to_json(self) -> dict:
        return {
            "project": None,
            "projects": self.projects,
            "query": self.query,
            "results": [hit.to_json() for hit in self.hits],
        }


SearchHits = ProjectSearchHits | CrossProjectSearchHits
