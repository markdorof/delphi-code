from importlib.metadata import version

from fastapi import Depends, FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..services.application import DelphiCode
from .failures import report_failures_as_json
from .routes import diagnostics, projects, search
from .security import require_token
from .settings import ApiSettings


def create_app(delphi_code: DelphiCode, settings: ApiSettings) -> FastAPI:
    api = FastAPI(
        title="Delphi Code",
        version=version("delphi-code"),
        dependencies=[Depends(require_token)],
        docs_url=None,
        redoc_url=None,
    )
    api.state.delphi_code = delphi_code
    api.state.settings = settings
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_host_names))
    report_failures_as_json(api)
    for routes in (search, projects, diagnostics):
        api.include_router(routes.router)
    return api
