from __future__ import annotations

from functools import cached_property
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from ..domain.errors import ExitCode, Failure

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

SUPPORTED_MODULES = {
    "sentence_transformers.models.Transformer",
    "sentence_transformers.models.Pooling",
    "sentence_transformers.models.Normalize",
    "sentence_transformers.models.Dense",
}
MODULES_WITHOUT_DIRECTORY = {"sentence_transformers.models.Normalize"}
DOCUMENTATION_ASSETS = {"README.md", "LICENSE", "provenance.json"}
HASH_BLOCK_BYTES = 1024 * 1024


def is_incidental_asset(relative: Path) -> bool:
    is_os_or_downloader_metadata = any(part.startswith(".") for part in relative.parts)
    return relative.name in DOCUMENTATION_ASSETS or is_os_or_downloader_metadata


class LocalModel:
    def __init__(self, directory: Path, sha256: str):
        self.directory = directory
        self.sha256 = sha256

    @classmethod
    def inspect(cls, location: str | Path | None) -> LocalModel:
        if not location:
            raise _model_failure("model_missing", "Set DELPHI_CODE_MODEL to a local model directory")
        directory = Path(location).expanduser().resolve()
        file_stats = _asset_file_stats(directory)
        reusable = _models_inspected_in_this_process.get(directory)
        if reusable and reusable.file_stats == file_stats:
            return reusable.model
        _validate_layout(directory)
        model = cls(directory, _asset_digest(directory))
        _models_inspected_in_this_process[directory] = _InspectedModel(file_stats, model)
        return model

    @property
    def dimensions(self) -> int:
        dimensions = self._encoder.get_embedding_dimension()
        if dimensions is None:
            raise _model_failure("model_invalid", f"Model at {self.directory} does not declare its embedding dimension")
        return dimensions

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        import numpy as np

        vectors = self._encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)
        vectors = np.asarray(vectors, dtype=np.float32)
        if not np.isfinite(vectors).all() or (np.linalg.norm(vectors, axis=-1) == 0).any():
            raise _model_failure("embedding_invalid", "Model produced invalid or zero embeddings")
        return vectors

    @cached_property
    def _encoder(self):
        from sentence_transformers import SentenceTransformer

        try:
            return SentenceTransformer(
                str(self.directory),
                device="cpu",
                local_files_only=True,
                trust_remote_code=False,
                model_kwargs={"use_safetensors": True, "local_files_only": True},
            )
        except Exception as exc:
            raise _model_failure("model_invalid", f"Cannot load local model assets at {self.directory}: {exc}") from exc


class _InspectedModel(NamedTuple):
    file_stats: tuple[tuple[str, int, int], ...]
    model: LocalModel


# A long-running MCP server opens the model for every tool call; hashing and loading it each time takes seconds.
_models_inspected_in_this_process: dict[Path, _InspectedModel] = {}


def _asset_file_stats(directory: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (path.relative_to(directory).as_posix(), stat.st_size, stat.st_mtime_ns)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
        for stat in [path.stat()]
    )


def _validate_layout(directory: Path):
    if not directory.is_dir() or not (directory / "modules.json").is_file():
        raise _model_failure(
            "model_missing",
            f"Local SentenceTransformers assets missing: {directory}. Run delphi-code setup, "
            "or set DELPHI_CODE_MODEL to prepared assets; downloads are never automatic.",
        )
    modules = json.loads((directory / "modules.json").read_text())
    if not isinstance(modules, list) or not modules:
        raise _model_failure("model_invalid", "modules.json must contain a nonempty module list")
    for module in modules:
        if module.get("type") not in SUPPORTED_MODULES:
            raise _model_failure("model_invalid", f"Unsupported model module: {module.get('type')}")
        folder = (directory / module.get("path", "")).resolve()
        if not folder.is_relative_to(directory) or (
            not folder.is_dir() and module["type"] not in MODULES_WITHOUT_DIRECTORY
        ):
            raise _model_failure("model_missing", "A model module directory is missing or outside the model")
    if not any(directory.rglob("*.safetensors")):
        raise _model_failure(
            "model_missing", "Model requires local safetensors weights; pickle weights are unsupported"
        )


def _asset_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if is_incidental_asset(relative) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode() + b"\0")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(HASH_BLOCK_BYTES), b""):
                digest.update(block)
    return digest.hexdigest()


def _model_failure(code: str, message: str) -> Failure:
    return Failure(code, message, ExitCode.RUNTIME_ASSETS)
