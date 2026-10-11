from ....domain.diagnostics import Diagnostics, ModelSetup
from ..text_layout import LabelledFields, TextStyle, home_abbreviated
from .project_names import project_display_name


class DiagnosticsView:
    def __init__(self, diagnostics: Diagnostics):
        self._diagnostics = diagnostics

    def lines(self, style: TextStyle) -> list[str]:
        return [
            f"{style.green('✓')} Installation works",
            *LabelledFields(diagnostic_fields(self._diagnostics)).lines(style),
        ]


class ModelSetupView:
    def __init__(self, setup: ModelSetup):
        self._setup = setup

    def lines(self, style: TextStyle) -> list[str]:
        setup = self._setup
        outcome = "Model already installed" if setup.reused else "Model installed"
        fields = LabelledFields(
            [("Indexes", home_abbreviated(setup.index_root)), *diagnostic_fields(setup.diagnostics)]
        )
        return [f"{style.green('✓')} {outcome} at {home_abbreviated(setup.model)}", *fields.lines(style)]


def diagnostic_fields(diagnostics: Diagnostics) -> list[tuple[str, str | None]]:
    return [
        ("Version", diagnostics.version),
        ("Project", project_display_name(diagnostics.key) if diagnostics.key else None),
        ("Index", home_abbreviated(diagnostics.index_directory) or "none yet"),
        ("Model", home_abbreviated(diagnostics.model)),
        ("Embedding", f"{diagnostics.dimensions} dimensions on {diagnostics.device}"),
        ("Storage", diagnostics.cocoindex_storage),
        ("Network guard", diagnostics.network_guard),
        ("SQLite", diagnostics.sqlite),
        ("Packages", ", ".join(f"{name} {version}" for name, version in diagnostics.dependencies.items())),
    ]
