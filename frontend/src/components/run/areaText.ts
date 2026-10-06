import type { AreaAccess, Amenity, AreaIntel } from "../../api/types";

/** "Metro 1.8 km · 4 schools · 3 hospitals found within 3 km (from the locality centre)". */
export function accessLine(access: AreaAccess | null | undefined): string | null {
  if (!access) return null;
  const metro = access.metro_km != null ? `Metro ${access.metro_km} km` : "No metro within 5 km";
  const where = access.measured_from === "listing" ? "" : " (from the locality centre)";
  return `${metro} · ${access.schools_3km} schools · ${access.hospitals_3km} hospitals found within 3 km${where}`;
}

const CATEGORY_LABELS: Record<string, string> = {
  metro: "Metro stations", school: "Schools", hospital: "Hospitals",
};

/** Up to `limit` nearest amenities per category, in display order. */
export function nearestByCategory(area: AreaIntel, limit = 3): { label: string; items: Amenity[] }[] {
  return Object.entries(CATEGORY_LABELS).flatMap(([category, label]) => {
    const items = (area.amenities ?? [])
      .filter((amenity) => amenity.category === category)
      .sort((a, b) => (a.distance_km ?? 0) - (b.distance_km ?? 0))
      .slice(0, limit);
    return items.length > 0 ? [{ label, items }] : [];
  });
}

const SECTION_LABELS: Record<string, string> = {
  centre: "Locality centre", metro: "Metro stations", school: "Schools", hospital: "Hospitals",
  growth: "Price growth", summary: "AI summary", news: "Local news", classify_news: "News topics",
};

/** "Price growth: No recorded google response…", one line per section that failed (ADR 0019). */
export function areaWarnings(area: AreaIntel): string[] {
  return (area.warnings ?? []).map((warning) => {
    const label = warning.section.startsWith("rent:")
      ? `Rent (${warning.section.slice(5).replace("_", " ")})`
      : SECTION_LABELS[warning.section] ?? warning.section;
    return `${label}: ${warning.message}`;
  });
}

type NewsItem = NonNullable<AreaIntel["news"]>[number];

/** Up to `limit` news items: infrastructure stories first, then newest (ADR 0020). */
export function newsForPanel(area: AreaIntel, limit = 5): NewsItem[] {
  const newest = (a: NewsItem, b: NewsItem) => (b.published_on ?? "").localeCompare(a.published_on ?? "");
  const items = [...(area.news ?? [])].sort(newest);
  const infrastructure = items.filter((item) => item.classified && item.topic === "infrastructure");
  const rest = items.filter((item) => !(item.classified && item.topic === "infrastructure"));
  return [...infrastructure, ...rest].slice(0, limit);
}
