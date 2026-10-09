from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Protocol

from ..domain.agent_connection import AgentConnection, Outcome

SERVER_NAME = "delphi-code"
SERVER_ARGUMENTS = ["mcp"]
PLUGIN_ID = "delphi-code@delphi-code"
PLUGIN_MARKETPLACE = "delphi-code"
PLUGIN_MARKETPLACE_SOURCE = "markdorof/delphi-code"
SKILL_FILE = Path(__file__).with_name("SKILL.md")
BACKUP_SUFFIX = ".delphi-code-backup"
AGENT_CLI_TIMEOUT_SECONDS = 180
NOT_ADDED_BY_CONNECT = "not added by delphi-code connect; remove it by hand if unwanted"


class AgentConfig(Protocol):
    name: str
    title: str

    @property
    def skills_directory(self) -> Path | None: ...

    def installed(self) -> bool: ...

    def connect(self, command: str) -> AgentConnection: ...

    def disconnect(self, command: str) -> AgentConnection: ...

    def configured(self) -> bool: ...


class JsonServersFile:
    def __init__(
        self,
        name: str,
        title: str,
        app_directory: Path | None,
        file_names: tuple[str, ...],
        servers_key: str,
        skills_directory: Path | None = None,
        server_entry: Callable[[str], dict] = lambda command: {"command": command, "args": SERVER_ARGUMENTS},
    ):
        self.name = name
        self.title = title
        self.skills_directory = skills_directory
        self._app_directory = app_directory
        self._file_names = file_names
        self._servers_key = servers_key
        self._server_entry = server_entry

    def installed(self) -> bool:
        return self._app_directory is not None and self._app_directory.is_dir()

    def connect(self, command: str) -> AgentConnection:
        loaded = self._load()
        if isinstance(loaded, AgentConnection):
            return loaded
        path, settings, servers = loaded
        if SERVER_NAME in servers:
            return self._result(Outcome.ALREADY_CONFIGURED, path)
        servers[SERVER_NAME] = self._server_entry(command)
        return self._save(path, settings, Outcome.ADDED)

    def disconnect(self, command: str) -> AgentConnection:
        loaded = self._load()
        if isinstance(loaded, AgentConnection):
            return loaded
        path, settings, servers = loaded
        entry = servers.get(SERVER_NAME)
        if entry is None:
            return self._result(Outcome.NOT_CONFIGURED, path)
        if not isinstance(entry, dict) or entry.get("command") != self._server_entry(command)["command"]:
            return self._result(Outcome.KEPT, path, NOT_ADDED_BY_CONNECT)
        del servers[SERVER_NAME]
        return self._save(path, settings, Outcome.REMOVED)

    def configured(self) -> bool:
        loaded = self._load()
        return not isinstance(loaded, AgentConnection) and SERVER_NAME in loaded[2]

    def _load(self) -> tuple[Path, dict, dict] | AgentConnection:
        if self._app_directory is None:
            return self._result(Outcome.NOT_FOUND)
        candidates = [self._app_directory / file_name for file_name in self._file_names]
        path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        try:
            settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return self._result(Outcome.FAILED, path, f"cannot read it as JSON ({exc}); edit it by hand")
        servers = settings.setdefault(self._servers_key, {}) if isinstance(settings, dict) else None
        if not isinstance(servers, dict):
            return self._result(Outcome.FAILED, path, f"expected a {self._servers_key!r} object; edit it by hand")
        return path, settings, servers

    def _save(self, path: Path, settings: dict, outcome: Outcome) -> AgentConnection:
        try:
            _write_keeping_a_backup(path, json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
        except OSError as exc:
            return self._result(Outcome.FAILED, path, f"cannot write it: {exc}")
        return self._result(outcome, path)

    def _result(self, outcome: Outcome, path: Path | None = None, detail: str | None = None) -> AgentConnection:
        return AgentConnection(self.name, self.title, outcome, str(path) if path else None, detail)


class _AgentCliFailure(Exception):
    pass


class CodexConfig:
    name = "codex"
    title = "Codex"
    plugin_config = f"plugin {PLUGIN_ID}"

    def __init__(self, codex_home: Path, skills_directory: Path):
        self._codex_home = codex_home
        self.skills_directory = skills_directory

    def installed(self) -> bool:
        return self._codex_home.is_dir()

    def connect(self, command: str) -> AgentConnection:
        loaded = self._load()
        if isinstance(loaded, AgentConnection):
            return loaded
        path, text, settings = loaded
        if PLUGIN_ID in settings.get("plugins", {}):
            return self._plugin_result(Outcome.ALREADY_CONFIGURED)
        if SERVER_NAME in settings.get("mcp_servers", {}):
            return self._result(
                Outcome.ALREADY_CONFIGURED,
                path,
                "as a standalone server; to switch to the plugin, run `delphi-code disconnect codex` "
                "and then `delphi-code connect codex`",
            )
        if shutil.which("codex") is None:
            return self._add_server_table(path, text, command)
        try:
            _run_agent_cli("codex", "plugin", "marketplace", "add", PLUGIN_MARKETPLACE_SOURCE, "--json")
            _run_agent_cli("codex", "plugin", "add", PLUGIN_ID, "--json")
        except _AgentCliFailure as exc:
            # Codex releases without `codex plugin add` still read a standalone server.
            return replace(self._add_server_table(path, text, command), detail=f"as a standalone server: {exc}")
        return self._plugin_result(Outcome.ADDED)

    def disconnect(self, command: str) -> AgentConnection:
        loaded = self._load()
        if isinstance(loaded, AgentConnection):
            return loaded
        path, text, settings = loaded
        if PLUGIN_ID in settings.get("plugins", {}):
            return self._remove_plugin()
        if SERVER_NAME not in settings.get("mcp_servers", {}):
            return self._result(Outcome.NOT_CONFIGURED, path)
        table = _codex_server_table(command)
        if table not in text:
            return self._result(Outcome.KEPT, path, NOT_ADDED_BY_CONNECT)
        remaining = text.replace(table, "", 1).rstrip("\n")
        return self._save(path, remaining + "\n" if remaining else "", Outcome.REMOVED)

    def configured(self) -> bool:
        loaded = self._load()
        if isinstance(loaded, AgentConnection):
            return False
        settings = loaded[2]
        return SERVER_NAME in settings.get("mcp_servers", {}) or PLUGIN_ID in settings.get("plugins", {})

    def _add_server_table(self, path: Path, text: str, command: str) -> AgentConnection:
        separator = "" if not text or text.endswith("\n\n") else "\n" if text.endswith("\n") else "\n\n"
        return self._save(path, text + separator + _codex_server_table(command), Outcome.ADDED)

    def _remove_plugin(self) -> AgentConnection:
        if shutil.which("codex") is None:
            return self._plugin_result(
                Outcome.FAILED, f"codex is not on PATH; run `codex plugin remove {PLUGIN_ID}` by hand"
            )
        try:
            _run_agent_cli("codex", "plugin", "remove", PLUGIN_ID, "--json")
            _run_agent_cli("codex", "plugin", "marketplace", "remove", PLUGIN_MARKETPLACE, "--json")
        except _AgentCliFailure as exc:
            return self._plugin_result(Outcome.FAILED, str(exc))
        return self._plugin_result(Outcome.REMOVED)

    def _load(self) -> tuple[Path, str, dict] | AgentConnection:
        path = self._codex_home / "config.toml"
        try:
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            return path, text, tomllib.loads(text)
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            return self._result(Outcome.FAILED, path, f"cannot read it as TOML ({exc}); edit it by hand")

    def _save(self, path: Path, text: str, outcome: Outcome) -> AgentConnection:
        try:
            _write_keeping_a_backup(path, text)
        except OSError as exc:
            return self._result(Outcome.FAILED, path, f"cannot write it: {exc}")
        return self._result(outcome, path)

    def _plugin_result(self, outcome: Outcome, detail: str | None = None) -> AgentConnection:
        return AgentConnection(self.name, self.title, outcome, self.plugin_config, detail, plugin_brings_the_skill=True)

    def _result(self, outcome: Outcome, path: Path, detail: str | None = None) -> AgentConnection:
        return AgentConnection(self.name, self.title, outcome, str(path), detail)


class ClaudeCodePlugin:
    name = "claude-code"
    title = "Claude Code"
    config = f"plugin {PLUGIN_ID}"
    # The plugin brings the skill.
    skills_directory = None

    def installed(self) -> bool:
        return shutil.which("claude") is not None

    def connect(self, command: str) -> AgentConnection:
        try:
            if self._installed_plugin_scope() is not None:
                return self._result(Outcome.ALREADY_CONFIGURED)
            if self._has_standalone_server():
                return self._result(
                    Outcome.ALREADY_CONFIGURED,
                    f"as a standalone server; to get the skill too, run `claude mcp remove {SERVER_NAME} -s user` "
                    "and then `delphi-code connect claude-code`",
                )
            self._claude("plugin", "marketplace", "add", PLUGIN_MARKETPLACE_SOURCE, "--json")
            self._claude("plugin", "install", PLUGIN_ID, "--scope", "user", "--json")
        except _AgentCliFailure as exc:
            return self._result(Outcome.FAILED, str(exc))
        return self._result(Outcome.ADDED)

    def disconnect(self, command: str) -> AgentConnection:
        try:
            scope = self._installed_plugin_scope()
            if scope is None:
                if self._has_standalone_server():
                    return self._result(Outcome.KEPT, f"standalone server {NOT_ADDED_BY_CONNECT}")
                return self._result(Outcome.NOT_CONFIGURED)
            self._claude("plugin", "uninstall", PLUGIN_ID, "--scope", scope, "--json")
            self._claude("plugin", "marketplace", "remove", PLUGIN_MARKETPLACE, "--json")
        except _AgentCliFailure as exc:
            return self._result(Outcome.FAILED, str(exc))
        return self._result(Outcome.REMOVED)

    def configured(self) -> bool:
        try:
            return self._installed_plugin_scope() is not None or self._has_standalone_server()
        except _AgentCliFailure:
            return False

    def _installed_plugin_scope(self) -> str | None:
        listing = self._claude("plugin", "list", "--json").stdout
        try:
            plugins = json.loads(listing)
        except json.JSONDecodeError as exc:
            raise _AgentCliFailure(f"claude plugin list printed unexpected output: {exc}") from exc
        scopes = [plugin.get("scope", "user") for plugin in plugins if plugin.get("id") == PLUGIN_ID]
        return scopes[0] if scopes else None

    def _has_standalone_server(self) -> bool:
        return self._claude("mcp", "get", SERVER_NAME, check=False).returncode == 0

    def _claude(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return _run_agent_cli("claude", *arguments, check=check)

    def _result(self, outcome: Outcome, detail: str | None = None) -> AgentConnection:
        return AgentConnection(self.name, self.title, outcome, self.config, detail)


def supported_agents() -> list[AgentConfig]:
    home = Path.home()
    return [
        JsonServersFile(
            "claude-desktop",
            "Claude Desktop",
            _macos_application_support("Claude"),
            ("claude_desktop_config.json",),
            "mcpServers",
        ),
        ClaudeCodePlugin(),
        CodexConfig(Path(os.environ.get("CODEX_HOME") or home / ".codex").expanduser(), home / ".agents/skills"),
        JsonServersFile("cursor", "Cursor", home / ".cursor", ("mcp.json",), "mcpServers", home / ".cursor/skills"),
        JsonServersFile(
            "vscode",
            "VS Code",
            _vscode_user_directory(),
            ("mcp.json",),
            "servers",
            server_entry=lambda command: {"type": "stdio", "command": command, "args": SERVER_ARGUMENTS},
        ),
        JsonServersFile(
            "gemini", "Gemini CLI", home / ".gemini", ("settings.json",), "mcpServers", home / ".gemini/skills"
        ),
        JsonServersFile(
            "opencode",
            "OpenCode",
            _xdg_config_home() / "opencode",
            ("opencode.json", "opencode.jsonc"),
            "mcp",
            home / ".agents/skills",
            server_entry=lambda command: {"type": "local", "command": [command, *SERVER_ARGUMENTS], "enabled": True},
        ),
    ]


def install_skill(skills_directory: Path) -> Path:
    skill_directory = skills_directory / SERVER_NAME
    skill_directory.mkdir(parents=True, exist_ok=True)
    (skill_directory / SKILL_FILE.name).write_text(SKILL_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    return skill_directory


def remove_skill(skills_directory: Path) -> Path | None:
    skill_directory = skills_directory / SERVER_NAME
    skill = skill_directory / SKILL_FILE.name
    if not skill.exists():
        return None
    skill.unlink()
    if not any(skill_directory.iterdir()):
        skill_directory.rmdir()
    return skill_directory


def _run_agent_cli(program: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        finished = subprocess.run(
            [program, *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=AGENT_CLI_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _AgentCliFailure(f"{program} {' '.join(arguments[:2])} failed: {exc}") from exc
    if check and finished.returncode != 0:
        message = (finished.stderr or finished.stdout).strip() or f"exit code {finished.returncode}"
        raise _AgentCliFailure(f"{program} {' '.join(arguments[:2])} failed: {message}")
    return finished


def _codex_server_table(command: str) -> str:
    # json.dumps quoting is valid TOML for basic strings and arrays of them.
    return f"[mcp_servers.{SERVER_NAME}]\ncommand = {json.dumps(command)}\nargs = {json.dumps(SERVER_ARGUMENTS)}\n"


def _macos_application_support(app: str) -> Path | None:
    return Path.home() / "Library/Application Support" / app if sys.platform == "darwin" else None


def _vscode_user_directory() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Code/User"
    return _xdg_config_home() / "Code/User"


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config").expanduser()


def _write_keeping_a_backup(path: Path, text: str):
    temporary = path.with_name(path.name + ".delphi-code-tmp")
    temporary.write_text(text, encoding="utf-8")
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + BACKUP_SUFFIX))
        # Agent configs can hold tokens, so the new file keeps the original's permissions.
        shutil.copymode(path, temporary)
    os.replace(temporary, path)
