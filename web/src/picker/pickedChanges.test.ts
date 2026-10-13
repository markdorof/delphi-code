import { describe, expect, it } from "vitest";
import { pickedChanges } from "./pickedChanges";

describe("pickedChanges", () => {
  it("adds newly chosen repositories and drops unchosen tracked ones, among those listed", () => {
    const listed = ["bitbucket.org/acme/api", "bitbucket.org/acme/web", "bitbucket.org/acme/docs"];
    const chosen = new Set(["bitbucket.org/acme/api", "bitbucket.org/acme/web"]);
    const tracked = new Set(["bitbucket.org/acme/web", "bitbucket.org/acme/docs", "github.com/elsewhere/kept"]);

    expect(pickedChanges(listed, chosen, tracked)).toEqual({
      added: ["bitbucket.org/acme/api"],
      removed: ["bitbucket.org/acme/docs"],
    });
  });
});
