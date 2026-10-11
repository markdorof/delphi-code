import asyncio
from dataclasses import replace
import fcntl
import json
import logging
from pathlib import Path
import shutil
import tempfile

from ..domain.diagnostics import Diagnostics, ModelSetup
from ..domain.errors import Failure, FailureKind
from ..infrastructure.model_assets import download, verify_assets
from ..infrastructure.paths import index_root
from ..infrastructure.store import Store
from .agent_connections import connect_agents
from .progress import SILENT, Progress, Stage

logger = logging.getLogger(__name__)


def diagnose(model: Path) -> Diagnostics:
    from ..infrastructure.vector_index import check_storage
    from .diagnostics import diagnose as run_doctor

    root = index_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=root):
        pass
    with tempfile.TemporaryDirectory(prefix=".setup-probe-", dir=root.parent) as scratch:
        asyncio.run(check_storage(Path(scratch)))
    return run_doctor(str(model), Store(), str(Path.cwd()))


def set_up(
    model_location: str, import_from: str | None, progress: Progress, connect_agents_to: str | None = None
) -> ModelSetup:
    provisioned = provision(model_location, import_from, progress)
    if connect_agents_to is None:
        return provisioned
    return replace(provisioned, agents=connect_agents(connect_agents_to, [], progress).connections)


def provision(model_location: str, import_from: str | None = None, progress: Progress = SILENT) -> ModelSetup:
    destination = Path(model_location).expanduser().resolve()
    progress.model_setup_started(destination)
    source = Path(import_from).expanduser().resolve() if import_from else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (destination.parent / f".{destination.name}.setup.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Failure(
                "setup_busy", "Another setup is running for this model; retry when it finishes", FailureKind.BUSY
            ) from exc
        if destination.exists():
            logger.info("Verifying existing model at %s", destination)
            progress.stage_started(Stage.VERIFYING_MODEL)
            try:
                verify_assets(destination)
            except Failure as exc:
                raise Failure(
                    exc.code,
                    f"{exc}. Existing assets were preserved. Move {destination} aside, then rerun delphi-code setup",
                    FailureKind.PREREQUISITE_MISSING,
                ) from exc
            progress.stage_started(Stage.CHECKING_INSTALLATION)
            diagnostics = diagnose(destination)
            reused = True
        else:
            with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as temporary:
                staged = Path(temporary) / "model"
                if source:
                    logger.info("Importing model from %s to %s", source, destination)
                    progress.stage_started(Stage.COPYING_MODEL)
                    verify_assets(source)
                    shutil.copytree(source, staged, ignore=shutil.ignore_patterns(".*"))
                else:
                    logger.info("Downloading model to %s", destination)
                    progress.stage_started(Stage.DOWNLOADING_MODEL)
                    staged.mkdir()
                    download(staged)
                progress.stage_started(Stage.VERIFYING_MODEL)
                provenance = verify_assets(staged)
                (staged / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
                progress.stage_started(Stage.CHECKING_INSTALLATION)
                diagnostics = diagnose(staged)
                staged.rename(destination)
            diagnostics = replace(diagnostics, model=str(destination))
            reused = False
    progress.model_setup_finished(reused)
    return ModelSetup(str(destination), str(index_root()), reused, diagnostics)
