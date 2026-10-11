from enum import StrEnum


class FailureKind(StrEnum):
    USAGE = "usage"
    RUNTIME_ASSETS = "runtime_assets"
    INDEX_STATE = "index_state"
    OPERATION = "operation"


class Failure(Exception):
    def __init__(self, code: str, message: str, kind: FailureKind, data: dict | None = None):
        super().__init__(message)
        self.code = code
        self.kind = kind
        self.data = data

    @classmethod
    def from_exception(cls, exc: BaseException) -> "Failure":
        if isinstance(exc, Failure):
            return exc
        if isinstance(exc, ModuleNotFoundError):
            return cls("dependency_missing", str(exc), FailureKind.RUNTIME_ASSETS)
        return cls("runtime_error", str(exc), FailureKind.OPERATION)

    def to_json(self) -> dict:
        return {"code": self.code, "message": str(self)}
