import type { StreamedWriteResult } from "@/api/streamedWrite";
import { pluralized } from "@/formatting/pluralized";

type SyncReport = StreamedWriteResult<"/api/projects/sync">;
type TrackingReport = StreamedWriteResult<"/api/projects">;
type SyncedOrTracked = TrackingReport["repos"][number];

export function indexSummary(outcome: StreamedWriteResult<"/api/projects/index">): string {
  return `Indexed ${pluralized(outcome.files, "file")} into ${pluralized(outcome.chunks, "chunk")}.`;
}

export function syncSummary(report: SyncReport): string {
  return syncedCounts(report.repos) || "Nothing is tracked yet.";
}

export function addSummary(report: TrackingReport): string {
  const tracked = report.repos.filter((repo) => !("ok" in repo)).length;
  const synced = syncedCounts(report.repos);
  if (tracked > 0) {
    return `Now tracking ${pluralized(tracked, "project")}; run Sync all to index ${tracked === 1 ? "it" : "them"}.`;
  }
  return synced;
}

export function pickedSummary(report: StreamedWriteResult<"/api/projects/picked">): string {
  const stoppedTracking = report.removed?.length ?? 0;
  const parts = [
    addSummary(report),
    stoppedTracking && `Stopped tracking ${pluralized(stoppedTracking, "repository")}.`,
  ];
  return parts.filter(Boolean).join(" ") || "Nothing changed.";
}

function syncedCounts(repos: SyncedOrTracked[]): string {
  const synced = repos.filter((repo) => "ok" in repo);
  const failed = synced.filter((repo) => !repo.ok).length;
  const upToDate = synced.filter((repo) => repo.ok && repo.unchanged).length;
  const indexed = synced.length - failed - upToDate;
  const parts = [
    indexed && `${pluralized(indexed, "project")} indexed`,
    upToDate && `${upToDate} up to date`,
    failed && `${failed} failed`,
  ].filter(Boolean);
  return parts.length ? `${parts.join(", ")}.` : "";
}
