from typing import Annotated

from fastapi import APIRouter, Depends

from ...services.application import DelphiCode
from ..request_context import delphi_code_of
from ..response_models import IndexStateResponse, ProjectListingResponse

router = APIRouter()


@router.get("/api/projects", response_model=ProjectListingResponse, response_model_exclude_unset=True)
def list_projects(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], indexed: bool = False) -> dict:
    return delphi_code.list_projects(indexed).to_json()


@router.get("/api/projects/status", response_model=IndexStateResponse, response_model_exclude_unset=True)
def status(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], project: str) -> dict:
    return delphi_code.status(project).to_json()
