import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fakes import application, use_fake_model
from fastapi.testclient import TestClient

from delphi_code.cli.main import arguments, execute
from delphi_code.domain.errors import Failure
from delphi_code.http_api.app import create_app
from delphi_code.http_api.settings import ApiSettings
from delphi_code.mcp_server.tools import delphi_code_server

TOKEN = "contract-test-token"


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

    def http_response(self, path: str, parameters: dict):
        client = TestClient(
            create_app(application(str(self.root / "model")), ApiSettings(TOKEN)), base_url="http://127.0.0.1"
        )
        return client.get(path, params=parameters, headers={"Authorization": f"Bearer {TOKEN}"})

    def http_data(self, path: str, parameters: dict) -> dict:
        response = self.http_response(path, parameters)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_successful_commands_return_the_same_data(self):
        project = str(self.project)
        query = "where are passwords checked?"
        commands = [
            (
                ["search", "-p", project, query],
                ("search", {"project": project, "query": query}),
                ("/api/search", {"project": project, "query": query}),
            ),
            (["search", query], ("search", {"query": query}), ("/api/search", {"query": query})),
            (
                ["status", "-p", project],
                ("status", {"project": project}),
                ("/api/projects/status", {"project": project}),
            ),
            (["doctor", "-p", project], ("doctor", {"project": project}), ("/api/doctor", {"project": project})),
            (["index", "-p", project], ("index", {"project": project}), None),
            (["add", project, "--no-sync"], ("add", {"sources": [project], "no_sync": True}), None),
            (["list"], ("list", {}), ("/api/projects", {})),
            (["list", "--indexed"], ("list", {"indexed": True}), ("/api/projects", {"indexed": "true"})),
        ]
        for cli_arguments, mcp_call, http_call in commands:
            with self.subTest(command=" ".join(cli_arguments)):
                cli_data = self.cli_data(*cli_arguments)
                self.assertEqual(cli_data, self.mcp_data(*mcp_call))
                if http_call:
                    self.assertEqual(cli_data, self.http_data(*http_call))

    def test_failures_carry_the_same_code(self):
        missing, project = str(self.root / "missing"), str(self.project)
        failures = [
            (
                ["status", "-p", missing],
                ("status", {"project": missing}),
                ("/api/projects/status", {"project": missing}),
            ),
            (
                ["search", "-p", project, "  "],
                ("search", {"project": project, "query": "  "}),
                ("/api/search", {"project": project, "query": "  "}),
            ),
            (["remove", missing], ("remove", {"name": missing}), None),
        ]
        for cli_arguments, mcp_call, http_call in failures:
            with self.subTest(command=" ".join(cli_arguments)):
                cli_code = self.cli_failure_code(*cli_arguments)
                result = self.mcp_result(*mcp_call)
                self.assertTrue(result["isError"])
                self.assertEqual(result["content"][0]["text"].split(":")[0], cli_code)
                if http_call:
                    self.assertEqual(self.http_response(*http_call).json()["error"]["code"], cli_code)


if __name__ == "__main__":
    unittest.main()
