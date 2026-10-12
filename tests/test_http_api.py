import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fakes import application, use_fake_model
from fastapi.testclient import TestClient

from delphi_code.domain.errors import Failure, FailureKind
from delphi_code.domain.indexing_outcomes import SyncReport
from delphi_code.http_api.app import create_app
from delphi_code.http_api.failures import HTTP_STATUS_BY_FAILURE_KIND
from delphi_code.http_api.progress_stream import NDJSON
from delphi_code.http_api.settings import ApiSettings
from delphi_code.infrastructure.registry import Entry, Registry
from delphi_code.services.application import DelphiCode

TOKEN = "http-api-test-token"
AUTHORIZED = {"Authorization": f"Bearer {TOKEN}"}


class HttpApi(unittest.TestCase):
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
        api = create_app(application(str(self.root / "model")), ApiSettings(TOKEN))
        self.client = TestClient(api, base_url="http://127.0.0.1")

    def test_every_request_needs_the_token(self):
        for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/projects", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "unauthorized")
        self.assertEqual(self.client.get("/api/projects", headers=AUTHORIZED).status_code, 200)

    def test_only_loopback_host_names_are_served(self):
        rebound = TestClient(self.client.app, base_url="http://attacker.example")
        self.assertEqual(rebound.get("/api/projects", headers=AUTHORIZED).status_code, 400)
        local = TestClient(self.client.app, base_url="http://localhost:8123")
        self.assertEqual(local.get("/api/projects", headers=AUTHORIZED).status_code, 200)

    def test_failures_map_to_http_statuses_with_their_code(self):
        missing = self.client.get(
            "/api/projects/status", params={"project": str(self.root / "gone")}, headers=AUTHORIZED
        )
        self.assertEqual((missing.status_code, missing.json()["error"]["code"]), (404, "project_missing"))
        not_indexed = self.client.get("/api/projects/status", params={"project": str(self.project)}, headers=AUTHORIZED)
        self.assertEqual((not_indexed.status_code, not_indexed.json()["error"]["code"]), (409, "index_missing"))
        self.assertEqual(set(HTTP_STATUS_BY_FAILURE_KIND), set(FailureKind))

    def test_invalid_parameters_are_usage_errors(self):
        for parameters in ({}, {"query": "q", "limit": 0}):
            with self.subTest(parameters=parameters):
                response = self.client.get("/api/search", params=parameters, headers=AUTHORIZED)
                self.assertEqual((response.status_code, response.json()["error"]["code"]), (400, "usage"))

    def test_openapi_describes_each_response(self):
        schemas = self.client.get("/openapi.json").json()["components"]["schemas"]
        for name in ("ProjectSearchHitsResponse", "CrossProjectSearchHitsResponse", "ProjectListingResponse"):
            with self.subTest(schema=name):
                self.assertIn(name, schemas)

    def test_no_page_loads_scripts_from_a_cdn(self):
        for path in ("/docs", "/redoc"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def stream_lines(self, response) -> list[dict]:
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith(NDJSON))
        return [json.loads(line) for line in response.text.splitlines()]

    def test_index_streams_progress_then_the_outcome(self):
        (self.project / "auth.py").write_text("def check_password(user, password):\n    return False\n")
        response = self.client.post("/api/projects/index", json={"project": str(self.project)}, headers=AUTHORIZED)
        lines = self.stream_lines(response)
        events = [line["event"] for line in lines[:-1]]
        self.assertEqual(events[0], "repository_started")
        self.assertIn("files_embedded", events)
        self.assertEqual(events[-1], "repository_finished")
        self.assertEqual(lines[-1]["done"]["files"], 1)

    def test_a_partly_failed_sync_is_a_done_report(self):
        with Registry().edit() as entries:
            entries[:] = [Entry(str(self.root / "gone")), Entry(str(self.project))]
        lines = self.stream_lines(self.client.post("/api/projects/sync", headers=AUTHORIZED))
        repos = lines[-1]["done"]["repos"]
        self.assertEqual(
            [(repo["ok"], repo.get("error", {}).get("code")) for repo in repos],
            [(False, "project_missing"), (True, None)],
        )

    def test_a_failure_after_progress_began_ends_the_stream(self):
        def fail_after_starting(self, project, selection, progress):
            progress.repository_started(project, 1, 1)
            raise Failure("index_busy", "Another command is updating this project", FailureKind.BUSY)

        with patch.object(DelphiCode, "index", fail_after_starting):
            response = self.client.post("/api/projects/index", json={"project": "p"}, headers=AUTHORIZED)
        self.assertEqual(
            self.stream_lines(response)[-1],
            {"failed": {"code": "index_busy", "message": "Another command is updating this project"}},
        )

    def test_one_write_at_a_time(self):
        started, release = threading.Event(), threading.Event()

        def slow_sync(self, progress):
            progress.repository_started("p", 1, 1)
            started.set()
            release.wait(10)
            return SyncReport("/repos.toml", [])

        with patch.object(DelphiCode, "sync", slow_sync):
            first = threading.Thread(
                target=self.client.post, args=("/api/projects/sync",), kwargs={"headers": AUTHORIZED}
            )
            first.start()
            started.wait(10)
            busy = self.client.post("/api/projects/sync", headers=AUTHORIZED)
            reading = self.client.get("/api/projects", headers=AUTHORIZED)
            release.set()
            first.join(10)
        self.assertEqual((busy.status_code, busy.json()["error"]["code"]), (409, "busy"))
        self.assertEqual(reading.status_code, 200)
        self.assertEqual(self.client.post("/api/projects/sync", headers=AUTHORIZED).status_code, 200)

    def test_changes_from_another_origin_are_refused(self):
        foreign = self.client.post("/api/projects/sync", headers={**AUTHORIZED, "Origin": "http://attacker.example"})
        self.assertEqual((foreign.status_code, foreign.json()["error"]["code"]), (403, "forbidden_origin"))
        own = self.client.post("/api/projects/sync", headers={**AUTHORIZED, "Origin": "http://127.0.0.1"})
        self.assertEqual(own.status_code, 200)


if __name__ == "__main__":
    unittest.main()
