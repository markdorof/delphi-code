from enum import StrEnum


class FailureKind(StrEnum):
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    INVALID_CONFIGURATION = "invalid_configuration"
    PREREQUISITE_MISSING = "prerequisite_missing"
    INDEX_NOT_READY = "index_not_ready"
    BUSY = "busy"
    REMOTE_FAILED = "remote_failed"
    OPERATION_FAILED = "operation_failed"


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
            return cls("dependency_missing", str(exc), FailureKind.PREREQUISITE_MISSING)
        return cls("runtime_error", str(exc), FailureKind.OPERATION_FAILED)

    def to_json(self) -> dict:
        return {"code": self.code, "message": str(self)}
