import type { ExtractionMethod, SerpEngine, SourceRef } from "../api/types";

export type ConfidenceLevel = "high" | "medium" | "low";

/** Badge level for a `Sourced` confidence. Parsed and SerpApi fields score 0.8–0.9; computed,
 * query-derived and AI-extracted area figures 0.5–0.7 (backend cleaning and enrichment). */
export function confidenceLevel(confidence: number | undefined): ConfidenceLevel {
  const value = confidence ?? 0;
  if (value >= 0.8) return "high";
  if (value >= 0.5) return "medium";
  return "low";
}

export const METHOD_LABELS: Record<ExtractionMethod, string> = {
  serpapi_field: "SerpApi field",
  regex: "Parsed from the result text",
  llm: "AI-extracted, checked against the text",
  computed: "Computed from other figures",
  query: "From the search that found it",
};

export const ENGINE_LABELS: Record<SerpEngine, string> = {
  google: "Google Search",
  google_local: "Google Local",
  google_maps: "Google Maps",
  google_maps_directions: "Google Maps directions",
  google_maps_reviews: "Google Maps reviews",
  google_news: "Google News",
  google_trends: "Google Trends",
};

/** A readable name for a source: its title, else the link's host, else the SerpApi search id. */
export function sourceLabel(source: SourceRef): string {
  if (source.title) return source.title;
  if (source.url) {
    try {
      return new URL(source.url).host.replace(/^www\./, "");
    } catch {
      return source.url;
    }
  }
  return `Search ${source.search_id ?? ""}`.trim();
}

/** Sources grouped by engine, in first-seen order. */
export function groupSources(sources: SourceRef[]): { engine: SerpEngine; label: string; items: SourceRef[] }[] {
  const groups = new Map<SerpEngine, SourceRef[]>();
  for (const source of sources) {
    groups.set(source.engine, [...(groups.get(source.engine) ?? []), source]);
  }
  return [...groups].map(([engine, items]) => ({ engine, label: ENGINE_LABELS[engine], items }));
}
