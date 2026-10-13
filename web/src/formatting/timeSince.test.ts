import { describe, expect, it } from "vitest";
import { timeSince } from "./timeSince";

const NOW = new Date("2026-10-13T12:00:00Z");

describe("timeSince", () => {
  it("names the largest whole unit", () => {
    expect(timeSince("2026-10-13T11:59:40Z", NOW)).toBe("just now");
    expect(timeSince("2026-10-13T11:15:00Z", NOW)).toBe("45 minutes ago");
    expect(timeSince("2026-10-12T12:00:00Z", NOW)).toBe("yesterday");
    expect(timeSince("2026-09-13T12:00:00Z", NOW)).toBe("last month");
  });
});
