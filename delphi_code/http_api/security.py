import secrets

from fastapi import HTTPException, Request

from .settings import ApiSettings

BEARER_PREFIX = "Bearer "
MISSING_TOKEN_MESSAGE = "Send the server's token as Authorization: Bearer TOKEN"


def require_token(request: Request):
    settings: ApiSettings = request.app.state.settings
    presented = request.headers.get("authorization", "")
    token = presented.removeprefix(BEARER_PREFIX) if presented.startswith(BEARER_PREFIX) else ""
    if not secrets.compare_digest(token.encode(), settings.token.encode()):
        raise HTTPException(401, MISSING_TOKEN_MESSAGE)


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    if origin is not None and origin != f"{request.url.scheme}://{request.url.netloc}":
        raise HTTPException(403, f"Requests from {origin} may not change anything")
