from ....domain.index_state import IndexState
from ..text_layout import LabelledFields, TextStyle, home_abbreviated, pluralized, relative_time
from .project_names import project_directory_unless_named_by_it, project_display_name


class IndexStateView:
    def __init__(self, state: IndexState):
        self._state = state

    def lines(self, style: TextStyle) -> list[str]:
        state, manifest = self._state, self._state.manifest
        readiness = style.green("ready") if manifest.ready else style.yellow("incomplete; run index again")
        counts = state.counts
        sizes = f"{pluralized(counts.files, 'file')}, {pluralized(counts.chunks, 'chunk')}" if counts else None
        project = str(manifest.project) if manifest.project else None
        selection = manifest.selection
        fields = LabelledFields(
            [
                ("State", readiness),
                ("Indexed", relative_time(manifest.indexed_at)),
                ("Contents", sizes),
                ("Project", project_directory_unless_named_by_it(state.key, project)),
                ("Ref", manifest.revision.ref),
                ("Commit", manifest.revision.commit),
                ("Paths", ", ".join(selection.paths)),
                ("Languages", ", ".join(selection.languages)),
                ("Ignored", ", ".join(selection.ignores)),
                ("Model", home_abbreviated(manifest.model_directory)),
                ("Index", home_abbreviated(state.index_directory)),
            ]
        )
        return [style.bold(project_display_name(state.key)), *fields.lines(style)]
