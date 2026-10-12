import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fakes import application, use_fake_model

from delphi_code.http_api.server import LoopbackServer
from delphi_code.http_api.settings import ApiSettings

TOKEN = "loopback-server-test-token"
STARTUP_SECONDS = 10


class LoopbackServerOverTcp(unittest.TestCase):
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
                },
            )
        )
        use_fake_model(self, self.root / "model")
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "auth.py").write_text("def check_password(user, password):\n    return False\n")
        self.server = LoopbackServer(application(str(self.root / "model")), ApiSettings(TOKEN))
        running = threading.Thread(target=self.server.run, daemon=True)
        running.start()
        self.addCleanup(running.join, STARTUP_SECONDS)
        self.addCleanup(self.server.stop)
        deadline = time.monotonic() + STARTUP_SECONDS
        while not self.server.started and time.monotonic() < deadline:
            time.sleep(0.01)

    def call(self, method: str, path: str, body: dict | None = None, token: str = TOKEN) -> tuple[int, str]:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            with urlopen(Request(self.server.url + path, data, headers, method=method), timeout=30) as response:
                return response.status, response.read().decode()
        except HTTPError as error:
            with error:
                return error.code, error.read().decode()

    def test_listens_only_on_the_loopback_address(self):
        self.assertTrue(self.server.url.startswith("http://127.0.0.1:"))
        self.assertNotEqual(self.server.url, "http://127.0.0.1:0")

    def test_indexes_and_searches_over_tcp(self):
        status, streamed = self.call("POST", "/api/projects/index", {"project": str(self.project)})
        self.assertEqual(status, 200, streamed)
        self.assertEqual(json.loads(streamed.splitlines()[-1])["done"]["files"], 1)
        status, found = self.call("GET", f"/api/search?query=passwords&project={self.project}")
        self.assertEqual(status, 200, found)
        self.assertEqual([hit["path"] for hit in json.loads(found)["results"]], ["auth.py"])

    def test_refuses_requests_without_the_token(self):
        status, body = self.call("GET", "/api/projects", token="wrong")
        self.assertEqual((status, json.loads(body)["error"]["code"]), (401, "unauthorized"))


if __name__ == "__main__":
    unittest.main()
