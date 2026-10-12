from fastapi import Request

from ..services.application import DelphiCode


def delphi_code_of(request: Request) -> DelphiCode:
    return request.app.state.delphi_code
