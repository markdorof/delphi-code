from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Match
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

API_PATH_PREFIX = "api/"
PAGE_FILE = "index.html"
FINGERPRINTED_ASSETS_PREFIX = "assets/"
PAGE_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}
NEVER_CACHED = "no-store"
CACHED_FOREVER = "public, max-age=31536000, immutable"
WEB_UI_NOT_BUILT_MESSAGE = (
    "The web UI isn't built. Run `pnpm --dir web install` and `pnpm --dir web build`, then reload."
)


class WebUiFiles(StaticFiles):
    async def check_config(self):
        if self.directory is not None and Path(self.directory).is_dir():
            await super().check_config()

    async def get_response(self, path: str, scope: Scope) -> Response:
        if path == API_PATH_PREFIX.rstrip("/") or path.startswith(API_PATH_PREFIX):
            raise HTTPException(405 if _api_route_matches_path(scope) else 404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as missing:
            if missing.status_code != 404:
                raise
            response = await self._page_for_client_route(scope)
            path = PAGE_FILE
        response.headers.update(PAGE_SECURITY_HEADERS)
        if path in ("", ".", PAGE_FILE):
            response.headers["Cache-Control"] = NEVER_CACHED
        elif path.startswith(FINGERPRINTED_ASSETS_PREFIX):
            response.headers["Cache-Control"] = CACHED_FOREVER
        return response

    async def _page_for_client_route(self, scope: Scope) -> Response:
        try:
            return await super().get_response(PAGE_FILE, scope)
        except HTTPException as missing:
            if missing.status_code != 404:
                raise
            return PlainTextResponse(WEB_UI_NOT_BUILT_MESSAGE, status_code=503)


def _api_route_matches_path(scope: Scope) -> bool:
    # A mount at "/" fully matches every path, so it wins over an API route whose path matches but whose method doesn't.
    return any(route.matches(scope)[0] is Match.PARTIAL for route in scope["app"].router.routes)
