import socket

import uvicorn

from ..services.application import DelphiCode
from .app import create_app
from .settings import LOOPBACK_HOST_NAMES, ApiSettings

LOOPBACK_ADDRESS = LOOPBACK_HOST_NAMES[0]


class LoopbackServer:
    def __init__(self, delphi_code: DelphiCode, settings: ApiSettings, port: int = 0):
        # Binding here, before uvicorn starts, tells the caller the port and keeps the server off other interfaces.
        self._listening = socket.create_server((LOOPBACK_ADDRESS, port))
        config = uvicorn.Config(create_app(delphi_code, settings), log_config=None, access_log=False, lifespan="off")
        self._server = uvicorn.Server(config)

    @property
    def url(self) -> str:
        port = self._listening.getsockname()[1]
        return f"http://{LOOPBACK_ADDRESS}:{port}"

    @property
    def started(self) -> bool:
        return self._server.started

    def run(self):
        try:
            self._server.run(sockets=[self._listening])
        finally:
            self._listening.close()

    def stop(self):
        self._server.should_exit = True
