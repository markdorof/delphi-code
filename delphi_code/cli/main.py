import argparse
from collections.abc import Callable
from importlib.metadata import version
import logging
from pathlib import Path
import shutil
import sys
import time
import webbrowser

from ..domain.errors import Failure, FailureKind
from ..domain.search_request import MAX_SEARCH_LIMIT, SearchRequest
from ..domain.selection import DEFAULT_MAX_BYTES, FileSelection
from ..infrastructure.log_file import write_logs_to_file
from ..services.application import DelphiCode
from .controllers import indexing, installation, project_catalog, searching
from .controllers.response import ControllerResponse
from .terminal import output
from .terminal.progress import TerminalProgress
from .terminal.prompts import TerminalPrompts

logger = logging.getLogger(__name__)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Failure("usage", message, FailureKind.INVALID_REQUEST)


def arguments() -> argparse.Namespace:
    parser = Parser(prog="delphi-code", description="Offline local code search")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('delphi-code')}")
    output_format_options = Parser(add_help=False)
    output_format_options.add_argument(
        "--json", action="store_true", help="Write JSON even on a terminal; JSON is the default when piped"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def add_command_parser(name, **options):
        return commands.add_parser(name, parents=[output_format_options], **options)

    for name, summary in (
        ("index", "Build or update a project's index"),
        ("search", "Search indexed code with a natural-language query"),
        ("status", "Show a project's stored index state"),
        ("doctor", "Check the model, SQLite extensions and native storage"),
    ):
        command = add_command_parser(name, help=summary)
        command.add_argument(
            "--project",
            "-p",
            default=None if name == "search" else str(Path.cwd()),
            help="Project path, key, or indexed name; search defaults to all indexes",
        )
        if name in {"index", "search"}:
            _add_selection_options(command, indexing=name == "index")
        if name == "search":
            command.add_argument("query")
            command.add_argument("--limit", type=_search_limit, default=10)
    add = add_command_parser("add", help="Track projects in the registry and index them")
    add.add_argument(
        "sources",
        nargs="*",
        metavar="SOURCE",
        help="Project directory, bitbucket.org/workspace/repository, or github.com/owner/repository; "
        "omit to pick repositories interactively",
    )
    add.add_argument("--ref", help="Branch or tag of remote repositories; defaults to the default branch")
    _add_selection_options(add, indexing=True)
    add.add_argument("--no-sync", action="store_true", help="Only update the registry")
    add_command_parser("sync", help="Index every tracked project")
    listing = add_command_parser("list", help="List tracked projects and stored indexes")
    listing.add_argument("--indexed", action="store_true", help="Only list projects that have an index")
    remove = add_command_parser("remove", help="Stop tracking a project and delete its index")
    remove.add_argument("name", help="Project path, key, or indexed name")
    remove.add_argument("--keep-index", action="store_true", help="Only untrack the project")
    setup = add_command_parser("setup", help="Download or import the pinned model and check the installation")
    setup.add_argument("--from", dest="source", help="Import a prepared MiniLM model without network access")
    setup.add_argument("--no-connect", action="store_true", help="Do not register the MCP server with agents")
    for name, summary in (
        ("connect", "Register the MCP server with installed agents"),
        ("disconnect", "Remove what connect registered, before uninstalling"),
    ):
        command = add_command_parser(name, help=summary)
        command.add_argument(
            "agents",
            nargs="*",
            metavar="AGENT",
            help="claude-desktop, claude-code, codex, cursor, vscode, gemini or opencode; omit for every installed agent",
        )
    commands.add_parser("mcp", help="Serve the other commands as MCP tools over stdio")
    web_ui = commands.add_parser("ui", help="Open the web UI, starting its local server unless one is running")
    web_ui.add_argument("--no-browser", action="store_true", help="Print the page's address instead of opening it")
    return parser.parse_args()


def execute(args: argparse.Namespace, progress: TerminalProgress | None = None) -> ControllerResponse:
    progress = progress or TerminalProgress.on_terminal()
    with progress:
        return COMMANDS[args.command](DelphiCode.from_environment(), args, progress)


def main():
    write_logs_to_file()
    started = time.monotonic()
    command, write_json = None, output.json_output_requested(json_flag="--json" in sys.argv[1:])
    progress = TerminalProgress.on_terminal()
    try:
        args = arguments()
        if args.command == "mcp":
            _serve_mcp()
            return
        if args.command == "ui":
            _serve_web_ui(open_browser=not args.no_browser)
            return
        command, write_json = args.command, output.json_output_requested(json_flag=args.json)
        logger.info("%s started in %s", command, Path.cwd())
        logger.debug("%s arguments: %s", command, vars(args))
        with output.stdout_reserved_for_result():
            response = execute(args, progress)
    except Exception as exc:
        failure = output.failure_of(exc)
        _log_failure(command, exc, failure, time.monotonic() - started)
        if write_json:
            raise SystemExit(output.write_json_failure(command, failure)) from None
        raise SystemExit(output.write_text_failure(failure)) from None
    logger.info("%s succeeded in %.2fs", command, time.monotonic() - started)
    if write_json:
        raise SystemExit(output.write_json_success(command, response.data))
    raise SystemExit(output.write_text_success(response.views))


COMMANDS: dict[str, Callable[[DelphiCode, argparse.Namespace, TerminalProgress], ControllerResponse]] = {
    "index": lambda app, args, progress: indexing.index(app, args.project, _selection(args), progress),
    "search": lambda app, args, progress: searching.search(
        app, args.project, SearchRequest(args.query, args.path, args.language, args.limit)
    ),
    "status": lambda app, args, progress: project_catalog.status(app, args.project),
    "doctor": lambda app, args, progress: installation.doctor(app, args.project),
    "add": lambda app, args, progress: indexing.add(
        app, args.sources, args.ref, _selection(args), not args.no_sync, progress, TerminalPrompts()
    ),
    "sync": lambda app, args, progress: indexing.sync(app, progress),
    "list": lambda app, args, progress: project_catalog.list_tracked(app, args.indexed),
    "remove": lambda app, args, progress: project_catalog.remove(app, args.name, args.keep_index),
    "setup": lambda app, args, progress: installation.setup(
        app, args.source, progress, None if args.no_connect else _delphi_code_command()
    ),
    "connect": lambda app, args, progress: installation.connect(app, _delphi_code_command(), args.agents, progress),
    "disconnect": lambda app, args, progress: installation.disconnect(app, _delphi_code_command(), args.agents),
}


def _serve_mcp():
    logger.info("mcp server started in %s", Path.cwd())
    from ..mcp_server import serve as serve_mcp

    serve_mcp()


def _serve_web_ui(open_browser: bool):
    logger.info("ui started in %s", Path.cwd())
    from ..http_api import serve as serve_web_ui

    def show_page(page_url: str, already_running: bool):
        if open_browser and webbrowser.open(page_url):
            output.write_web_ui_opened(page_url, already_running)
        else:
            output.write_web_ui_address(page_url, already_running)

    try:
        serve_web_ui(show_page)
    except KeyboardInterrupt:
        logger.info("ui stopped")


def _delphi_code_command() -> str:
    # Agents started from the Dock do not see the shell's PATH, so they need the full path.
    invoked = Path(sys.argv[0])
    if invoked.name == "delphi-code":
        return str(invoked.absolute())
    return shutil.which("delphi-code") or "delphi-code"


def _log_failure(command: str | None, exc: Exception, failure: Failure, seconds: float):
    message = "%s failed in %.2fs with %s: %s"
    if isinstance(exc, Failure):
        logger.warning(message, command, seconds, failure.code, failure, exc_info=exc.__cause__ is not None)
    else:
        logger.exception(message, command, seconds, failure.code, failure)


def _selection(args) -> FileSelection:
    return FileSelection(args.path, args.language, args.ignore, args.max_bytes)


def _add_selection_options(command, indexing):
    command.add_argument("--path", action="append", default=[], help="Project-relative glob; repeat for alternatives")
    command.add_argument("--language", action="append", default=[])
    if indexing:
        command.add_argument("--ignore", action="append", default=[])
        command.add_argument("--max-bytes", type=_positive_integer, default=DEFAULT_MAX_BYTES)


def _positive_integer(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def _search_limit(text):
    value = int(text)
    if not 1 <= value <= MAX_SEARCH_LIMIT:
        raise argparse.ArgumentTypeError(f"must be between 1 and {MAX_SEARCH_LIMIT}")
    return value
