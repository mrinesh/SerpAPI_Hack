import type { PropertyDetail, SourcedField } from "../api/types";

export function bestIndices(values: (number | null | undefined)[], direction: "min" | "max"): number[] {
  const known = values.filter((value): value is number => value != null && Number.isFinite(value));
  if (known.length < 2) return [];
  const best = direction === "min" ? Math.min(...known) : Math.max(...known);
  return values.flatMap((value, index) => value === best ? [index] : []);
}

export const comparisonRows: {
  label: string; direction: "min" | "max"; unit: string;
  fact: (p: PropertyDetail) => SourcedField | null | undefined;
}[] = [
  { label: "Price", direction: "min", unit: "inr", fact: p => p.listing.price_inr },
  { label: "Size", direction: "max", unit: "sq ft", fact: p => p.listing.size_sqft },
  { label: "Price per sq ft", direction: "min", unit: "inr", fact: p => p.metrics?.price_per_sqft ?? p.listing.price_per_sqft },
  { label: "Price vs area", direction: "min", unit: "%", fact: p => p.metrics?.price_vs_area_pct },
  { label: "Rental yield before costs", direction: "max", unit: "%", fact: p => p.metrics?.rental_yield_pct },
  { label: "Past-year price growth", direction: "max", unit: "%", fact: p => p.metrics?.price_growth_pct },
  { label: "Estimated total return before costs", direction: "max", unit: "%", fact: p => p.metrics?.total_return_pct },
];
