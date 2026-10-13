import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { apiServer, SERVER_TOKEN } from "@/test/apiServer";
import { createApiClient, dataOrFailure } from "./apiClient";
import { ApiFailure } from "./apiFailure";

const client = createApiClient(SERVER_TOKEN, "http://127.0.0.1:8123");

describe("the API client", () => {
  it("sends the server token", async () => {
    apiServer.use(
      http.get("http://127.0.0.1:8123/api/projects", ({ request }) =>
        request.headers.get("Authorization") === `Bearer ${SERVER_TOKEN}`
          ? HttpResponse.json({ registry: "/repos.toml", repos: [] })
          : HttpResponse.json({ error: { code: "unauthorized", message: "no" } }, { status: 401 }),
      ),
    );

    expect(dataOrFailure(await client.GET("/api/projects"))).toEqual({ registry: "/repos.toml", repos: [] });
  });

  it("turns error bodies into failures with their code", async () => {
    apiServer.use(
      http.get("http://127.0.0.1:8123/api/projects/status", () =>
        HttpResponse.json({ error: { code: "index_missing", message: "Run index first" } }, { status: 409 }),
      ),
    );

    const answer = await client.GET("/api/projects/status", { params: { query: { project: "api" } } });

    expect(() => dataOrFailure(answer)).toThrow(new ApiFailure("index_missing", "Run index first", 409));
  });

  it("asks for a new link when the server rejects the token", () => {
    expect(ApiFailure.fromBody(401, { error: { code: "unauthorized", message: "x" } }).needsNewServerToken).toBe(true);
    expect(ApiFailure.fromBody(502, "Bad gateway").code).toBe("http_error");
  });
});
