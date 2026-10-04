from collections.abc import Callable
from importlib.metadata import version
import json
from pathlib import Path
from typing import Any

from .controllers import indexing, installation, project_catalog, searching
from .controllers.response import ControllerResponse
from .domain.errors import Failure
from .domain.selection import DEFAULT_MAX_BYTES, FileSelection
from .infrastructure.mcp_stdio_server import McpStdioServer, McpTool, McpToolFailure
from .services.progress import SILENT
from .services.searching import MAX_SEARCH_LIMIT, SearchRequest
from .ui.prompts import TerminalPrompts

SERVER_INSTRUCTIONS = (
    "Offline semantic code search over locally indexed projects. Use search to find code by what it does "
    "when you don't know the identifier or file to grep for, then read the files it points to. "
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


def serve(model: str):
    delphi_code_server(model).serve_stdio()


def delphi_code_server(model: str) -> McpStdioServer:
    return McpStdioServer("delphi-code", version("delphi-code"), SERVER_INSTRUCTIONS, delphi_code_tools(model))


def delphi_code_tools(model: str) -> list[McpTool]:
    project = _string_property(
        "Project path, indexed key (github.com/acme/api) or indexed folder name (api); "
        "defaults to the server's working directory"
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
            "Search indexed code with a natural-language question such as 'where are passwords checked?'. "
            "Results are best match first; path is relative to the project and start_line/end_line locate the "
            "passage. A higher score is a closer match; compare scores with each other, not with a fixed threshold.",
            {
                "query": _string_property("Describe the behaviour you are looking for, not a single keyword"),
                "project": _string_property("Project path, indexed key or folder name; omit to search every index"),
                "path": _string_list_property("Only results whose path matches one of these globs, such as src/*"),
                "language": _string_list_property("Only results in these languages"),
                "limit": _integer_property(
                    "Maximum number of results; default 10", minimum=1, maximum=MAX_SEARCH_LIMIT
                ),
            },
            lambda arguments: searching.search(arguments.get("project"), _search_request(arguments), model),
            READ_ONLY,
            required=["query"],
        ),
        _tool(
            "index",
            "Build or incrementally update a local project's index. Updates after edits are fast; the first index "
            "of a large project can take minutes.",
            {"project": project, **indexing_selection},
            lambda arguments: indexing.index(
                _project_or_working_directory(arguments), _file_selection(arguments), model, SILENT
            ),
            UPDATES_LOCAL_INDEXES,
        ),
        _tool(
            "status",
            "Report whether a project is indexed, and when and at which commit.",
            {"project": project},
            lambda arguments: project_catalog.status(_project_or_working_directory(arguments)),
            READ_ONLY,
        ),
        _tool(
            "doctor",
            "Check the model, SQLite extensions and storage with a real embedding.",
            {"project": project},
            lambda arguments: installation.doctor(_project_or_working_directory(arguments), model),
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
            lambda arguments: indexing.add(
                arguments["sources"],
                arguments.get("ref"),
                _file_selection(arguments),
                model,
                not arguments.get("no_sync", False),
                SILENT,
                TerminalPrompts(),
            ),
            USES_THE_NETWORK,
            required=["sources"],
        ),
        _tool(
            "sync",
            "Index every tracked project; remote repositories are fetched, which needs the network.",
            {},
            lambda arguments: indexing.sync(model, SILENT),
            USES_THE_NETWORK,
        ),
        _tool(
            "list",
            "List tracked projects and stored indexes.",
            {"indexed": _boolean_property("Only list projects that have an index")},
            lambda arguments: project_catalog.list_tracked(arguments.get("indexed", False)),
            READ_ONLY,
        ),
        _tool(
            "remove",
            "Stop tracking a project and delete its index.",
            {
                "name": _string_property("Project path, key, or indexed name"),
                "keep_index": _boolean_property("Only untrack the project and keep its index"),
            },
            lambda arguments: project_catalog.remove(arguments["name"], arguments.get("keep_index", False)),
            DELETES_AN_INDEX,
            required=["name"],
        ),
        _tool(
            "setup",
            "Download the pinned embedding model, or import it with from, and check the installation.",
            {"from": _string_property("Prepared model directory to import without network access")},
            lambda arguments: installation.setup(model, arguments.get("from"), SILENT),
            USES_THE_NETWORK,
        ),
    ]


def _tool(
    name: str,
    description: str,
    properties: dict[str, dict],
    call_controller: Callable[[dict[str, Any]], ControllerResponse],
    annotations: dict[str, bool],
    required: list[str] | None = None,
) -> McpTool:
    def controller_data(arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            return call_controller(arguments).data
        except Exception as exc:
            raise McpToolFailure(_failure_text(Failure.from_exception(exc))) from exc

    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }
    return McpTool(name, description, input_schema, controller_data, annotations)


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
