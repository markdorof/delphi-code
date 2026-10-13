import { describe, expect, it } from "vitest";
import { commaSeparatedValues } from "./commaSeparatedValues";

describe("commaSeparatedValues", () => {
  it("splits, trims and drops empty values", () => {
    expect(commaSeparatedValues(" src/*, ,tests/* ")).toEqual(["src/*", "tests/*"]);
    expect(commaSeparatedValues(undefined)).toEqual([]);
  });
});
