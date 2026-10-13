import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from fakes import FakeHost, FakeModel, application

from delphi_code.domain.hosting_services import Owner, Repository
from delphi_code.domain.selection import FileSelection
from delphi_code.http_api.server import LoopbackServer
from delphi_code.http_api.settings import ApiSettings
from delphi_code.infrastructure.model import LocalModel

E2E_PORT = int(os.environ.get("DELPHI_CODE_E2E_PORT", "8765"))
E2E_TOKEN = os.environ.get("DELPHI_CODE_E2E_TOKEN", "e2e-token")
ADDABLE_PROJECT = os.environ.get("DELPHI_CODE_E2E_ADDABLE_PROJECT")
ADDABLE_FILES = {"retry.py": "def retry(call, attempts=3):\n    return call()\n"}
BITBUCKET_ACCOUNT = FakeHost(
    [Owner("acme", "Acme"), Owner("beta", "Beta")],
    [
        Repository("bitbucket.org", "acme", "api", "Public API", False),
        Repository("bitbucket.org", "acme", "web", "Website", True),
    ],
)
SEEDED_FILES = {
    "auth.py": (
        "def check_password(user, password):\n"
        f"    # {'A comment long enough to overflow a phone-width page. ' * 4}\n"
        "    return user.password == password\n"
    )
}


def main():
    with tempfile.TemporaryDirectory(prefix="delphi-code-e2e-") as temporary:
        root = Path(temporary)
        os.environ["DELPHI_CODE_INDEX_ROOT"] = str(root / "indexes")
        os.environ["DELPHI_CODE_REGISTRY"] = str(root / "repos.toml")
        with patch.object(LocalModel, "inspect", return_value=FakeModel(root / "model")):
            delphi_code = application(str(root / "model"), repository_hosts=[BITBUCKET_ACCOUNT])
            delphi_code.index(str(_project_with(root / "seeded-project", SEEDED_FILES)), FileSelection())
            if ADDABLE_PROJECT:
                shutil.rmtree(ADDABLE_PROJECT, ignore_errors=True)
                _project_with(Path(ADDABLE_PROJECT), ADDABLE_FILES)
            LoopbackServer(delphi_code, ApiSettings(E2E_TOKEN), port=E2E_PORT).run()


def _project_with(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir()
    for name, text in files.items():
        (directory / name).write_text(text)
    return directory


if __name__ == "__main__":
    main()
