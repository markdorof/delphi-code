from typing import Annotated

from fastapi import APIRouter, Depends

from ...services.application import DelphiCode
from ..request_context import delphi_code_of
from ..response_models import DiagnosticsResponse

router = APIRouter()


@router.get("/api/doctor", response_model=DiagnosticsResponse)
def doctor(delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], project: str) -> dict:
    return delphi_code.diagnose(project).to_json()
