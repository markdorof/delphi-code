from dataclasses import dataclass
from pathlib import Path

LOOPBACK_HOST_NAMES = ("127.0.0.1", "localhost")
BUILT_WEB_UI_DIRECTORY = Path(__file__).parent.parent / "web"


@dataclass(frozen=True)
class ApiSettings:
    token: str
    allowed_host_names: tuple[str, ...] = LOOPBACK_HOST_NAMES
    web_ui_directory: Path = BUILT_WEB_UI_DIRECTORY
