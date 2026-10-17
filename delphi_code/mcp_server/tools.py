from collections.abc import Callable
from importlib.metadata import version
import json
from pathlib import Path
from typing import Any

from ..domain.errors import Failure
from ..domain.indexing_outcomes import SyncReport
from ..domain.search_request import MAX_SEARCH_LIMIT, SearchRequest
from ..domain.selection import DEFAULT_MAX_BYTES, FileSelection
from ..domain.service_result import ServiceResult
from ..domain.tracking_report import TrackingReport
from ..services.application import DelphiCode
from .stdio_protocol import McpStdioServer, McpTool, McpToolFailure

SERVER_INSTRUCTIONS = (
    "Offline semantic code search across the user's indexed repositories, local and remote. When you look for "
    "code by what it does, or code that may live in another repository, call search first, then read the files "
    "it points to; for a remote repository, search again to see more of it. "
    "Use grep instead for exact names and strings. Tools mirror the delphi-code CLI commands and options."
)
READ_ONLY = {"readOnlyHint": True, "openWorldHint": False}
UPDATES_LOCAL_INDEXES = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
USES_THE_NETWORK = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}
DELETES_AN_INDEX = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}


def serve():
    delphi_code_server(DelphiCode.from_environment()).serve_stdio()


def delphi_code_server(app: DelphiCode) -> McpStdioServer:
    return McpStdioServer("delphi-code", version("delphi-code"), SERVER_INSTRUCTIONS, delphi_code_tools(app))


def delphi_code_tools(app: DelphiCode) -> list[McpTool]:
    project = _string_property(
        "Absolute path of the project root, or an indexed key (github.com/acme/api) or folder name (api). "
        "Pass it explicitly: the default is the server's working directory, which may not be your project"
    )
    indexing_selection = {
        "path": _string_list_property("Only index paths matching these project-relative globs, such as src/*"),
        "language": _string_list_property("Only index these languages, such as python or typescript"),
        "ignore": _string_list_property("Extra gitignore-style patterns to skip"),
        "max_bytes": _integer_property(f"Skip files larger than this; default {DEFAULT_MAX_BYTES}", minimum=1),
    }
    return [
        _tool(
            "search",
            "Find code by what it does. Call this before grepping or reading files whenever you look for where a "
            "behaviour or concept is implemented and don't know the exact identifier, file or string, such as "
            "'where are passwords checked?' or 'how are failed requests retried?', and when the answer may be in "
            "another indexed repository. Use grep only for exact names and strings you already know. Results are "
            "best match first; path is relative to the project and start_line/end_line locate the passage, so read "
            "around it. A higher score is a closer match; compare scores with each other, not with a fixed "
            "threshold. If the project is not indexed yet, call index first.",
            {
                "query": _string_property("Describe the behaviour you are looking for, not a single keyword"),
                "project": _string_property("Project path, indexed key or folder name; omit to search every index"),
                "path": _string_list_property("Only results whose path matches one of these globs, such as src/*"),
                "language": _string_list_property("Only results in these languages"),
                "limit": _integer_property(
                    "Maximum number of results; default 10", minimum=1, maximum=MAX_SEARCH_LIMIT
                ),
            },
            lambda arguments: app.search(arguments.get("project"), _search_request(arguments)),
            READ_ONLY,
            required=["query"],
        ),
        _tool(
            "index",
            "Build or incrementally update a local project's index. Updates after edits are fast; the first index "
            "of a large project can take minutes.",
            {"project": project, **indexing_selection},
            lambda arguments: app.index(_project_or_working_directory(arguments), _file_selection(arguments)),
            UPDATES_LOCAL_INDEXES,
        ),
        _tool(
            "status",
            "Report whether a project is indexed, and when and at which commit.",
            {"project": project},
            lambda arguments: app.status(_project_or_working_directory(arguments)),
            READ_ONLY,
        ),
        _tool(
            "doctor",
            "Check the model, SQLite extensions and storage with a real embedding.",
            {"project": project},
            lambda arguments: app.diagnose(_project_or_working_directory(arguments)),
            READ_ONLY,
        ),
        _tool(
            "add",
            "Track projects or remote repositories and index them. Remote repositories are cloned and indexed now, "
            "which needs the network and can take minutes.",
            {
                "sources": _string_list_property(
                    "Project directories, bitbucket.org/workspace/repository or github.com/owner/repository",
                    min_items=1,
                ),
                "ref": _string_property("Branch or tag of remote repositories; defaults to the default branch"),
                "no_sync": _boolean_property("Only update the registry; index later with sync"),
                **indexing_selection,
            },
            lambda arguments: _unless_any_project_failed(
                app.add(
                    arguments["sources"],
                    arguments.get("ref"),
                    _file_selection(arguments),
                    not arguments.get("no_sync", False),
                )
            ),
            USES_THE_NETWORK,
            required=["sources"],
        ),
        _tool(
            "sync",
            "Index tracked projects; remote repositories fetch their new commits, which needs the network.",
            {"projects": _string_list_property("Tracked project paths, keys or names; omit to sync every one")},
            lambda arguments: _unless_any_project_failed(app.sync(arguments.get("projects", []))),
            USES_THE_NETWORK,
        ),
        _tool(
            "list",
            "List tracked projects and stored indexes.",
            {"indexed": _boolean_property("Only list projects that have an index")},
            lambda arguments: app.list_projects(arguments.get("indexed", False)),
            READ_ONLY,
        ),
        _tool(
            "remove",
            "Stop tracking a project and delete its index.",
            {
                "name": _string_property("Project path, key, or indexed name"),
                "keep_index": _boolean_property("Only untrack the project and keep its index"),
            },
            lambda arguments: app.remove(arguments["name"], arguments.get("keep_index", False)),
            DELETES_AN_INDEX,
            required=["name"],
        ),
        _tool(
            "setup",
            "Download the pinned embedding model, or import it with from, and check the installation.",
            {"from": _string_property("Prepared model directory to import without network access")},
            lambda arguments: app.set_up(arguments.get("from")),
            USES_THE_NETWORK,
        ),
    ]


def _tool(
    name: str,
    description: str,
    properties: dict[str, dict],
    call_service: Callable[[dict[str, Any]], ServiceResult],
    annotations: dict[str, bool],
    required: list[str] | None = None,
) -> McpTool:
    def service_data(arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            return call_service(arguments).to_json()
        except Exception as exc:
            raise McpToolFailure(_failure_text(Failure.from_exception(exc))) from exc

    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }
    return McpTool(name, description, input_schema, service_data, annotations)


def _unless_any_project_failed[Report: SyncReport | TrackingReport](report: Report) -> Report:
    if failure := report.failure_if_any_failed():
        raise failure
    return report


def _failure_text(failure: Failure) -> str:
    text = f"{failure.code}: {failure}"
    if failure.data is not None:
        text += "\n" + json.dumps(failure.data, ensure_ascii=False, sort_keys=True)
    return text


def _search_request(arguments: dict[str, Any]) -> SearchRequest:
    return SearchRequest(
        arguments["query"], arguments.get("path", []), arguments.get("language", []), arguments.get("limit", 10)
    )


def _project_or_working_directory(arguments: dict[str, Any]) -> str:
    return arguments.get("project") or str(Path.cwd())


def _file_selection(arguments: dict[str, Any]) -> FileSelection:
    return FileSelection(
        arguments.get("path", []),
        arguments.get("language", []),
        arguments.get("ignore", []),
        arguments.get("max_bytes", DEFAULT_MAX_BYTES),
    )


def _string_property(description: str) -> dict:
    return {"type": "string", "description": description}


def _string_list_property(description: str, min_items: int = 0) -> dict:
    schema: dict = {"type": "array", "items": {"type": "string"}, "description": description}
    if min_items:
        schema["minItems"] = min_items
    return schema


def _integer_property(description: str, minimum: int, maximum: int | None = None) -> dict:
    schema: dict = {"type": "integer", "minimum": minimum, "description": description}
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _boolean_property(description: str) -> dict:
    return {"type": "boolean", "description": description}
