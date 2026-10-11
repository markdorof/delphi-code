from ....domain.search_hits import SearchHit
from ..text_layout import TextStyle, excerpt_lines
from .project_names import project_display_name

EXCERPT_LINE_LIMIT = 6
EXCERPT_INDENT = "    "


class SearchHitsView:
    def __init__(self, query: str, searched_scope: str, hits: list[SearchHit]):
        self._query = query
        self._searched_scope = searched_scope
        self._hits = hits

    def lines(self, style: TextStyle) -> list[str]:
        lines = [style.bold(self._heading()) + style.dim(f" in {self._searched_scope}")]
        for hit in self._hits:
            lines.append("")
            lines.extend(self._hit_lines(hit, style))
        return lines

    def _heading(self) -> str:
        count = len(self._hits)
        return f'{count or "No"} {"match" if count == 1 else "matches"} for "{self._query}"'

    def _hit_lines(self, hit: SearchHit, style: TextStyle) -> list[str]:
        location = f"{hit.path}:{hit.start_line}-{hit.end_line}"
        lines = [f"{style.cyan(location)}  {style.dim(hit.language)}  score {hit.score:.2f}"]
        if hit.url is not None:
            lines.append(f"  {style.dim(hit.url)}")
        elif hit.found_in is not None:
            lines.append(f"  {style.dim(project_display_name(hit.found_in.key))}")
        return lines + excerpt_lines(hit.text, EXCERPT_LINE_LIMIT, EXCERPT_INDENT, style)
