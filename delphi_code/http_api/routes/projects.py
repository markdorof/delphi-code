from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...services.application import DelphiCode
from ..progress_stream import NdjsonResponse, streamed_responses, streamed_write
from ..request_context import delphi_code_of
from ..request_models import AddRequest, IndexRequest
from ..response_models import (
    IndexingOutcomeResponse,
    IndexStateResponse,
    ProjectListingResponse,
    ProjectRemovalResponse,
    SyncReportResponse,
    TrackingReportResponse,
)
from ..security import require_same_origin

router = APIRouter()
changes_projects = APIRouter(dependencies=[Depends(require_same_origin)])


@router.get("/api/projects", response_model=ProjectListingResponse, response_model_exclude_unset=True)
def list_projects(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], indexed: bool = False) -> dict:
    return delphi_code.list_projects(indexed).to_json()


@router.get("/api/projects/status", response_model=IndexStateResponse, response_model_exclude_unset=True)
def status(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], project: str) -> dict:
    return delphi_code.status(project).to_json()


@changes_projects.post(
    "/api/projects/index", response_class=NdjsonResponse, responses=streamed_responses(IndexingOutcomeResponse)
)
def index(request: Request, delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], body: IndexRequest):
    return streamed_write(
        request, lambda progress: delphi_code.index(body.project, body.selection(), progress), IndexingOutcomeResponse
    )


@changes_projects.post(
    "/api/projects/sync", response_class=NdjsonResponse, responses=streamed_responses(SyncReportResponse)
)
def sync(request: Request, delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)]):
    return streamed_write(request, delphi_code.sync, SyncReportResponse)


@changes_projects.post(
    "/api/projects", response_class=NdjsonResponse, responses=streamed_responses(TrackingReportResponse)
)
def add(request: Request, delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], body: AddRequest):
    return streamed_write(
        request,
        lambda progress: delphi_code.add(body.sources, body.ref, body.selection(), not body.no_sync, progress),
        TrackingReportResponse,
    )


@changes_projects.delete("/api/projects", response_model=ProjectRemovalResponse)
def remove(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], name: str, keep_index: bool = False) -> dict:
    return delphi_code.remove(name, keep_index).to_json()
