from importlib.metadata import version
import threading

from fastapi import Depends, FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..services.application import DelphiCode
from .failures import report_failures_as_json
from .routes import diagnostics, installation, projects, search
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
    api.state.write_lock = threading.Lock()
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_host_names))
    report_failures_as_json(api)
    for router in (search.router, projects.router, projects.changes_projects, diagnostics.router, installation.router):
        api.include_router(router)
    return api
