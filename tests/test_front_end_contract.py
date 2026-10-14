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
from delphi_code.http_api.progress_stream import NDJSON
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

    def http_response(self, method: str, path: str, arguments: dict):
        client = TestClient(
            create_app(application(str(self.root / "model")), ApiSettings(TOKEN)), base_url="http://127.0.0.1"
        )
        sent = {"json": arguments} if method == "POST" else {"params": arguments}
        return client.request(method, path, headers={"Authorization": f"Bearer {TOKEN}"}, **sent)

    def http_data(self, method: str, path: str, arguments: dict) -> dict:
        response = self.http_response(method, path, arguments)
        self.assertEqual(response.status_code, 200, response.text)
        if response.headers["content-type"].startswith(NDJSON):
            return json.loads(response.text.splitlines()[-1])["done"]
        return response.json()

    def test_successful_commands_return_the_same_data(self):
        project = str(self.project)
        query = "where are passwords checked?"
        commands = [
            (
                ["search", "-p", project, query],
                ("search", {"project": project, "query": query}),
                ("GET", "/api/search", {"project": project, "query": query}),
            ),
            (["search", query], ("search", {"query": query}), ("GET", "/api/search", {"query": query})),
            (
                ["status", "-p", project],
                ("status", {"project": project}),
                ("GET", "/api/projects/status", {"project": project}),
            ),
            (
                ["doctor", "-p", project],
                ("doctor", {"project": project}),
                ("GET", "/api/doctor", {"project": project}),
            ),
            (
                ["index", "-p", project],
                ("index", {"project": project}),
                ("POST", "/api/projects/index", {"project": project}),
            ),
            (
                ["add", project, "--no-sync"],
                ("add", {"sources": [project], "no_sync": True}),
                ("POST", "/api/projects", {"sources": [project], "no_sync": True}),
            ),
            (["sync"], ("sync", {}), ("POST", "/api/projects/sync", {})),
            (
                ["sync", project],
                ("sync", {"projects": [project]}),
                ("POST", "/api/projects/sync", {"projects": [project]}),
            ),
            (["add", project], ("add", {"sources": [project]}), ("POST", "/api/projects", {"sources": [project]})),
            (["list"], ("list", {}), ("GET", "/api/projects", {})),
            (["list", "--indexed"], ("list", {"indexed": True}), ("GET", "/api/projects", {"indexed": "true"})),
        ]
        for cli_arguments, mcp_call, http_call in commands:
            with self.subTest(command=" ".join(cli_arguments)):
                cli_data = self.cli_data(*cli_arguments)
                self.assertEqual(cli_data, self.mcp_data(*mcp_call))
                self.assertEqual(cli_data, self.http_data(*http_call))

    def test_failures_carry_the_same_code(self):
        missing, project = str(self.root / "missing"), str(self.project)
        failures = [
            (
                ["status", "-p", missing],
                ("status", {"project": missing}),
                ("GET", "/api/projects/status", {"project": missing}),
            ),
            (
                ["search", "-p", project, "  "],
                ("search", {"project": project, "query": "  "}),
                ("GET", "/api/search", {"project": project, "query": "  "}),
            ),
            (
                ["index", "-p", missing],
                ("index", {"project": missing}),
                ("POST", "/api/projects/index", {"project": missing}),
            ),
            (["remove", missing], ("remove", {"name": missing}), ("DELETE", "/api/projects", {"name": missing})),
        ]
        for cli_arguments, mcp_call, http_call in failures:
            with self.subTest(command=" ".join(cli_arguments)):
                cli_code = self.cli_failure_code(*cli_arguments)
                result = self.mcp_result(*mcp_call)
                self.assertTrue(result["isError"])
                self.assertEqual(result["content"][0]["text"].split(":")[0], cli_code)
                self.assertEqual(self.http_response(*http_call).json()["error"]["code"], cli_code)


if __name__ == "__main__":
    unittest.main()
