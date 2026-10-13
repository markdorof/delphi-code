import { describe, expect, it } from "vitest";
import { searchFiltersFromUrl } from "./searchFilters";

describe("searchFiltersFromUrl", () => {
  it("keeps non-empty text filters and a supported limit", () => {
    expect(searchFiltersFromUrl({ q: " retry ", project: "github.com/acme/api", path: "", limit: "20" })).toEqual({
      q: "retry",
      project: "github.com/acme/api",
      limit: 20,
    });
  });

  it("drops the default limit and limits the form cannot choose", () => {
    expect(searchFiltersFromUrl({ q: "retry", limit: 10 })).toEqual({ q: "retry" });
    expect(searchFiltersFromUrl({ q: "retry", limit: 999 })).toEqual({ q: "retry" });
  });
});
