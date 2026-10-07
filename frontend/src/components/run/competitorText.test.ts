import { describe, expect, it } from "vitest";
import type { CompetitorReport } from "../../api/types";
import { countLine, readingLines } from "./competitorText";

const report = (overrides: Partial<CompetitorReport> = {}) =>
  ({
    locality: "Koramangala",
    business_type: "IT services",
    radius_km: 2,
    competitors: Array(7).fill({}),
    results_seen: 20,
    more_available: true,
    density_level: "medium",
    readings: { office: "cluster", shop_showroom: "competition" },
    ...overrides,
  }) as CompetitorReport;

describe("competitor text", () => {
  it("reads the same density as a cluster for offices and competition for shops", () => {
    expect(readingLines(report())).toEqual([
      {
        type: "office",
        label: "Business cluster: medium",
        text: "An established IT services presence nearby, a sign of tenant demand.",
      },
      { type: "shop_showroom", label: "Competition: medium", text: "Some IT services competition nearby." },
    ]);
  });

  it("keeps only the listing's own type on the detail page", () => {
    const lines = readingLines(report({ density_level: "high" }), "shop_showroom");
    expect(lines.map((line) => line.label)).toEqual(["Competition: high"]);
    expect(lines[0].text).toMatch(/^Crowded/);
  });

  it("says the count is a sample from one page of results", () => {
    expect(countLine(report())).toBe(
      "7 places within 2 km of the Koramangala centre, from the first 20 Google Maps results (more exist, so this is a floor).",
    );
    expect(countLine(report({ competitors: [{}] as CompetitorReport["competitors"], more_available: false, results_seen: 4 })))
      .toBe("1 place within 2 km of the Koramangala centre, from the first 4 Google Maps results.");
  });
});
