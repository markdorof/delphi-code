import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { apiServer, ndjson, SERVER_TOKEN } from "@/test/apiServer";
import { ApiFailure } from "./apiFailure";
import type { ProgressEvent } from "./progressEvents";
import { runStreamedWrite } from "./streamedWrite";

const SYNCED = { repos: [] };

function sync(onProgress: (event: ProgressEvent) => void = () => {}) {
  return runStreamedWrite({ path: "/api/projects/sync", body: undefined, serverToken: SERVER_TOKEN, onProgress });
}

describe("runStreamedWrite", () => {
  it("reports progress events and resolves with the done result", async () => {
    apiServer.use(
      http.post("/api/projects/sync", () =>
        ndjson([
          { event: "repository_started", key: "github.com/acme/api", position: 1, count: 1 },
          { event: "files_embedded", done: 3, total: 4 },
          { done: SYNCED },
        ]),
      ),
    );
    const events: ProgressEvent[] = [];

    await expect(sync((event) => events.push(event))).resolves.toEqual(SYNCED);
    expect(events.map((event) => event.event)).toEqual(["repository_started", "files_embedded"]);
  });

  it("rejects with the failure that ended the stream", async () => {
    apiServer.use(
      http.post("/api/projects/sync", () =>
        ndjson([
          { event: "stage_started", stage: "embedding" },
          { failed: { code: "sync_failed", message: "1 failed" } },
        ]),
      ),
    );

    await expect(sync()).rejects.toMatchObject({ code: "sync_failed", message: "1 failed" });
  });

  it("rejects with an ordinary error answered before the stream began", async () => {
    apiServer.use(
      http.post("/api/projects/sync", () =>
        HttpResponse.json({ error: { code: "busy", message: "Another write is running" } }, { status: 409 }),
      ),
    );

    await expect(sync()).rejects.toEqual(new ApiFailure("busy", "Another write is running", 409));
  });

  it("rejects when the stream stops without a result", async () => {
    apiServer.use(http.post("/api/projects/sync", () => ndjson([{ event: "listing_finished" }])));

    await expect(sync()).rejects.toMatchObject({ code: "stream_ended" });
  });
});
