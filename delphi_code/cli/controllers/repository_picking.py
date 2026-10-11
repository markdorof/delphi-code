from typing import Protocol

from ...domain.selection import FileSelection
from ...domain.tracking_changes import TrackingChanges
from ...domain.tracking_report import TrackingReport
from ...infrastructure.registry import Registry
from ...infrastructure.store import Store
from ...services import remote_repositories
from ...services.progress import Progress


class Prompts(Protocol):
    def require_terminal(self) -> None: ...
    def choose_host(self, hosts): ...
    def choose_owner(self, host, owners) -> str | None: ...
    def type_owner(self, host) -> str | None: ...
    def choose_repositories(self, owner, repositories, tracked_keys) -> set[str] | None: ...
    def confirm_changes(self, changes: TrackingChanges) -> bool: ...


def pick_tracking_changes(hosts, tracked_keys, prompts: Prompts, progress: Progress) -> TrackingChanges | None:
    host = hosts[0] if len(hosts) == 1 else prompts.choose_host(hosts)
    if host is None:
        return None
    owner = _pick_owner(host, prompts, progress)
    if owner is None:
        return None
    repositories = remote_repositories.repositories_of_owner(host, owner, progress)
    chosen_keys = prompts.choose_repositories(owner, repositories, tracked_keys)
    if chosen_keys is None:
        return None
    changes = TrackingChanges.from_selection(repositories, chosen_keys, tracked_keys)
    if changes and not prompts.confirm_changes(changes):
        return None
    return changes


def add_picked(
    ref: str | None, selection: FileSelection, model: str, sync_now: bool, progress: Progress, prompts: Prompts
) -> TrackingReport:
    prompts.require_terminal()
    hosts = remote_repositories.hosts_with_credentials()
    store, registry = Store(), Registry()
    changes = pick_tracking_changes(hosts, remote_repositories.tracked_keys(registry), prompts, progress)
    return remote_repositories.apply_picked_changes(store, registry, changes, ref, selection, model, sync_now, progress)


def _pick_owner(host, prompts: Prompts, progress: Progress) -> str | None:
    owners = remote_repositories.owners_if_listable(host, progress)
    if owners is None:
        return prompts.type_owner(host)
    return owners[0].slug if len(owners) == 1 else prompts.choose_owner(host, owners)
