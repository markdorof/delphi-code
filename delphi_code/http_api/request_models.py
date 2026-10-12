from pydantic import BaseModel, ConfigDict, Field

from ..domain.selection import DEFAULT_MAX_BYTES, FileSelection


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileSelectionRequest(RequestModel):
    path: list[str] = Field(default_factory=list, description="Project-relative globs, such as src/*")
    language: list[str] = Field(default_factory=list, description="Languages, such as python or typescript")
    ignore: list[str] = Field(default_factory=list, description="Extra gitignore-style patterns to skip")
    max_bytes: int = Field(DEFAULT_MAX_BYTES, ge=1, description="Skip files larger than this")

    def selection(self) -> FileSelection:
        return FileSelection(self.path, self.language, self.ignore, self.max_bytes)


class IndexRequest(FileSelectionRequest):
    project: str = Field(description="Absolute project path, indexed key or folder name")


class AddRequest(FileSelectionRequest):
    sources: list[str] = Field(min_length=1, description="Project directories or host/owner/repository")
    ref: str | None = Field(None, description="Branch or tag of remote repositories")
    no_sync: bool = Field(False, description="Only update the registry")


class SetupRequest(RequestModel):
    import_from: str | None = Field(None, alias="from", description="Prepared model directory to import")
