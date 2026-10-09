import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { Listing, PropertyDetail } from "../api/types";
import { CompetitorCard } from "../components/run/CompetitorCard";
import { AlertsPage } from "./AlertsPage";
import { ComparePage } from "./ComparePage";
import { SavedPage } from "./SavedPage";

function listing(id: string, price: number): Listing {
  const unknown = { value: null, confidence: 0, method: "regex" as const };
  return {
    id, name: `Property ${id}`, kind: "snippet_entry", portal: "99acres", segment: "residential",
    property_type: { value: "apartment", confidence: 0.8, method: "regex" },
    locality: { value: "whitefield", confidence: 0.8, method: "regex" },
    price_inr: { value: price, confidence: 0.8, method: "regex" },
    size_sqft: { value: 1200, confidence: 0.8, method: "regex" },
    price_per_sqft: unknown, bedrooms: unknown, status: unknown, location: unknown,
    first_seen_at: "2026-10-10T00:00:00Z", last_seen_at: "2026-10-10T00:00:00Z",
  };
}

function render(page: ReactNode, path: string, seed: (cache: QueryClient) => void) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  seed(cache);
  return renderToStaticMarkup(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}>{page}</MemoryRouter></QueryClientProvider>);
}

describe("P1 screens render stored API data", () => {
  it("shows saved properties, notes, selection and comparison controls", () => {
    const html = render(<SavedPage />, "/saved", cache => cache.setQueryData(["saved"], [
      { listing: listing("a", 6_000_000), note: "Call owner", saved_at: "2026-10-10T00:00:00Z" },
    ]));
    expect(html).toContain("Property a");
    expect(html).toContain("Call owner");
    expect(html).toContain("Select for comparison");
    expect(html).toContain("Save notes");
    expect(html).not.toContain("not implemented");
  });

  it("renders a sourced two-property comparison and validates invalid selections", () => {
    const properties: PropertyDetail[] = ["a", "b"].map((id, index) => ({
      listing: listing(id, 6_000_000 + index * 100_000), profile_id: "profile", run_id: "run",
    }));
    const html = render(<ComparePage />, "/compare?ids=a&ids=b", cache => cache.setQueryData(["compare", ["a", "b"]], { properties }));
    expect(html).toContain("Property a");
    expect(html).toContain("Property b");
    expect(html).toContain("bg-emerald-50");
    expect(html).toContain("View source search");
    expect(render(<ComparePage />, "/compare?ids=a&ids=a", () => {})).toContain("distinct properties");
  });

  it("shows unread alerts with mark-read and refresh controls", () => {
    const html = render(<AlertsPage />, "/alerts", cache => cache.setQueryData(["alerts", false], [
      { id: "alert", profile_id: "profile", listing_id: "a", kind: "price_drop",
        message: "Quoted price fell", created_at: "2026-10-10T00:00:00Z", read_at: null },
    ]));
    expect(html).toContain("Quoted price fell");
    expect(html).toContain("Mark read");
    expect(html).toContain("Check now");
    expect(html).toContain("/properties/a");
  });

  it("shows tentative review hypotheses and their source evidence", () => {
    const html = renderToStaticMarkup(<CompetitorCard typeLabel={value => value} report={{
      locality_key: "bengaluru/koramangala", locality: "Koramangala", business_type: "Cafe",
      center: { lat: 12.93, lng: 77.62 }, radius_km: 2,
      results_seen: 1, more_available: false, density_per_sq_km: 0.08, density_level: "low",
      total_reviews: 10, status: "ok", schema_version: 2, review_places_limit: 1,
      fetched_at: "2026-10-10T00:00:00Z", expires_at: "2026-10-17T00:00:00Z",
      review_status: "ok", review_places_sampled: 1,
      reviews: [{ id: "r", business: "Sample cafe", rating: 2, snippet: "Slow service",
        source: { engine: "google_maps_reviews", url: "https://example.com/review" } }],
      gaps: [{ value: "Potential gap: faster responses", confidence: 0.55, method: "llm" }],
    }} />);
    expect(html).toContain("Potential gap: faster responses");
    expect(html).toContain("Slow service");
    expect(html).toContain("https://example.com/review");
    expect(html).toContain("not proof of market demand");
  });
});
