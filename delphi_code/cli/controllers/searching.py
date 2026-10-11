from ...domain.search_hits import CrossProjectSearchHits
from ...domain.search_request import SearchRequest
from ...services.application import DelphiCode
from ..terminal.text_layout import pluralized
from ..terminal.views.project_names import project_display_name
from ..terminal.views.search_hits import SearchHitsView
from .response import ControllerResponse


def search(app: DelphiCode, project: str | None, request: SearchRequest) -> ControllerResponse:
    found = app.search(project, request)
    if isinstance(found, CrossProjectSearchHits):
        searched_scope = pluralized(len(found.projects), "index", "indexes")
    else:
        searched_scope = project_display_name(found.key)
    view = SearchHitsView(request.query, searched_scope, found.hits)
    return ControllerResponse(found.to_json(), [view])
