import { describe, expect, it } from "vitest";
import type { InvestmentMetrics } from "../../api/types";
import { metricsLine, targetBadge } from "./metricsText";

const sourced = (value: number | null, note?: string) => ({ value, confidence: 0.6, method: "computed", note });

describe("metrics text", () => {
  it("shows yield, growth and total, and hides missing parts", () => {
    const metrics = {
      rental_yield_pct: sourced(4.76), price_growth_pct: sourced(29, "past data"),
      total_return_pct: sourced(33.76), meets_target_roi: true,
    } as unknown as InvestmentMetrics;
    expect(metricsLine(metrics)).toBe("Yield 4.8% before costs · Growth +29.0% (past 12 months) · Total 33.8%");
    expect(targetBadge(metrics, 4)).toBe("Meets 4% target");
    const partial = {
      rental_yield_pct: sourced(null), price_growth_pct: sourced(5, "the investor's expected growth"),
      total_return_pct: sourced(null), meets_target_roi: null,
    } as unknown as InvestmentMetrics;
    expect(metricsLine(partial)).toBe("Growth +5.0% (your estimate)");
    expect(targetBadge(partial, 4)).toBeNull();
    const frozen = { ...metrics, target_roi_pct: 3 } as unknown as InvestmentMetrics;
    expect(targetBadge(frozen, 5)).toBe("Meets 3% target"); // the run's target, not today's profile
    expect(metricsLine(null)).toBeNull();
  });
});
