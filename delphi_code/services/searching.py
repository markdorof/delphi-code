from dataclasses import replace

from ..domain.errors import Failure, FailureKind
from ..domain.manifest import Manifest
from ..domain.search_hits import CrossProjectSearchHits, HitProject, ProjectSearchHits, SearchHit, SearchHits
from ..domain.search_request import SearchRequest
from ..infrastructure.model import LocalModel
from ..infrastructure.offline import without_network
from ..infrastructure.store import Index, Store
from .local_model import open_model
from .project_catalog import optional_path_text, resolve_indexed


def search(store: Store, project: str | None, request: SearchRequest, model_location: str) -> SearchHits:
    if project is None:
        return search_everywhere(store, request, model_location)
    return search_project(store, project, request, model_location)


@without_network()
def search_project(store: Store, name: str, request: SearchRequest, model_location: str) -> ProjectSearchHits:
    key, index = resolve_indexed(store, name)
    model = open_model(model_location)
    with index.lock(False):
        manifest = index.read_searchable_manifest(model)
        hits = _search_index(index, manifest, request, _query_vector(model, request))
    return ProjectSearchHits(
        optional_path_text(manifest.project), key, str(index.directory), manifest.revision, request.query, hits
    )


@without_network()
def search_everywhere(store: Store, request: SearchRequest, model_location: str) -> CrossProjectSearchHits:
    indexes, unrecognized = store.all(), store.unrecognized_directories()
    if not indexes and not unrecognized:
        raise Failure(
            "index_missing",
            "No indexes exist; run delphi-code index -p /absolute/path/to/project first",
            FailureKind.INDEX_NOT_READY,
        )
    if unrecognized:
        raise Failure(
            "index_incompatible", f"{unrecognized[0]}: Index has no valid project identity", FailureKind.INDEX_NOT_READY
        )
    model = open_model(model_location)
    query_vector = _query_vector(model, request)
    hits: list[SearchHit] = []
    projects = []
    for index in indexes:
        try:
            with index.lock(False):
                manifest = index.read_searchable_manifest(model)
                found_in = HitProject(index.key, optional_path_text(manifest.project))
                hits.extend(
                    replace(hit, found_in=found_in) for hit in _search_index(index, manifest, request, query_vector)
                )
                projects.append(found_in.project or index.key)
        except Failure as exc:
            raise Failure(exc.code, f"{index.directory}: {exc}", exc.kind) from exc
    hits.sort(key=_cross_project_rank)
    return CrossProjectSearchHits(sorted(projects), request.query, hits[: request.limit])


def _query_vector(model: LocalModel, request: SearchRequest) -> bytes:
    return model.embed([request.query])[0].tobytes()


def _search_index(index: Index, manifest: Manifest, request: SearchRequest, query_vector: bytes) -> list[SearchHit]:
    hits = index.search(query_vector, request.paths, request.languages, request.limit)
    return [replace(hit, url=manifest.web_link(hit.path, hit.start_line, hit.end_line)) for hit in hits]


def _cross_project_rank(hit: SearchHit) -> tuple:
    key = hit.found_in.key if hit.found_in else ""
    return (hit.distance, key, hit.path, hit.start_line, hit.end_line, hit.text)
