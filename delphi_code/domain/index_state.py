from dataclasses import dataclass

from .manifest import Manifest


@dataclass(frozen=True)
class IndexCounts:
    files: int
    chunks: int

    def to_json(self) -> dict:
        return {"files": self.files, "chunks": self.chunks}


@dataclass(frozen=True)
class IndexState:
    key: str
    index_directory: str
    manifest: Manifest
    counts: IndexCounts | None

    def to_json(self) -> dict:
        return {
            "key": self.key,
            "index_directory": self.index_directory,
            **self.manifest.to_json(),
            **(self.counts.to_json() if self.counts else {}),
        }
