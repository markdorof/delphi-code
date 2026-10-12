from collections.abc import Callable
import logging
import os
import secrets
from urllib.request import Request, urlopen

from ..infrastructure.web_ui_server_record import WebUiServerRecord, WebUiServerRecordFile
from ..services.application import DelphiCode
from .security import BEARER_PREFIX
from .server import LoopbackServer
from .settings import ApiSettings

TOKEN_BYTES = 32
LIVENESS_CHECK_SECONDS = 2
logger = logging.getLogger(__name__)


def serve(page_ready: Callable[[str, bool], None]):
    record_file = WebUiServerRecordFile()
    running = record_file.read()
    if running is not None and _still_serving(running):
        logger.info("web ui already served at %s by process %d", running.url, running.pid)
        page_ready(_page_url(running), True)
        return
    settings = ApiSettings(secrets.token_urlsafe(TOKEN_BYTES))
    server = LoopbackServer(DelphiCode.from_environment(), settings)
    record = WebUiServerRecord(os.getpid(), server.url, settings.token)
    record_file.write(record)
    logger.info("web ui served at %s", server.url)
    try:
        page_ready(_page_url(record), False)
        server.run()
    finally:
        record_file.remove(record)


def _page_url(record: WebUiServerRecord) -> str:
    return f"{record.url}/#token={record.token}"


def _still_serving(record: WebUiServerRecord) -> bool:
    try:
        os.kill(record.pid, 0)
    except OSError:
        return False
    authorized = Request(f"{record.url}/api/projects", headers={"Authorization": BEARER_PREFIX + record.token})
    try:
        with urlopen(authorized, timeout=LIVENESS_CHECK_SECONDS) as response:
            return response.status == 200
    except OSError:
        return False
