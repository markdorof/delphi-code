from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ...domain.search_request import MAX_SEARCH_LIMIT, SearchRequest
from ...services.application import DelphiCode
from ..request_context import delphi_code_of
from ..response_models import CrossProjectSearchHitsResponse, ProjectSearchHitsResponse

router = APIRouter()


@router.get(
    "/api/search",
    response_model=ProjectSearchHitsResponse | CrossProjectSearchHitsResponse,
    response_model_exclude_unset=True,
)
def search(
    delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)],
    query: str,
    project: str | None = None,
    path: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SEARCH_LIMIT)] = 10,
) -> dict:
    return delphi_code.search(project, SearchRequest(query, path or [], language or [], limit)).to_json()
