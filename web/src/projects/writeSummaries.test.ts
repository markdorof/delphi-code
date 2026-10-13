import { describe, expect, it } from "vitest";
import { addSummary, indexSummary, syncSummary } from "./writeSummaries";

const INDEXED = {
  source: "/work/api",
  ok: true as const,
  unchanged: false as const,
  project: "/work/api",
  key: "local:/work/api",
  index_directory: "/indexes/1",
  files: 3,
  chunks: 7,
  skipped: 0,
  incremental: {
    num_adds: 1,
    num_deletes: 0,
    num_errors: 0,
    num_execution_starts: 1,
    num_reprocesses: 0,
    num_unchanged: 0,
  },
};
const UP_TO_DATE = {
  source: "github.com/acme/web",
  ok: true as const,
  unchanged: true as const,
  project: null,
  key: "github.com/acme/web",
  index_directory: "/indexes/2",
};
const FAILED = { source: "github.com/acme/gone", ok: false as const, error: { code: "clone_failed", message: "404" } };

describe("write summaries", () => {
  it("counts what a sync did to each project", () => {
    expect(syncSummary({ registry: "/repos.toml", repos: [INDEXED, UP_TO_DATE, FAILED] })).toBe(
      "1 project indexed, 1 up to date, 1 failed.",
    );
    expect(syncSummary({ registry: "/repos.toml", repos: [] })).toBe("Nothing is tracked yet.");
  });

  it("counts files and chunks in the right number", () => {
    expect(indexSummary({ ...INDEXED, files: 1, chunks: 1 })).toBe("Indexed 1 file into 1 chunk.");
    expect(indexSummary(INDEXED)).toBe("Indexed 3 files into 7 chunks.");
  });

  it("says when added projects still need a sync", () => {
    expect(addSummary({ registry: "/repos.toml", repos: [{ source: "/work/api", key: "local:/work/api" }] })).toBe(
      "Now tracking 1 project; run Sync all to index it.",
    );
    expect(addSummary({ registry: "/repos.toml", repos: [INDEXED] })).toBe("1 project indexed.");
  });
});
