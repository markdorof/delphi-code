from ..infrastructure.store import Store
from ..services import searching
from ..services.searching import SearchRequest
from ..ui.text_layout import pluralized
from ..ui.views.project_names import project_display_name
from ..ui.views.search_hits import SearchHitsView
from .response import ControllerResponse


def search(project: str | None, request: SearchRequest, model: str) -> ControllerResponse:
    found = searching.search(Store(), project, request, model)
    if project is None:
        searched_scope = pluralized(len(found["projects"]), "index", "indexes")
    else:
        searched_scope = project_display_name(found["key"])
    view = SearchHitsView(request.query, searched_scope, found["results"], names_project_of_each_hit=project is None)
    return ControllerResponse(found, [view])
