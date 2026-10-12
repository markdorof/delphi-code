import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fakes import application, use_fake_model
from fastapi.testclient import TestClient

from delphi_code.domain.errors import FailureKind
from delphi_code.http_api.app import create_app
from delphi_code.http_api.failures import HTTP_STATUS_BY_FAILURE_KIND
from delphi_code.http_api.settings import ApiSettings

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


if __name__ == "__main__":
    unittest.main()
