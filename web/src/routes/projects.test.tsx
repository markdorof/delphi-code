import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { apiServer, ndjson } from "@/test/apiServer";
import { renderAppAt, TEST_API_ORIGIN } from "@/test/renderAppAt";

const LOCAL = {
  key: "local:/work/api",
  tracked: true,
  source: "/work/api",
  project: "/work/api",
  index_directory: "/indexes/1",
  ready: true,
  indexed_at: "2026-10-12T10:00:00Z",
};
const REMOTE = {
  key: "github.com/acme/web",
  tracked: true,
  source: "github.com/acme/web",
  project: null,
  index_directory: "/indexes/2",
  ready: true,
  indexed_at: "2026-10-12T10:00:00Z",
  ref: "main",
};
const STORED_STATE = {
  key: LOCAL.key,
  index_directory: "/indexes/1",
  ready: true,
  paths: ["src/*"],
  languages: ["python"],
  ignores: [],
  max_bytes: 2048,
  files: 3,
  chunks: 7,
};

function answerProjects(repos: unknown[] = [LOCAL, REMOTE]) {
  apiServer.use(
    http.get(`${TEST_API_ORIGIN}/api/projects`, () => HttpResponse.json({ registry: "/repos.toml", repos })),
    http.get(`${TEST_API_ORIGIN}/api/projects/status`, () => HttpResponse.json(STORED_STATE)),
  );
}

describe("the projects page", () => {
  it("offers re-indexing only for local projects", async () => {
    answerProjects();
    renderAppAt("/projects");

    expect(await screen.findByText("local:/work/api")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Re-index local:/work/api" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Re-index github.com/acme/web" })).toBeNull();
  });

  it("re-indexes with the stored selection and shows the streamed progress", async () => {
    answerProjects();
    let sentBody: unknown;
    apiServer.use(
      http.post("/api/projects/index", async ({ request }) => {
        sentBody = await request.json();
        return ndjson([
          { event: "repository_started", key: LOCAL.key, position: 1, count: 1 },
          { event: "files_embedded", done: 2, total: 3 },
          { done: { ...STORED_STATE, project: "/work/api", files: 3, chunks: 7, skipped: 0, incremental: {} } },
        ]);
      }),
    );
    renderAppAt("/projects");

    fireEvent.click(await screen.findByRole("button", { name: "Re-index local:/work/api" }));

    const activity = await screen.findByRole("region", { name: "Activity" });
    expect(await within(activity).findByText("Indexed 3 files into 7 chunks.")).toBeTruthy();
    expect(sentBody).toEqual({
      project: LOCAL.key,
      path: ["src/*"],
      language: ["python"],
      ignore: [],
      max_bytes: 2048,
    });
  });

  it("explains that another write is already running", async () => {
    answerProjects();
    apiServer.use(
      http.post("/api/projects/sync", () =>
        HttpResponse.json(
          { error: { code: "busy", message: "Another index, sync, add or setup is running" } },
          { status: 409 },
        ),
      ),
    );
    renderAppAt("/projects");

    fireEvent.click(await screen.findByRole("button", { name: "Sync all" }));

    const activity = await screen.findByRole("region", { name: "Activity" });
    expect(await within(activity).findByText("Another index, sync, add or setup is running")).toBeTruthy();
  });

  it("removes a project after confirmation, keeping its index when asked", async () => {
    answerProjects();
    let removal: URLSearchParams | undefined;
    apiServer.use(
      http.delete(`${TEST_API_ORIGIN}/api/projects`, ({ request }) => {
        removal = new URL(request.url).searchParams;
        return HttpResponse.json({ key: REMOTE.key, untracked: true, deleted_index: null });
      }),
    );
    renderAppAt("/projects");

    fireEvent.click(await screen.findByRole("button", { name: "Remove github.com/acme/web" }));
    fireEvent.click(await screen.findByRole("checkbox", { name: "Keep the index so it stays searchable" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(await screen.findByText("Removed github.com/acme/web; its index was kept.")).toBeTruthy();
    expect(removal?.get("name")).toBe(REMOTE.key);
    expect(removal?.get("keep_index")).toBe("true");
  });

  it("adds folders and repositories one per line", async () => {
    answerProjects([]);
    let sentBody: unknown;
    apiServer.use(
      http.post("/api/projects", async ({ request }) => {
        sentBody = await request.json();
        return ndjson([{ done: { registry: "/repos.toml", repos: [{ source: "/work/api", key: LOCAL.key }] } }]);
      }),
    );
    renderAppAt("/projects");

    fireEvent.click(await screen.findByRole("button", { name: "Add projects" }));
    fireEvent.change(screen.getByLabelText("Folders or repositories, one per line"), {
      target: { value: "/work/api\n\n github.com/acme/web " },
    });
    fireEvent.change(screen.getByLabelText("Languages"), { target: { value: "python, go" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Index them now" }));
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() =>
      expect(sentBody).toEqual({
        sources: ["/work/api", "github.com/acme/web"],
        path: [],
        language: ["python", "go"],
        ignore: [],
        no_sync: true,
      }),
    );
    expect(await screen.findByText("Now tracking 1 project; run Sync all to index it.")).toBeTruthy();
  });

  it("asks for a new link when the token is rejected", async () => {
    apiServer.use(
      http.get(`${TEST_API_ORIGIN}/api/projects`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "Send the token" } }, { status: 401 }),
      ),
    );
    renderAppAt("/projects");

    expect(await screen.findByText("Open Delphi Code from your terminal")).toBeTruthy();
  });
});
