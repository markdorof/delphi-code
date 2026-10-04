import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fakes import use_fake_model

from delphi_code.mcp_server import delphi_code_server

CLI_COMMANDS = ["add", "doctor", "index", "list", "remove", "search", "setup", "status", "sync"]


class McpServerTools(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "DELPHI_CODE_INDEX_ROOT": str(self.root / "indexes"),
                    "DELPHI_CODE_REGISTRY": str(self.root / "repos.toml"),
                },
            )
        )
        self.model = use_fake_model(self, self.root / "model")
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "auth.py").write_text("def check_password(user, password):\n    return False\n")

    def results_of(self, *calls):
        messages = [
            {"jsonrpc": "2.0", "id": number, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
            for number, (name, arguments) in enumerate(calls)
        ]
        outgoing = io.StringIO()
        delphi_code_server(str(self.root / "model")).answer_messages(
            io.StringIO("".join(json.dumps(message) + "\n" for message in messages)), outgoing
        )
        return [json.loads(line)["result"] for line in outgoing.getvalue().splitlines()]

    def test_offers_a_tool_for_every_cli_command(self):
        self.assertEqual(sorted(delphi_code_server("model").tools_by_name), CLI_COMMANDS)

    def test_indexes_then_searches_in_one_session(self):
        project = str(self.project)
        indexed, status, found = self.results_of(
            ("index", {"project": project}),
            ("status", {"project": project}),
            ("search", {"query": "where are passwords checked?", "project": project, "limit": 1}),
        )
        self.assertFalse(indexed["isError"], indexed["content"])
        self.assertTrue(status["structuredContent"]["ready"])
        self.assertEqual([hit["path"] for hit in found["structuredContent"]["results"]], ["auth.py"])

    def test_project_defaults_to_the_working_directory(self):
        with patch.object(Path, "cwd", return_value=self.project):
            (indexed,) = self.results_of(("index", {}))
        self.assertEqual(indexed["structuredContent"]["project"], str(self.project))

    def test_tracks_lists_and_removes_projects(self):
        added, listed, removed = self.results_of(
            ("add", {"sources": [str(self.project)], "no_sync": True}),
            ("list", {}),
            ("remove", {"name": str(self.project)}),
        )
        self.assertFalse(added["isError"], added["content"])
        self.assertEqual([repo["source"] for repo in listed["structuredContent"]["repos"]], [str(self.project)])
        self.assertTrue(removed["structuredContent"]["untracked"])

    def test_failures_carry_their_stable_code(self):
        missing, empty_query, picker = self.results_of(
            ("status", {"project": str(self.root / "missing")}),
            ("search", {"query": "  ", "project": str(self.project)}),
            ("add", {"sources": []}),
        )
        self.assertTrue(missing["isError"])
        self.assertTrue(missing["content"][0]["text"].startswith("project_missing: "))
        self.assertEqual(empty_query["content"][0]["text"], "usage: Query must be nonempty")
        self.assertEqual(picker["content"][0]["text"], "sources must have at least 1 item(s)")


if __name__ == "__main__":
    unittest.main()
