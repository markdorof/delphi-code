from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class HostingService:
    domain: str
    name: str
    owner_noun: str
    suggested_owner: str | None = None

    def to_json(self) -> dict:
        return {
            "domain": self.domain,
            "name": self.name,
            "owner_noun": self.owner_noun,
            "suggested_owner": self.suggested_owner,
        }


@dataclass(frozen=True)
class Owner:
    slug: str
    name: str

    def to_json(self) -> dict:
        return {"slug": self.slug, "name": self.name}


@dataclass(frozen=True)
class Repository:
    host: str
    owner: str
    slug: str
    description: str
    private: bool

    @property
    def key(self) -> str:
        return f"{self.host}/{self.owner}/{self.slug}".lower()

    def to_json(self) -> dict:
        return {
            "key": self.key,
            "host": self.host,
            "owner": self.owner,
            "slug": self.slug,
            "description": self.description,
            "private": self.private,
        }


class ConnectionState(StrEnum):
    CONNECTED = "connected"
    FAILED = "failed"
    NOT_CONNECTED = "not_connected"


@dataclass(frozen=True)
class AccountConnection:
    service: HostingService
    how_to_connect: str
    credentials_source: str | None = None
    account: str | None = None
    problem: str | None = None

    @property
    def state(self) -> ConnectionState:
        if self.credentials_source is None:
            return ConnectionState.NOT_CONNECTED
        return ConnectionState.FAILED if self.problem else ConnectionState.CONNECTED

    def to_json(self) -> dict:
        return {
            "domain": self.service.domain,
            "name": self.service.name,
            "state": self.state,
            "account": self.account,
            "credentials_source": self.credentials_source,
            "problem": self.problem,
            "how_to_connect": self.how_to_connect,
        }
