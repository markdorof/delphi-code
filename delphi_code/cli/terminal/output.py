from contextlib import redirect_stdout
import json
import os
import sys

from ...domain.errors import Failure, FailureKind
from .text_layout import TextStyle, TextView

OUTPUT_SCHEMA_VERSION = 1
EXIT_CODE_BY_FAILURE_KIND = {
    FailureKind.INVALID_REQUEST: 2,
    FailureKind.NOT_FOUND: 2,
    FailureKind.INVALID_CONFIGURATION: 2,
    FailureKind.PREREQUISITE_MISSING: 3,
    FailureKind.INDEX_NOT_READY: 4,
    FailureKind.BUSY: 5,
    FailureKind.REMOTE_FAILED: 5,
    FailureKind.OPERATION_FAILED: 5,
}


def stdout_reserved_for_result():
    return redirect_stdout(sys.stderr)


def json_output_requested(json_flag: bool) -> bool:
    return json_flag or not sys.stdout.isatty()


def write_json_success(command: str, data: dict) -> int:
    _write_json({"ok": True, "command": command, "data": data})
    return 0


def write_json_failure(command: str | None, failure: Failure) -> int:
    _write_failure_message(failure)
    payload = {"ok": False, "command": command, "error": failure.to_json()}
    if failure.data is not None:
        payload["data"] = failure.data
    _write_json(payload)
    return EXIT_CODE_BY_FAILURE_KIND[failure.kind]


def write_text_success(views: list[TextView]) -> int:
    style = TextStyle.for_stdout()
    lines = [line for view in views for line in view.lines(style)]
    if lines:
        print("\n".join(lines))
    return 0


def write_text_failure(failure: Failure) -> int:
    _write_failure_message(failure)
    return EXIT_CODE_BY_FAILURE_KIND[failure.kind]


def write_web_ui_opened(page_url: str, already_running: bool):
    address = page_url.split("#", 1)[0]
    if already_running:
        _write_line(f"Opened the Delphi Code web UI already running at {address}")
    else:
        _write_line(f"Delphi Code is open in your browser at {address}. Press Ctrl-C to stop it.")


def write_web_ui_address(page_url: str, already_running: bool):
    if already_running:
        _write_line(f"Delphi Code is already running at {page_url}")
    else:
        _write_line(f"Delphi Code is running at {page_url}\nPress Ctrl-C to stop it.")


def failure_of(exc: Exception) -> Failure:
    if os.environ.get("DELPHI_CODE_DEBUG") == "1":
        import traceback

        traceback.print_exc(file=sys.stderr)
    return Failure.from_exception(exc)


def _write_line(text: str):
    print(text, flush=True)


def _write_failure_message(failure: Failure):
    print(f"delphi-code: {failure}", file=sys.stderr)


def _write_json(payload: dict):
    print(
        json.dumps(
            {"schema_version": OUTPUT_SCHEMA_VERSION, **payload}, ensure_ascii=False, sort_keys=True, allow_nan=False
        )
    )
