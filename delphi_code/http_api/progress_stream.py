from collections.abc import Callable, Iterator
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import queue
import threading
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.responses import Response

from ..domain.errors import Failure, FailureKind
from ..domain.indexing_outcomes import IndexingOutcome, ProjectUpToDate
from ..domain.service_result import ServiceResult
from ..services.progress import Progress, Stage
from .failures import HTTP_STATUS_BY_FAILURE_KIND, failure_body

NDJSON = "application/x-ndjson"
STREAM_DESCRIPTION = (
    'Newline-delimited JSON: one object per progress event ({"event": ...}), then a last line that is either '
    '{"done": RESULT} or {"failed": ERROR, "data": ...}. A failure before the first event is an ordinary error response.'
)


class NdjsonResponse(Response):
    media_type = NDJSON


def streamed_responses(result_model: type[BaseModel]) -> dict[int | str, dict[str, Any]]:
    return {200: {"description": STREAM_DESCRIPTION, "model": result_model}}


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _WriteFinished:
    line: dict
    failure: Failure | None = None


class StreamedProgress(Progress):
    def __init__(self, events: queue.Queue):
        self._events = events

    def owners_listing_started(self, host_name: str, owner_noun: str):
        self._put("owners_listing_started", host=host_name, owner_noun=owner_noun)

    def repositories_listing_started(self, host_name: str, owner: str):
        self._put("repositories_listing_started", host=host_name, owner=owner)

    def listing_finished(self):
        self._put("listing_finished")

    def repository_started(self, key: str, position: int, count: int):
        self._put("repository_started", key=key, position=position, count=count)

    def model_setup_started(self, destination: Path):
        self._put("model_setup_started", destination=str(destination))

    def stage_started(self, stage: Stage):
        self._put("stage_started", stage=str(stage))

    def files_embedded(self, done: int, total: int):
        self._put("files_embedded", done=done, total=total)

    def repository_finished(self, result: IndexingOutcome | ProjectUpToDate):
        self._put("repository_finished", result=result.to_json())

    def repository_failed(self, failure: Failure):
        self._put("repository_failed", error=failure.to_json())

    def model_setup_finished(self, reused: bool):
        self._put("model_setup_finished", reused=reused)

    def agents_connection_started(self):
        self._put("agents_connection_started")

    def _put(self, event: str, **fields):
        self._events.put({"event": event, **fields})


def streamed_write(
    request: Request, write: Callable[[Progress], ServiceResult], result_model: type[BaseModel]
) -> Response:
    one_write_at_a_time: threading.Lock = request.app.state.write_lock
    if not one_write_at_a_time.acquire(blocking=False):
        raise Failure("busy", "Another index, sync, add or setup is running; retry when it finishes", FailureKind.BUSY)
    events: queue.Queue = queue.Queue()
    threading.Thread(target=_run_write, args=(write, result_model, events, one_write_at_a_time), daemon=True).start()
    first = events.get()
    if isinstance(first, _WriteFinished) and first.failure is not None:
        return JSONResponse(failure_body(first.failure), status_code=HTTP_STATUS_BY_FAILURE_KIND[first.failure.kind])
    return StreamingResponse(_ndjson_lines(first, events), media_type=NDJSON)


def _run_write(
    write: Callable[[Progress], ServiceResult],
    result_model: type[BaseModel],
    events: queue.Queue,
    one_write_at_a_time: threading.Lock,
):
    try:
        result = write(StreamedProgress(events))
        done = result_model.model_validate(result.to_json()).model_dump(mode="json", exclude_unset=True)
        finished = _WriteFinished({"done": done})
    except Exception as exc:
        failure = Failure.from_exception(exc)
        logger.warning("HTTP write failed with %s: %s", failure.code, failure, exc_info=not isinstance(exc, Failure))
        finished = _WriteFinished({"failed": failure.to_json(), **_data_of(failure)}, failure)
    finally:
        one_write_at_a_time.release()
    events.put(finished)


def _ndjson_lines(first: dict | _WriteFinished, events: queue.Queue) -> Iterator[str]:
    item = first
    while not isinstance(item, _WriteFinished):
        yield json.dumps(item, ensure_ascii=False) + "\n"
        item = events.get()
    yield json.dumps(item.line, ensure_ascii=False) + "\n"


def _data_of(failure: Failure) -> dict:
    return {"data": failure.data} if failure.data is not None else {}
