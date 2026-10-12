from dataclasses import dataclass

LOOPBACK_HOST_NAMES = ("127.0.0.1", "localhost")


@dataclass(frozen=True)
class ApiSettings:
    token: str
    allowed_host_names: tuple[str, ...] = LOOPBACK_HOST_NAMES
