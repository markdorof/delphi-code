from collections.abc import Callable
import logging
import os
import secrets
import threading
import time
from urllib.request import Request, urlopen

from ..infrastructure.web_ui_server_record import WebUiServerRecord, WebUiServerRecordFile
from ..services.application import DelphiCode
from .security import BEARER_PREFIX
from .server import LoopbackServer
from .settings import ApiSettings

TOKEN_BYTES = 32
LIVENESS_CHECK_SECONDS = 2
STARTUP_POLL_SECONDS = 0.02
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
    showing_page = threading.Thread(target=_show_page_once_started, args=(server, page_ready, record), daemon=True)
    try:
        showing_page.start()
        server.run()
    finally:
        record_file.remove(record)


def _show_page_once_started(server: LoopbackServer, page_ready: Callable[[str, bool], None], record: WebUiServerRecord):
    while not server.started:
        time.sleep(STARTUP_POLL_SECONDS)
    page_ready(_page_url(record), False)


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
