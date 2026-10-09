import { describe, expect, it } from "vitest";
import { bestIndices } from "./comparison";

describe("comparison highlights", () => {
  it("excludes unknown and nonfinite values instead of treating them as zero", () => {
    expect(bestIndices([null, 12, 20, Number.NaN], "min")).toEqual([1]);
    expect(bestIndices([undefined, 20, 12], "max")).toEqual([1]);
  });
  it("highlights ties and needs at least two known values", () => {
    expect(bestIndices([10, 10, 20], "min")).toEqual([0, 1]);
    expect(bestIndices([10, null], "min")).toEqual([]);
    expect(bestIndices([null, undefined], "max")).toEqual([]);
  });
});
