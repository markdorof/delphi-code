import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from fakes import FakeModel, application

from delphi_code.domain.selection import FileSelection
from delphi_code.http_api.server import LoopbackServer
from delphi_code.http_api.settings import ApiSettings
from delphi_code.infrastructure.model import LocalModel

E2E_PORT = int(os.environ.get("DELPHI_CODE_E2E_PORT", "8765"))
E2E_TOKEN = os.environ.get("DELPHI_CODE_E2E_TOKEN", "e2e-token")
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
            delphi_code = application(str(root / "model"))
            delphi_code.index(str(_seeded_project(root / "seeded-project")), FileSelection())
            LoopbackServer(delphi_code, ApiSettings(E2E_TOKEN), port=E2E_PORT).run()


def _seeded_project(directory: Path) -> Path:
    directory.mkdir()
    for name, text in SEEDED_FILES.items():
        (directory / name).write_text(text)
    return directory


if __name__ == "__main__":
    main()
