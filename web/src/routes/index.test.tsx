import { fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { apiServer } from "@/test/apiServer";
import { renderAppAt, TEST_API_ORIGIN } from "@/test/renderAppAt";

const HIT = {
  path: "src/auth.py",
  language: "text",
  text: "def check_password(user, password):\n    return False\n",
  start_line: 12,
  end_line: 13,
  distance: 0.4,
  score: 0.61,
};

function answerSearches(record: URLSearchParams[] = []) {
  apiServer.use(
    http.get(`${TEST_API_ORIGIN}/api/projects`, () => HttpResponse.json({ registry: "/repos.toml", repos: [] })),
    http.get(`${TEST_API_ORIGIN}/api/search`, ({ request }) => {
      record.push(new URL(request.url).searchParams);
      return HttpResponse.json({
        project: "api",
        key: "github.com/acme/api",
        index_directory: "/indexes/1",
        query: "passwords",
        results: [HIT],
      });
    }),
  );
  return record;
}

describe("the search page", () => {
  it("searches with the filters in its address", async () => {
    const searched = answerSearches();
    renderAppAt("/?q=passwords&project=github.com/acme/api&language=python,%20go&limit=20");

    expect(await screen.findByText("src/auth.py")).toBeTruthy();
    expect(screen.getByText("1 match in github.com/acme/api")).toBeTruthy();
    expect(screen.getByText("0.61")).toBeTruthy();
    const parameters = searched[0];
    expect(parameters?.get("query")).toBe("passwords");
    expect(parameters?.get("project")).toBe("github.com/acme/api");
    expect(parameters?.getAll("language")).toEqual(["python", "go"]);
    expect(parameters?.get("limit")).toBe("20");
  });

  it("puts a submitted query into the address", async () => {
    answerSearches();
    const router = renderAppAt("/");

    fireEvent.change(await screen.findByRole("textbox", { name: "What are you looking for?" }), {
      target: { value: "where are passwords checked" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(router.state.location.search).toEqual({ q: "where are passwords checked" }));
    expect(await screen.findByText("src/auth.py")).toBeTruthy();
  });

  it("explains failures such as a missing index", async () => {
    apiServer.use(
      http.get(`${TEST_API_ORIGIN}/api/projects`, () => HttpResponse.json({ registry: "/repos.toml", repos: [] })),
      http.get(`${TEST_API_ORIGIN}/api/search`, () =>
        HttpResponse.json({ error: { code: "index_missing", message: "Run index first" } }, { status: 409 }),
      ),
    );
    renderAppAt("/?q=passwords");

    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Run index first");
  });
});
