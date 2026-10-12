from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from ...services.application import DelphiCode
from ..progress_stream import STREAMED_RESPONSE, streamed_write
from ..request_context import delphi_code_of
from ..request_models import SetupRequest
from ..response_models import ModelSetupResponse
from ..security import require_same_origin

router = APIRouter(dependencies=[Depends(require_same_origin)])


@router.post("/api/setup", response_class=Response, responses=STREAMED_RESPONSE)
def setup(request: Request, delphi_code: Annotated[DelphiCode, Depends(delphi_code_of)], body: SetupRequest):
    return streamed_write(request, lambda progress: delphi_code.set_up(body.import_from, progress), ModelSetupResponse)
