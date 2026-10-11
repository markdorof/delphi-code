from pathlib import Path
from unittest.mock import patch

import numpy as np

from delphi_code.domain.diagnostics import Diagnostics
from delphi_code.domain.index_state import IndexCounts
from delphi_code.domain.indexing_outcomes import IndexingOutcome
from delphi_code.domain.manifest import IndexedRevision
from delphi_code.infrastructure.model import LocalModel


class FakeModel:
    def __init__(self, directory: Path, sha256: str = "same-model", vector=(1, 0)):
        self.directory = directory
        self.sha256 = sha256
        self.vector = vector
        self.embedded: list[list[str]] = []

    @property
    def dimensions(self):
        return len(self.vector)

    def embed(self, texts):
        self.embedded.append(texts)
        return np.array([self.vector] * len(texts), dtype=np.float32)


def use_fake_model(test_case, directory: Path, **options) -> FakeModel:
    model = FakeModel(directory, **options)
    test_case.enterContext(patch.object(LocalModel, "inspect", return_value=model))
    return model


def indexing_outcome(key: str, index_directory: str, project: str | None = None, **revision) -> IndexingOutcome:
    return IndexingOutcome(project, key, index_directory, IndexedRevision(**revision), IndexCounts(0, 0), 0, None)


def diagnostics(model: str = "/models/m") -> Diagnostics:
    return Diagnostics(
        version="0.0.0",
        project=None,
        key="local:/work",
        index_directory=None,
        model=model,
        model_sha256="same-model",
        dimensions=2,
        self_distance=0.0,
        device="cpu",
        cocoindex_storage="ok",
        offline=True,
        network_guard="python_audit",
        sqlite="3",
        dependencies={},
    )
