from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ..domain.errors import Failure, FailureKind

HTTP_STATUS_BY_FAILURE_KIND = {
    FailureKind.INVALID_REQUEST: 400,
    FailureKind.NOT_FOUND: 404,
    FailureKind.INVALID_CONFIGURATION: 500,
    FailureKind.PREREQUISITE_MISSING: 503,
    FailureKind.INDEX_NOT_READY: 409,
    FailureKind.BUSY: 409,
    FailureKind.REMOTE_FAILED: 502,
    FailureKind.OPERATION_FAILED: 500,
}
ERROR_CODE_BY_HTTP_STATUS = {401: "unauthorized", 403: "forbidden_origin", 404: "not_found", 405: "method_not_allowed"}


def report_failures_as_json(api: FastAPI):
    api.add_exception_handler(Failure, _failure_response)
    api.add_exception_handler(RequestValidationError, _invalid_request_response)
    api.add_exception_handler(HTTPException, _http_error_response)


def failure_body(failure: Failure) -> dict:
    body: dict = {"error": failure.to_json()}
    if failure.data is not None:
        body["data"] = failure.data
    return body


async def _failure_response(request: Request, exc: Exception) -> JSONResponse:
    failure = Failure.from_exception(exc)
    return JSONResponse(failure_body(failure), status_code=HTTP_STATUS_BY_FAILURE_KIND[failure.kind])


async def _invalid_request_response(request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    problems = "; ".join(f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in errors)
    return JSONResponse({"error": {"code": "usage", "message": problems}}, status_code=400)


async def _http_error_response(request: Request, exc: Exception) -> JSONResponse:
    error = cast(HTTPException, exc)
    code = ERROR_CODE_BY_HTTP_STATUS.get(error.status_code, "http_error")
    return JSONResponse({"error": {"code": code, "message": str(error.detail)}}, status_code=error.status_code)
