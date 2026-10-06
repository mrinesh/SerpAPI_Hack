import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { InvestmentMetrics } from "../../api/types";
import { InvestmentMetricsPanel } from "./InvestmentMetricsPanel";

const missing = { value: null, confidence: 0, method: "computed" as const, sources: [], note: "No comparable quote" };
const base: InvestmentMetrics = {
  price_per_sqft: missing, area_avg_price_per_sqft: missing, price_vs_area_pct: missing,
  est_monthly_rent_inr: missing, rental_yield_pct: missing, price_growth_pct: missing,
  total_return_pct: missing, roi_measure: "rental_yield", target_roi_pct: 4, meets_target_roi: null,
};

describe("investment comparison", () => {
  it("shows missing values as unavailable with an unknown target assessment", () => {
    const html = renderToStaticMarkup(<InvestmentMetricsPanel metrics={base} />);
    expect(html).toContain("Unavailable");
    expect(html).toContain("Unable to assess");
    expect(html).toContain("Gross rental yield before costs");
    expect(html).toContain("No comparable quote");
    expect(html).not.toContain("Meets target");
  });
  it("distinguishes below target from unknown and labels investor assumptions", () => {
    const html = renderToStaticMarkup(<InvestmentMetricsPanel metrics={{ ...base,
      meets_target_roi: false, price_growth_pct: { ...missing, value: 0, method: "query" },
    }} />);
    expect(html).toContain("Below target");
    expect(html).toContain("Your growth assumption");
    expect(html).toContain("0.00%");
  });
  it("shows source links and confidence next to observed metrics", () => {
    const html = renderToStaticMarkup(<InvestmentMetricsPanel metrics={{ ...base, meets_target_roi: true,
      rental_yield_pct: { ...missing, value: 5, confidence: 0.6, sources: [{ engine: "google", url: "https://example.com/rent", title: "Rent evidence" }] },
    }} />);
    expect(html).toContain("Meets target");
    expect(html).toContain("60% confidence");
    expect(html).toContain("https://example.com/rent");
    expect(html).toContain("5.00%");
  });
});
