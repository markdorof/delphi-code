from typing import Protocol


class ServiceResult(Protocol):
    def to_json(self) -> dict: ...
