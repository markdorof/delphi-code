import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { createApiClient } from "@/api/apiClient";
import { ApiConnectionProvider } from "@/api/apiContext";
import { apiServer, SERVER_TOKEN } from "@/test/apiServer";
import { ProjectsOverview } from "./projects";

function renderOverview() {
  const connection = { client: createApiClient(SERVER_TOKEN, "http://127.0.0.1:8123"), serverToken: SERVER_TOKEN };
  render(
    <ApiConnectionProvider connection={connection}>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ProjectsOverview />
      </QueryClientProvider>
    </ApiConnectionProvider>,
  );
}

const LISTED = {
  key: "github.com/acme/api",
  tracked: true,
  source: "github.com/acme/api",
  project: "api",
  index_directory: "/indexes/1",
  ready: true,
  indexed_at: "2026-10-12T10:00:00Z",
};

describe("ProjectsOverview", () => {
  it("lists projects with their index state", async () => {
    apiServer.use(
      http.get("http://127.0.0.1:8123/api/projects", () =>
        HttpResponse.json({ registry: "/repos.toml", repos: [LISTED] }),
      ),
    );
    renderOverview();

    expect(await screen.findByText("github.com/acme/api")).toBeTruthy();
    expect(screen.getByText("Indexed")).toBeTruthy();
  });

  it("asks for a new link when the token is rejected", async () => {
    apiServer.use(
      http.get("http://127.0.0.1:8123/api/projects", () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "Send the token" } }, { status: 401 }),
      ),
    );
    renderOverview();

    expect(await screen.findByText("Open Delphi Code from your terminal")).toBeTruthy();
  });
});
