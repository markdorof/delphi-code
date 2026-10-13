import { fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { apiServer, ndjson } from "@/test/apiServer";
import { renderAppAt, TEST_API_ORIGIN } from "@/test/renderAppAt";

const BITBUCKET = { domain: "bitbucket.org", name: "Bitbucket", owner_noun: "workspace", suggested_owner: null };
const GITHUB = { domain: "github.com", name: "GitHub", owner_noun: "owner", suggested_owner: "octo" };
const ACME_REPOSITORIES = [
  {
    key: "bitbucket.org/acme/api",
    host: "bitbucket.org",
    owner: "acme",
    slug: "api",
    description: "Public API",
    private: false,
  },
  {
    key: "bitbucket.org/acme/web",
    host: "bitbucket.org",
    owner: "acme",
    slug: "web",
    description: "Website",
    private: true,
  },
];
const TRACKED_WEB = {
  key: "bitbucket.org/acme/web",
  tracked: true,
  source: "bitbucket.org/acme/web",
  project: null,
  index_directory: "/indexes/1",
  ready: true,
  indexed_at: null,
};

function answerPicker({
  services = [BITBUCKET],
  owners = [
    { slug: "acme", name: "Acme" },
    { slug: "beta", name: "Beta" },
  ],
}: {
  services?: unknown[];
  owners?: unknown[] | null;
} = {}) {
  apiServer.use(
    http.get(`${TEST_API_ORIGIN}/api/hosting-services`, () => HttpResponse.json({ hosting_services: services })),
    http.get(`${TEST_API_ORIGIN}/api/hosting-services/:domain/owners`, () => HttpResponse.json({ owners })),
    http.get(`${TEST_API_ORIGIN}/api/hosting-services/:domain/owners/:owner/repositories`, () =>
      HttpResponse.json({ repositories: ACME_REPOSITORIES }),
    ),
    http.get(`${TEST_API_ORIGIN}/api/projects`, () =>
      HttpResponse.json({ registry: "/repos.toml", repos: [TRACKED_WEB] }),
    ),
  );
}

describe("the repository picker", () => {
  it("skips the only account, then tracks and stops tracking what changed", async () => {
    answerPicker();
    let sentBody: unknown;
    apiServer.use(
      http.post("/api/projects/picked", async ({ request }) => {
        sentBody = await request.json();
        return ndjson([
          {
            done: {
              registry: "/repos.toml",
              repos: [{ source: "bitbucket.org/acme/api", key: "bitbucket.org/acme/api" }],
              removed: [{ key: "bitbucket.org/acme/web", deleted_index: "/indexes/1" }],
              cancelled: false,
            },
          },
        ]);
      }),
    );
    const router = renderAppAt("/projects/from-account");

    fireEvent.click(await screen.findByText("Acme"));
    const web = await screen.findByRole("checkbox", { name: /web/ });
    expect(web.getAttribute("aria-checked")).toBe("true");
    fireEvent.click(web);
    fireEvent.click(screen.getByRole("checkbox", { name: /api/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Index them now" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/projects"));
    expect(sentBody).toEqual({ added: ["bitbucket.org/acme/api"], removed: ["bitbucket.org/acme/web"], no_sync: true });
    expect(
      await screen.findByText("Now tracking 1 project; run Sync all to index it. Stopped tracking 1 repository."),
    ).toBeTruthy();
  });

  it("asks which account when there are several", async () => {
    answerPicker({ services: [BITBUCKET, GITHUB] });
    const router = renderAppAt("/projects/from-account");

    fireEvent.click(await screen.findByRole("button", { name: "GitHub" }));

    await waitFor(() => expect(router.state.location.search).toEqual({ service: "github.com" }));
  });

  it("lets the owner be typed when the credentials cannot list owners", async () => {
    answerPicker({ services: [GITHUB], owners: null });
    const router = renderAppAt("/projects/from-account");

    const owner = await screen.findByLabelText(/These credentials cannot list GitHub owners/);
    expect(owner).toHaveProperty("value", "octo");
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(router.state.location.search).toEqual({ service: "github.com", owner: "octo" }));
  });

  it("explains how to connect an account when none has credentials", async () => {
    answerPicker({ services: [] });
    renderAppAt("/projects/from-account");

    expect(await screen.findByRole("heading", { name: "Connect Bitbucket or GitHub" })).toBeTruthy();
  });
});
