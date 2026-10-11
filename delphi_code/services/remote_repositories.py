from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..domain.errors import Failure, FailureKind
from ..domain.selection import FileSelection
from ..domain.tracking_changes import TrackingChanges
from ..infrastructure.registry import Registry
from ..infrastructure.store import Store
from .progress import Progress
from .tracking import apply_tracking_changes

if TYPE_CHECKING:
    from ..infrastructure.hosts import Owner, Repository, RepositoryHost


def hosts_with_credentials() -> Sequence[RepositoryHost]:
    from ..infrastructure.hosts import configured_hosts

    hosts = configured_hosts()
    if not hosts:
        raise Failure(
            "remote_auth_missing",
            "Picking repositories needs Bitbucket or GitHub credentials: set BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD or GITHUB_TOKEN, sign in with gh auth login, or store git credentials for bitbucket.org or github.com",
            FailureKind.RUNTIME_ASSETS,
        )
    return hosts


def tracked_keys(registry: Registry) -> set[str]:
    return {entry.current_key() for entry in registry.entries()}


def owners_if_listable(host: RepositoryHost, progress: Progress) -> list[Owner] | None:
    progress.owners_listing_started(host.name, host.owner_noun)
    try:
        owners = host.owners()
    except Failure as failure:
        if failure.code != "remote_permission_denied":
            raise
        return None
    finally:
        progress.listing_finished()
    if not owners:
        raise Failure("remote_empty", f"Your {host.name} account has no repositories", FailureKind.USAGE)
    return owners


def repositories_of_owner(host: RepositoryHost, owner: str, progress: Progress) -> list[Repository]:
    progress.repositories_listing_started(host.name, owner)
    try:
        repositories = host.repositories(owner)
    finally:
        progress.listing_finished()
    if not repositories:
        raise Failure(
            "remote_empty", f"You have no repositories in the {host.name} {host.owner_noun} {owner}", FailureKind.USAGE
        )
    return repositories


def apply_picked_changes(
    store: Store,
    registry: Registry,
    changes: TrackingChanges | None,
    ref: str | None,
    selection: FileSelection,
    model_location: str,
    sync_now: bool,
    progress: Progress,
) -> dict:
    if changes is None:
        return {"registry": str(registry.path), "cancelled": True, "repos": [], "removed": []}
    try:
        applied = apply_tracking_changes(store, registry, changes, ref, selection, model_location, sync_now, progress)
    except Failure as failure:
        failure.data = {**(failure.data or {}), "cancelled": False}
        raise
    return {**applied, "cancelled": False}
