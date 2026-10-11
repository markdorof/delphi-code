from ....domain.errors import Failure
from ....domain.indexing_outcomes import FileChanges, IndexingOutcome, ProjectUpToDate, SyncedProject
from ..text_layout import LabelledFields, TextStyle, home_abbreviated, pluralized
from .project_names import project_directory_unless_named_by_it, project_display_name


class IndexingOutcomeView:
    def __init__(self, outcome: IndexingOutcome, shows_headline: bool):
        self._outcome = outcome
        self._shows_headline = shows_headline

    def lines(self, style: TextStyle) -> list[str]:
        outcome = self._outcome
        fields = LabelledFields(
            [
                ("Changes", file_change_summary(outcome.changes) or "none"),
                ("Project", project_directory_unless_named_by_it(outcome.key, outcome.project)),
                ("Ref", outcome.revision.ref),
                ("Commit", outcome.revision.commit),
                ("Skipped", pluralized(outcome.skipped, "file") if outcome.skipped else None),
                ("Index", home_abbreviated(outcome.index_directory)),
            ]
        )
        headline = [indexing_outcome_line(outcome, style)] if self._shows_headline else []
        return headline + fields.lines(style)


class IndexingOutcomesSummaryView:
    def __init__(self, projects: list[SyncedProject], lists_each_outcome: bool):
        self._projects = projects
        self._lists_each_outcome = lists_each_outcome

    def lines(self, style: TextStyle) -> list[str]:
        listed = [self._outcome_line(project, style) for project in self._projects] if self._lists_each_outcome else []
        return [*listed, *([""] if listed else []), style.dim(self._totals_line())]

    def _outcome_line(self, project: SyncedProject, style: TextStyle) -> str:
        if isinstance(project.result, Failure):
            return f"{style.red('✗')} {style.bold(project.source)}: {project.result}"
        return indexing_outcome_line(project.result, style)

    def _totals_line(self) -> str:
        results = [project.result for project in self._projects]
        failed_count = sum(isinstance(result, Failure) for result in results)
        unchanged_count = sum(isinstance(result, ProjectUpToDate) for result in results)
        counts_by_result = [
            (len(results) - failed_count - unchanged_count, "indexed"),
            (unchanged_count, "up to date"),
            (failed_count, "failed"),
        ]
        totals = ", ".join(f"{count} {result}" for count, result in counts_by_result if count)
        return f"{pluralized(len(results), 'project')}: {totals}"


def indexing_outcome_line(result: IndexingOutcome | ProjectUpToDate, style: TextStyle) -> str:
    name = style.bold(project_display_name(result.key))
    if isinstance(result, ProjectUpToDate):
        return f"{style.green('✓')} {name} is up to date"
    sizes = f"{pluralized(result.counts.files, 'file')}, {pluralized(result.counts.chunks, 'chunk')}"
    changes = file_change_summary(result.changes)
    return f"{style.green('✓')} Indexed {name}: {sizes}" + (f" ({changes})" if changes else "")


def file_change_summary(changes: FileChanges | None) -> str:
    if changes is None:
        return ""
    counts_by_change = [
        (changes.num_adds, "added"),
        (changes.num_reprocesses, "updated"),
        (changes.num_deletes, "removed"),
        (changes.num_unchanged, "unchanged"),
        (changes.num_errors, "failed"),
    ]
    return ", ".join(f"{count} {change}" for count, change in counts_by_change if count)
