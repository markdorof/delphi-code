import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from urllib.request import Request, urlopen

from delphi_code.infrastructure.web_ui_server_record import WebUiServerRecord, WebUiServerRecordFile

COMMAND_SECONDS = 60
RUNNING_AT = "running at "


class WebUiCommand(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        opened_pages = self.root / "opened-pages.txt"
        fake_browser = self.root / "fake-browser"
        fake_browser.write_text(f'#!/bin/sh\necho "$1" >> "{opened_pages}"\n')
        fake_browser.chmod(0o700)
        self.opened_pages = opened_pages
        self.environment = {
            **os.environ,
            "HOME": str(self.root / "home"),
            "XDG_DATA_HOME": str(self.root / "xdg"),
            "DELPHI_CODE_MODEL": str(self.root / "model"),
            "DELPHI_CODE_INDEX_ROOT": str(self.root / "indexes"),
            "DELPHI_CODE_REGISTRY": str(self.root / "repos.toml"),
            "DELPHI_CODE_LOG_FILE": str(self.root / "delphi-code.log"),
            "BROWSER": f"{fake_browser} %s",
        }
        self.record_file = WebUiServerRecordFile(self.record_path())

    def record_path(self) -> Path:
        data = self.root / ("home/Library/Application Support" if sys.platform == "darwin" else "xdg")
        return data / "delphi-code" / "web-ui-server.json"

    def ui(self, *options: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "delphi_code", "ui", *options],
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=COMMAND_SECONDS,
        )

    def start_server(self) -> tuple[subprocess.Popen, str]:
        server = subprocess.Popen(
            [sys.executable, "-m", "delphi_code", "ui", "--no-browser"],
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop, server)
        assert server.stdout is not None
        announced = server.stdout.readline()
        self.assertIn(RUNNING_AT, announced, server.stderr.read() if server.poll() is not None else announced)
        return server, announced.split(RUNNING_AT, 1)[1].strip()

    def stop(self, server: subprocess.Popen) -> tuple[int, str]:
        if server.poll() is None:
            server.send_signal(signal.SIGINT)
        try:
            _, errors = server.communicate(timeout=COMMAND_SECONDS)
        except subprocess.TimeoutExpired:
            server.kill()
            raise
        return server.returncode, errors

    def projects_status(self, page_url: str) -> int:
        address, token = page_url.split("/#token=")
        with urlopen(Request(f"{address}/api/projects", headers={"Authorization": f"Bearer {token}"})) as response:
            return response.status

    def test_serves_the_api_and_records_itself_for_the_owner_only(self):
        server, page_url = self.start_server()
        self.assertTrue(page_url.startswith("http://127.0.0.1:"))
        self.assertEqual(self.projects_status(page_url), 200)
        record = self.record_file.read()
        assert record is not None
        self.assertEqual((record.pid, f"{record.url}/#token={record.token}"), (server.pid, page_url))
        self.assertEqual(stat.S_IMODE(self.record_path().stat().st_mode), 0o600)

    def test_a_second_run_reuses_the_running_server(self):
        _, page_url = self.start_server()
        printed = self.ui("--no-browser")
        self.assertEqual(printed.returncode, 0, printed.stderr)
        self.assertEqual(printed.stdout.strip(), f"Delphi Code is already running at {page_url}")
        opened = self.ui()
        self.assertEqual(opened.returncode, 0, opened.stderr)
        self.assertNotIn("#token=", opened.stdout)
        self.assertEqual(self.opened_pages.read_text().splitlines(), [page_url])

    def test_ctrl_c_stops_quietly_and_forgets_the_server(self):
        server, _ = self.start_server()
        exit_code, errors = self.stop(server)
        self.assertEqual(exit_code, 0, errors)
        self.assertNotIn("Traceback", errors)
        self.assertFalse(self.record_path().exists())

    def test_a_record_left_by_a_dead_server_is_replaced(self):
        self.record_file.write(WebUiServerRecord(_pid_of_finished_process(), "http://127.0.0.1:9", "old"))
        server, page_url = self.start_server()
        self.assertNotIn("#token=old", page_url)
        record = self.record_file.read()
        assert record is not None
        self.assertEqual(record.pid, server.pid)


def _pid_of_finished_process() -> int:
    finished = subprocess.Popen(["true"])
    finished.wait()
    return finished.pid


if __name__ == "__main__":
    unittest.main()
