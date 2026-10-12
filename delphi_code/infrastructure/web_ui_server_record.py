from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path

from .paths import web_ui_server_record_path

OWNER_ONLY = 0o600


@dataclass(frozen=True)
class WebUiServerRecord:
    pid: int
    url: str
    token: str


class WebUiServerRecordFile:
    def __init__(self, path: Path | None = None):
        self._path = path or web_ui_server_record_path()

    def read(self) -> WebUiServerRecord | None:
        try:
            fields = json.loads(self._path.read_text())
            return WebUiServerRecord(int(fields["pid"]), str(fields["url"]), str(fields["token"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def write(self, record: WebUiServerRecord):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        temporary.unlink(missing_ok=True)
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, OWNER_ONLY), "w") as written:
            json.dump(asdict(record), written)
        os.replace(temporary, self._path)

    def remove(self, record: WebUiServerRecord):
        if self.read() == record:
            self._path.unlink(missing_ok=True)
