import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AreaDevelopment } from "../../api/types";
import { DevelopmentPanel } from "./DevelopmentPanel";

const report: AreaDevelopment = {
  locality_key: "bengaluru/whitefield", locality: "Whitefield", city: "Bengaluru",
  as_of: "2026-10-07T00:00:00Z", signal: "no_sustained_growth", recommendation: "Monitor interest",
  evidence_score: 30, coverage_pct: 85, ai_review: "mixed",
  app_interest: { kind: "app_searches", query: "bengaluru/whitefield", unit: "distinct_profiles_per_week", note: "Need complete history", sustained_weeks: 0, signal: "unavailable", usable: false },
  public_interest: [{ kind: "rental_interest", query: "Whitefield rent", geo: "IN-KA", unit: "relative_interest_0_100",
    note: "Relative interest", signal: "falling", usable: true, sustained_weeks: 1, quarter_change_pct: -17.39, annual_change_pct: -6.17,
    source: { engine: "google_trends", url: "https://trends.google.com/test" }, retrieved_at: "2026-10-07",
    history: [{ week: "2026-09-14", value: 20 }, { week: "2026-09-21", value: 15 }] }],
  observed_price_growth: {}, recent_positive_infrastructure: 1,
};

describe("search-based locality research", () => {
  it("shows falling public interest and missing app history without a false priority", () => {
    const html = renderToStaticMarkup(<DevelopmentPanel reports={[report]} />);
    expect(html).toContain("No locality currently has enough");
    expect(html).toContain("-17.4%");
    expect(html).toContain("Collecting complete weekly history");
    expect(html).toContain("Distinct profiles per complete UTC week");
    expect(html).toContain("Relative interest 0–100");
    expect(html).toContain("https://trends.google.com/test");
    expect(html).toContain("Weekly observations");
    expect(html).not.toContain("#1");
  });
  it("labels supported explanations as unconfirmed, preserves quotes and sources", () => {
    const html = renderToStaticMarkup(<DevelopmentPanel reports={[{ ...report, rank: 1, signal: "corroborated_growth",
      hypotheses: [{ driver: "transport", explanation: "Possible explanation, not demonstrated causation.",
        evidence: { value: "Metro extension proposed; funding pending", confidence: 0.5, method: "llm",
          sources: [{ engine: "google_news", url: "https://example.org/metro" }] } }],
    }]} />);
    expect(html).toContain("#1");
    expect(html).toContain("unconfirmed hypotheses");
    expect(html).toContain("funding pending");
    expect(html).toContain("https://example.org/metro");
    expect(html).toContain("not a probability or return forecast");
    expect(html).toContain("Reports do not verify construction completion");
    expect(html).not.toContain("No locality currently has enough");
  });
});
