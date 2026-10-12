from typing import Any

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchHitResponse(ResponseModel):
    path: str
    language: str
    text: str
    start_line: int
    end_line: int
    distance: float
    score: float
    url: str | None = None
    key: str | None = None
    project: str | None = None


class ProjectSearchHitsResponse(ResponseModel):
    project: str | None
    key: str
    index_directory: str
    ref: str | None = None
    commit: str | None = None
    query: str
    results: list[SearchHitResponse]


class CrossProjectSearchHitsResponse(ResponseModel):
    project: None
    projects: list[str]
    query: str
    results: list[SearchHitResponse]


class ListedProjectResponse(ResponseModel):
    key: str
    tracked: bool
    source: str | None
    project: str | None
    index_directory: str | None
    ready: bool
    indexed_at: str | None
    ref: str | None = None
    commit: str | None = None


class ProjectListingResponse(ResponseModel):
    registry: str
    repos: list[ListedProjectResponse]


class IndexStateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    index_directory: str
    schema_version: int | None = None
    project: str | None = None
    source: dict[str, Any] | None = None
    ready: bool = False
    model: str | None = None
    model_sha256: str | None = None
    paths: list[str] | None = None
    languages: list[str] | None = None
    ignores: list[str] | None = None
    max_bytes: int | None = None
    indexed_at: str | None = None
    files: int | None = None
    chunks: int | None = None


class DiagnosticsResponse(ResponseModel):
    version: str
    project: str | None
    key: str
    index_directory: str | None
    model: str
    model_sha256: str
    dimensions: int
    self_distance: float
    device: str
    cocoindex_storage: str
    offline: bool
    network_guard: str
    sqlite: str
    dependencies: dict[str, str]
