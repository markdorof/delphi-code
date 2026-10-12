import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fakes import application, use_fake_model

from delphi_code.cli.main import arguments, execute
from delphi_code.domain.errors import Failure
from delphi_code.mcp_server.tools import delphi_code_server


class SameDataFromEveryFrontEnd(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "DELPHI_CODE_INDEX_ROOT": str(self.root / "indexes"),
                    "DELPHI_CODE_REGISTRY": str(self.root / "repos.toml"),
                    "DELPHI_CODE_MODEL": str(self.root / "model"),
                },
            )
        )
        use_fake_model(self, self.root / "model")
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "auth.py").write_text("def check_password(user, password):\n    return False\n")
        self.cli_data("index", "-p", str(self.project))

    def cli_data(self, *args) -> dict:
        with patch.object(sys, "argv", ["delphi-code", *args]):
            return execute(arguments()).data

    def cli_failure_code(self, *args) -> str:
        with self.assertRaises(Failure) as raised:
            self.cli_data(*args)
        return raised.exception.code

    def mcp_result(self, tool: str, tool_arguments: dict) -> dict:
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": tool_arguments},
        }
        replies = io.StringIO()
        delphi_code_server(application(str(self.root / "model"))).answer_messages(
            io.StringIO(json.dumps(message) + "\n"), replies
        )
        return json.loads(replies.getvalue())["result"]

    def mcp_data(self, tool: str, tool_arguments: dict) -> dict:
        result = self.mcp_result(tool, tool_arguments)
        self.assertFalse(result["isError"], result["content"])
        return result["structuredContent"]

    def test_successful_commands_return_the_same_data(self):
        project = str(self.project)
        query = "where are passwords checked?"
        commands = [
            (["search", "-p", project, query], "search", {"project": project, "query": query}),
            (["search", query], "search", {"query": query}),
            (["status", "-p", project], "status", {"project": project}),
            (["index", "-p", project], "index", {"project": project}),
            (["add", project, "--no-sync"], "add", {"sources": [project], "no_sync": True}),
            (["list"], "list", {}),
            (["list", "--indexed"], "list", {"indexed": True}),
        ]
        for cli_arguments, tool, tool_arguments in commands:
            with self.subTest(command=" ".join(cli_arguments)):
                self.assertEqual(self.cli_data(*cli_arguments), self.mcp_data(tool, tool_arguments))

    def test_failures_carry_the_same_code(self):
        missing = str(self.root / "missing")
        failures = [
            (["status", "-p", missing], "status", {"project": missing}),
            (["search", "-p", str(self.project), "  "], "search", {"project": str(self.project), "query": "  "}),
            (["remove", missing], "remove", {"name": missing}),
        ]
        for cli_arguments, tool, tool_arguments in failures:
            with self.subTest(command=" ".join(cli_arguments)):
                result = self.mcp_result(tool, tool_arguments)
                self.assertTrue(result["isError"])
                mcp_code = result["content"][0]["text"].split(":")[0]
                self.assertEqual(self.cli_failure_code(*cli_arguments), mcp_code)


if __name__ == "__main__":
    unittest.main()
