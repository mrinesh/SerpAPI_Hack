import type { InvestmentMetrics } from "../../api/types";

function signed(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

/** "Yield 4.8% before costs · Growth +29.0% (past 12 months) · Total 33.8%"; missing parts are
 * left out, never shown as 0 (ADR 0010). */
export function metricsLine(metrics: InvestmentMetrics | null | undefined): string | null {
  if (!metrics) return null;
  const parts: string[] = [];
  const rentalYield = metrics.rental_yield_pct?.value;
  const growth = metrics.price_growth_pct?.value;
  const total = metrics.total_return_pct?.value;
  if (rentalYield != null) parts.push(`Yield ${rentalYield.toFixed(1)}% before costs`);
  if (growth != null) {
    const investor = (metrics.price_growth_pct?.note ?? "").includes("investor");
    parts.push(`Growth ${signed(growth)} (${investor ? "your estimate" : "past 12 months"})`);
  }
  if (total != null) parts.push(`Total ${total.toFixed(1)}%`);
  return parts.length > 0 ? parts.join(" · ") : null;
}

/** "Meets 4% target" / "Below 4% target", or null when the measure is missing. */
export function targetBadge(metrics: InvestmentMetrics | null | undefined, target: number): string | null {
  if (metrics?.meets_target_roi == null) return null;
  return `${metrics.meets_target_roi ? "Meets" : "Below"} ${target}% target`;
}
