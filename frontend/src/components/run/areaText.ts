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
      : warning.section.startsWith("commute:")
        ? `Commute (${warning.section.slice(8).replace(/-/g, " ")})`
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

type Commute = NonNullable<AreaIntel["commutes"]>[string];

/** 70 -> "1 hr 10 min", 60 -> "1 hr", 45 -> "45 min". */
export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`;
}

export interface CommuteRow {
  hub: string;
  time: string; // "1 hr 10 min"
  typical: string | null; // "typically 55 min–1 hr 50 min"
  route: string; // "21.4 km via ITPL Main Rd and NH 44"
  url: string | null;
}

/** The weekday 9 AM drive to each job hub, quickest first (F-23, ADR 0026). */
export function commuteRows(area: AreaIntel): CommuteRow[] {
  const commutes = Object.values(area.commutes ?? {}).filter(
    (c): c is Commute => c?.duration_min?.value != null,
  );
  return commutes
    .sort((a, b) => (a.duration_min.value ?? 0) - (b.duration_min.value ?? 0))
    .map((c) => ({
      hub: c.hub,
      time: formatMinutes(c.duration_min.value ?? 0),
      typical: c.typical_min != null && c.typical_max != null
        ? `typically ${formatMinutes(c.typical_min)}–${formatMinutes(c.typical_max)}`
        : c.typical_text ? `typically ${c.typical_text}` : null,
      route: [`${c.distance_km} km`, c.via && `via ${c.via}`].filter(Boolean).join(" "),
      url: c.duration_min.sources?.[0]?.url ?? null,
    }));
}
