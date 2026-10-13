import { describe, expect, it } from "vitest";
import { serverTokenFromPageAddress } from "./serverToken";

describe("serverTokenFromPageAddress", () => {
  it("keeps the handed-over token and removes it from the address", () => {
    window.history.replaceState(null, "", "/projects?view=all#token=abc%2D123");

    const token = serverTokenFromPageAddress(window.location, window.history, window.sessionStorage);

    expect(token).toBe("abc-123");
    expect(window.location.hash).toBe("");
    expect(window.location.pathname + window.location.search).toBe("/projects?view=all");
  });

  it("finds the token again after a reload", () => {
    window.history.replaceState(null, "", "/#token=kept");
    serverTokenFromPageAddress(window.location, window.history, window.sessionStorage);

    expect(serverTokenFromPageAddress(window.location, window.history, window.sessionStorage)).toBe("kept");
  });

  it("has no token when the page was opened without one", () => {
    window.history.replaceState(null, "", "/");

    expect(serverTokenFromPageAddress(window.location, window.history, window.sessionStorage)).toBeNull();
  });
});
