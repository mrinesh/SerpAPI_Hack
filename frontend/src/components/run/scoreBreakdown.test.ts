import { describe, expect, it } from "vitest";
import { breakdownRows } from "./scoreBreakdown";

describe("score breakdown", () => {
  it("lists parts in order, explains missing ones and hides a zero penalty", () => {
    const rows = breakdownRows({
      area: null, evidence: 16.1, flag_penalty: 0, relevance: 38.9, roi: null, value: null,
    });
    expect(rows.map((row) => [row.label, row.points, row.note])).toEqual([
      ["Relevance", 38.9, undefined],
      ["Value vs area", null, "no price to compare"],
      ["Evidence", 16.1, undefined],
      ["ROI", null, "not available yet"],
      ["Area signals", null, "not available yet"],
    ]);
  });

  it("shows a flag penalty when there is one", () => {
    expect(breakdownRows({ relevance: 40, flag_penalty: -25 }).at(-1)).toEqual({
      key: "flag_penalty", label: "Flag penalty", points: -25, note: undefined,
    });
  });
});
