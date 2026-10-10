from collections.abc import Iterator
from contextlib import contextmanager
import os
import socket
import sys
import threading

DISABLED_ONLINE_FEATURES = (
    "COCOINDEX_DISABLE_USAGE_TRACKING",
    "HF_HUB_OFFLINE",
    "TRANSFORMERS_OFFLINE",
    "HF_DATASETS_OFFLINE",
    "HF_HUB_DISABLE_TELEMETRY",
    "DO_NOT_TRACK",
    "HF_HUB_DISABLE_PROGRESS_BARS",
)
NAME_RESOLUTION_EVENTS = {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}
SOCKET_TRAFFIC_EVENTS = {"socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto"}
INTERNET_ADDRESS_FAMILIES = {socket.AF_INET, socket.AF_INET6}


def disable_library_online_features():
    for name in DISABLED_ONLINE_FEATURES:
        os.environ[name] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["COCOINDEX_MAX_INFLIGHT_COMPONENTS"] = "1"


@contextmanager
def without_network() -> Iterator[None]:
    _NETWORK_DENIAL.enter()
    try:
        yield
    finally:
        _NETWORK_DENIAL.leave()


class _ProcessNetworkDenial:
    # Process-wide rather than per thread, because libraries may reach the network from their own threads.
    def __init__(self):
        self._lock = threading.Lock()
        self._active = 0
        self._hook_installed = False

    def enter(self):
        with self._lock:
            if not self._hook_installed:
                sys.addaudithook(self._deny_internet_access)
                self._hook_installed = True
            self._active += 1

    def leave(self):
        with self._lock:
            self._active -= 1

    def _deny_internet_access(self, event, args):
        if not self._active:
            return
        if event in NAME_RESOLUTION_EVENTS:
            raise RuntimeError("Offline policy blocked a DNS lookup")
        if event in SOCKET_TRAFFIC_EVENTS and getattr(args[0], "family", None) in INTERNET_ADDRESS_FAMILIES:
            raise RuntimeError("Offline policy blocked an Internet socket operation")


_NETWORK_DENIAL = _ProcessNetworkDenial()
