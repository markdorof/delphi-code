from dataclasses import dataclass


@dataclass(frozen=True)
class HostingService:
    domain: str
    name: str
    owner_noun: str
    suggested_owner: str | None = None


@dataclass(frozen=True)
class Owner:
    slug: str
    name: str


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
