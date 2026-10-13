import { describe, expect, it } from "vitest";
import { ApiFailure } from "@/api/apiFailure";
import type { ProgressEvent } from "@/api/progressEvents";
import { activityAfterProgress, failedActivity, startedActivity, succeededActivity } from "./writeActivity";

function afterEvents(...events: ProgressEvent[]) {
  return events.reduce(activityAfterProgress, startedActivity("Syncing"));
}

const UP_TO_DATE = {
  source: "github.com/acme/web",
  ok: true as const,
  unchanged: true as const,
  project: null,
  key: "github.com/acme/web",
  index_directory: "/indexes/2",
};

describe("write activity", () => {
  it("follows the current repository, stage and embedding progress", () => {
    const activity = afterEvents(
      { event: "repository_started", key: "github.com/acme/api", position: 2, count: 3 },
      { event: "stage_started", stage: "embedding" },
      { event: "files_embedded", done: 4, total: 10 },
    );

    expect(activity.repository).toEqual({ key: "github.com/acme/api", position: 2, count: 3 });
    expect(activity.stage).toBe("embedding");
    expect(activity.embedded).toEqual({ done: 4, total: 10 });
  });

  it("forgets the last repository's progress when the next one starts", () => {
    const activity = afterEvents(
      { event: "repository_started", key: "a", position: 1, count: 2 },
      { event: "files_embedded", done: 4, total: 4 },
      { event: "repository_started", key: "b", position: 2, count: 2 },
    );

    expect(activity.embedded).toBeUndefined();
    expect(activity.stage).toBeUndefined();
  });

  it("records each repository's outcome, naming failures by the repository that was running", () => {
    const activity = afterEvents(
      { event: "repository_started", key: "github.com/acme/web", position: 1, count: 2 },
      { event: "repository_finished", result: UP_TO_DATE },
      { event: "repository_started", key: "github.com/acme/gone", position: 2, count: 2 },
      { event: "repository_failed", error: { code: "clone_failed", message: "Repository not found" } },
    );

    expect(activity.outcomes).toEqual([
      { key: "github.com/acme/web", succeeded: true, detail: "Up to date" },
      { key: "github.com/acme/gone", succeeded: false, detail: "Repository not found" },
    ]);
  });

  it("ends with a summary or a failure and drops the step in progress", () => {
    const running = afterEvents({ event: "stage_started", stage: "saving" });

    expect(succeededActivity(running, "Done.")).toMatchObject({ state: "succeeded", summary: "Done." });
    expect(succeededActivity(running, "Done.").stage).toBeUndefined();
    const busy = new ApiFailure("busy", "Another write is running", 409);
    expect(failedActivity(running, busy)).toMatchObject({ state: "failed", failure: busy });
  });
});
