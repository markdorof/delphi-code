from .errors import Failure, FailureKind

MAX_SEARCH_LIMIT = 1000


class SearchRequest:
    def __init__(self, query: str, paths: list[str], languages: list[str], limit: int):
        if not query.strip():
            raise Failure("usage", "Query must be nonempty", FailureKind.INVALID_REQUEST)
        self.query = query
        self.paths = paths
        self.languages = languages
        self.limit = limit
