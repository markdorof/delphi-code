import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from delphi_code.controllers.installation import connect, disconnect, setup
from delphi_code.domain.errors import Failure
from delphi_code.mcp_server import delphi_code_tools
from delphi_code.services.progress import SILENT
from delphi_code.ui.text_layout import TextStyle

COMMAND = "/opt/bin/delphi-code"
REPOSITORY = Path(__file__).resolve().parent.parent
PLUGIN_SKILL = REPOSITORY / "plugin/skills/delphi-code/SKILL.md"
PACKAGED_SKILL = REPOSITORY / "delphi_code/infrastructure/SKILL.md"
PROVISIONED = {"model": "/models/m", "index_root": "/indexes", "reused": True, "diagnostics": {}}
UNCOLORED = TextStyle(colors_enabled=False)
FAKE_CLAUDE = """#!/bin/sh
echo "$@" >> "$FAKE_CLAUDE_LOG"
case "$1 $2" in
  "plugin list")
    if [ -e "$FAKE_CLAUDE_PLUGIN" ]; then echo '[{"id": "delphi-code@delphi-code", "scope": "user"}]'; else echo '[]'; fi ;;
  "plugin install") touch "$FAKE_CLAUDE_PLUGIN" ;;
  "plugin uninstall") rm "$FAKE_CLAUDE_PLUGIN" ;;
  "mcp get") [ -e "$FAKE_CLAUDE_STANDALONE" ] || exit 1 ;;
esac
"""


class ConnectAgents(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.claude_log = self.home / "claude.log"
        environment = patch.dict(
            os.environ,
            {
                "HOME": str(self.home),
                "PATH": f"{self.bin}:/bin:/usr/bin",
                "FAKE_CLAUDE_LOG": str(self.claude_log),
                "FAKE_CLAUDE_PLUGIN": str(self.home / "claude-plugin-installed"),
                "FAKE_CLAUDE_STANDALONE": str(self.home / "claude-standalone-server"),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        for variable in ("CODEX_HOME", "XDG_CONFIG_HOME"):
            os.environ.pop(variable, None)

    def outcomes(self, agents=(), change=connect):
        return {
            connection["agent"]: connection["outcome"] for connection in change(COMMAND, list(agents)).data["agents"]
        }

    def install_fake_claude(self):
        claude = self.bin / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)

    def test_finds_no_agents_in_an_empty_home(self):
        response = connect(COMMAND, [])
        self.assertEqual(response.data["agents"], [])
        self.assertEqual(response.views[0].lines(UNCOLORED)[0], "No supported agents found.")

    def test_adds_the_server_to_a_json_config_and_keeps_its_other_settings(self):
        cursor = self.home / ".cursor"
        cursor.mkdir()
        config = cursor / "mcp.json"
        config.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}))
        config.chmod(0o600)
        self.assertEqual(self.outcomes(), {"cursor": "added"})
        settings = json.loads(config.read_text())
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["mcpServers"]["other"], {"command": "x"})
        self.assertEqual(settings["mcpServers"]["delphi-code"], {"command": COMMAND, "args": ["mcp"]})
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
        self.assertTrue((cursor / "mcp.json.delphi-code-backup").exists())

    def test_creates_a_missing_config_with_the_agent_specific_shape(self):
        (self.home / ".gemini").mkdir()
        vscode_user = (
            self.home / "Library/Application Support/Code/User"
            if sys.platform == "darwin"
            else self.home / ".config/Code/User"
        )
        vscode_user.mkdir(parents=True)
        self.assertEqual(self.outcomes(), {"gemini": "added", "vscode": "added"})
        self.assertEqual(
            json.loads((vscode_user / "mcp.json").read_text())["servers"]["delphi-code"],
            {"type": "stdio", "command": COMMAND, "args": ["mcp"]},
        )
        self.assertIn("delphi-code", json.loads((self.home / ".gemini/settings.json").read_text())["mcpServers"])

    def test_never_overwrites_an_existing_entry_and_reports_unreadable_configs(self):
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor/mcp.json").write_text(json.dumps({"mcpServers": {"delphi-code": {"command": "mine"}}}))
        (self.home / ".gemini").mkdir()
        (self.home / ".gemini/settings.json").write_text("{ // comments are not JSON\n}")
        self.assertEqual(self.outcomes(), {"cursor": "already_configured", "gemini": "failed"})
        self.assertIn('"mine"', (self.home / ".cursor/mcp.json").read_text())
        self.assertEqual((self.home / ".gemini/settings.json").read_text(), "{ // comments are not JSON\n}")

    def test_appends_a_table_to_the_codex_config_once(self):
        codex = self.home / ".codex"
        codex.mkdir()
        (codex / "config.toml").write_text('model = "o4"\n\n[mcp_servers.other]\ncommand = "x"\n')
        self.assertEqual(self.outcomes(), {"codex": "added"})
        self.assertEqual(self.outcomes(), {"codex": "already_configured"})
        settings = tomllib.loads((codex / "config.toml").read_text())
        self.assertEqual(settings["model"], "o4")
        self.assertEqual(settings["mcp_servers"]["delphi-code"], {"command": COMMAND, "args": ["mcp"]})

    @unittest.skipUnless(sys.platform == "darwin", "Claude Desktop is macOS-only")
    def test_adds_the_server_to_claude_desktop(self):
        (self.home / "Library/Application Support/Claude").mkdir(parents=True)
        self.assertEqual(self.outcomes(), {"claude-desktop": "added"})

    def test_installs_the_claude_code_plugin_once(self):
        self.install_fake_claude()
        self.assertEqual(self.outcomes(), {"claude-code": "added"})
        self.assertEqual(self.outcomes(), {"claude-code": "already_configured"})
        self.assertEqual(
            self.claude_log.read_text().splitlines(),
            [
                "plugin list --json",
                "mcp get delphi-code",
                "plugin marketplace add markdorof/delphi-code --json",
                "plugin install delphi-code@delphi-code --scope user --json",
                "plugin list --json",
            ],
        )

    def test_leaves_a_standalone_claude_code_server_alone_instead_of_adding_a_duplicate(self):
        self.install_fake_claude()
        (self.home / "claude-standalone-server").touch()
        (connection,) = connect(COMMAND, []).data["agents"]
        self.assertEqual(connection["outcome"], "already_configured")
        self.assertIn("claude mcp remove delphi-code", connection["detail"])
        self.assertEqual(self.outcomes(change=disconnect), {"claude-code": "kept"})
        self.assertNotIn("plugin install", self.claude_log.read_text())
        self.assertNotIn("plugin uninstall", self.claude_log.read_text())

    def test_disconnect_removes_only_what_connect_added(self):
        self.install_fake_claude()
        for directory in (".cursor", ".gemini", ".codex"):
            (self.home / directory).mkdir()
        (self.home / ".gemini/settings.json").write_text(
            json.dumps({"mcpServers": {"delphi-code": {"command": "mine"}}})
        )
        codex_config = self.home / ".codex/config.toml"
        codex_config.write_text('model = "o4"\n')
        self.outcomes()
        self.assertEqual(
            self.outcomes(change=disconnect),
            {"claude-code": "removed", "codex": "removed", "cursor": "removed", "gemini": "kept"},
        )
        self.assertEqual(json.loads((self.home / ".cursor/mcp.json").read_text()), {"mcpServers": {}})
        self.assertEqual(codex_config.read_text(), 'model = "o4"\n')
        self.assertIn('"mine"', (self.home / ".gemini/settings.json").read_text())
        self.assertIn("plugin marketplace remove delphi-code --json", self.claude_log.read_text())
        self.assertEqual(
            self.outcomes(change=disconnect),
            {"claude-code": "not_configured", "codex": "not_configured", "cursor": "not_configured", "gemini": "kept"},
        )

    def test_codex_counts_its_delphi_code_plugin_as_configured(self):
        (self.home / ".codex").mkdir()
        (self.home / ".codex/config.toml").write_text('[plugins."delphi-code@delphi-code"]\nenabled = true\n')
        self.assertEqual(self.outcomes(), {"codex": "already_configured"})
        self.assertFalse((self.home / ".agents/skills/delphi-code").exists())

    def test_the_packaged_skill_matches_the_plugin_skill(self):
        self.assertEqual(PACKAGED_SKILL.read_text(), PLUGIN_SKILL.read_text())

    def test_installs_and_refreshes_the_skill_where_each_agent_reads_skills(self):
        for directory in (".codex", ".cursor", ".gemini"):
            (self.home / directory).mkdir()
        stale = self.home / ".cursor/skills/delphi-code/SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("an older skill")
        connections = connect(COMMAND, []).data["agents"]
        skills = {
            "codex": self.home / ".agents/skills/delphi-code",
            "cursor": self.home / ".cursor/skills/delphi-code",
            "gemini": self.home / ".gemini/skills/delphi-code",
        }
        self.assertEqual({c["agent"]: c["skill"] for c in connections}, {a: str(d) for a, d in skills.items()})
        for directory in skills.values():
            self.assertEqual((directory / "SKILL.md").read_text(), PLUGIN_SKILL.read_text())
        self.assertIn("skill in ~/.agents/skills/delphi-code", connect(COMMAND, ["codex"]).views[0].lines(UNCOLORED)[0])

        disconnected = disconnect(COMMAND, []).data["agents"]
        self.assertEqual({c["agent"]: c["skill"] for c in disconnected}, {a: str(d) for a, d in skills.items()})
        self.assertFalse(any(directory.exists() for directory in skills.values()))
        self.assertTrue((self.home / ".cursor/skills").is_dir())

    def test_adds_opencode_with_its_command_list_and_prefers_an_existing_jsonc_config(self):
        opencode = self.home / ".config/opencode"
        opencode.mkdir(parents=True)
        self.assertEqual(self.outcomes(), {"opencode": "added"})
        self.assertEqual(
            json.loads((opencode / "opencode.json").read_text())["mcp"]["delphi-code"],
            {"type": "local", "command": [COMMAND, "mcp"], "enabled": True},
        )
        self.assertEqual(self.outcomes(change=disconnect), {"opencode": "removed"})
        (opencode / "opencode.json").unlink()
        (opencode / "opencode.jsonc").write_text('{"$schema": "https://opencode.ai/config.json"}')
        self.assertEqual(self.outcomes(), {"opencode": "added"})
        self.assertIn("delphi-code", json.loads((opencode / "opencode.jsonc").read_text())["mcp"])
        self.assertFalse((opencode / "opencode.json").exists())

    def test_keeps_the_skill_codex_and_opencode_share_until_both_are_disconnected(self):
        (self.home / ".codex").mkdir()
        (self.home / ".config/opencode").mkdir(parents=True)
        shared_skill = self.home / ".agents/skills/delphi-code/SKILL.md"
        self.outcomes()
        self.assertTrue(shared_skill.exists())
        (codex,) = disconnect(COMMAND, ["codex"]).data["agents"]
        self.assertEqual((codex["outcome"], codex["skill"]), ("removed", None))
        self.assertTrue(shared_skill.exists())
        disconnect(COMMAND, ["opencode"])
        self.assertFalse(shared_skill.exists())

    def test_agents_without_a_skills_folder_get_only_the_server(self):
        (self.home / "Library/Application Support/Code/User").mkdir(parents=True)
        (self.home / ".config/Code/User").mkdir(parents=True)
        (connection,) = connect(COMMAND, ["vscode"]).data["agents"]
        self.assertEqual((connection["outcome"], connection["skill"]), ("added", None))

    def test_setup_connects_agents_unless_asked_not_to(self):
        (self.home / ".cursor").mkdir()
        with patch("delphi_code.services.model_installation.provision", return_value=dict(PROVISIONED)):
            skipped = setup("/models/m", None, SILENT, connect_agents_to=None)
            self.assertNotIn("agents", skipped.data)
            self.assertFalse((self.home / ".cursor/mcp.json").exists())
            connected = setup("/models/m", None, SILENT, connect_agents_to=COMMAND)
        self.assertEqual([agent["outcome"] for agent in connected.data["agents"]], ["added"])
        self.assertEqual(len(connected.views), 2)

    def test_the_setup_mcp_tool_never_edits_agent_configs(self):
        (self.home / ".cursor").mkdir()
        (setup_tool,) = [tool for tool in delphi_code_tools("/models/m") if tool.name == "setup"]
        with patch("delphi_code.services.model_installation.provision", return_value=dict(PROVISIONED)):
            self.assertNotIn("agents", setup_tool.run({}))
        self.assertFalse((self.home / ".cursor/mcp.json").exists())

    def test_named_agents_that_are_missing_are_reported_and_unknown_names_fail(self):
        self.assertEqual(self.outcomes(["cursor"]), {"cursor": "not_found"})
        with self.assertRaises(Failure) as raised:
            connect(COMMAND, ["emacs"])
        self.assertEqual(raised.exception.code, "usage")


if __name__ == "__main__":
    unittest.main()
