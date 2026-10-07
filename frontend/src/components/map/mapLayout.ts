import type { Amenity, AreaIntel, Competitor, CompetitorReport, Listing, Recommendation, Verification } from "../../api/types";

export type LatLng = [number, number];

/** Where a run left a candidate: ranked, checked but unranked, filtered out, or never checked. */
export type MapStatus = "ranked" | "checked" | "filtered" | "unchecked";

export interface MapItem {
  listing: Listing;
  status: MapStatus;
  rank?: number;
  score?: number; // the ranked composite score (F-04); other statuses have none
}

/** A candidate at its own GPS: a Maps project, or a priced entry matched to one (F-02). */
export interface ListingMarker {
  position: LatLng;
  item: MapItem;
}

/** Candidates with no position of their own, shown together at their locality's geocoded
 * centre (F-05) rather than at an invented point. */
export interface LocalityMarker {
  locality: string;
  position: LatLng;
  items: MapItem[];
}

export interface AmenityMarker {
  position: LatLng;
  amenity: Amenity;
  locality: string;
}

/** A same-category business from a commercial run's competitor report (F-06). */
export interface CompetitorMarker {
  position: LatLng;
  competitor: Competitor;
  businessType: string;
}

export interface MapLayout {
  listings: ListingMarker[];
  localities: LocalityMarker[];
  amenities: AmenityMarker[];
  competitors: CompetitorMarker[];
  unplaced: MapItem[]; // no GPS and no locality centre (yet): counted, never drawn
  bounds: LatLng[]; // what the map opens on
}

const AMENITY_CATEGORIES = new Set(["metro", "school", "hospital"]);

const STATUS_ORDER: Record<MapStatus, number> = { ranked: 0, checked: 1, unchecked: 2, filtered: 3 };

const byStatusThenRank = (a: MapItem, b: MapItem) =>
  STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || (a.rank ?? 0) - (b.rank ?? 0);

/** Places a run's candidates for the results map (F-19). Positions only ever come from SerpApi:
 * a listing's own GPS, else its locality's centre, labelled as such. Amenities are drawn once
 * each, as are commercial competitors (F-06). The map opens on the candidates. When none has its
 * own position (a lone locality centre says little) it also takes in the competitors, which sit
 * within 2 km, else the amenities; `fitAmenities` takes in everything (the detail page). */
export function layoutMap({ listings, verifications, recommendations, areas, competitors = [], fitAmenities = false }: {
  listings: Listing[];
  verifications: Verification[];
  recommendations: Recommendation[];
  areas: AreaIntel[];
  competitors?: CompetitorReport[];
  fitAmenities?: boolean;
}): MapLayout {
  const ranked = new Map(recommendations.map((r) => [r.listing.id, r]));
  const checks = new Map(verifications.map((v) => [v.listing_id, v]));
  const centres = new Map(
    areas.flatMap((area) => (area.center ? [[localitySlug(area), area] as const] : [])),
  );

  const result: MapLayout = { listings: [], localities: [], amenities: [], competitors: [], unplaced: [], bounds: [] };
  const groups = new Map<string, LocalityMarker>();
  for (const listing of listings) {
    const recommendation = ranked.get(listing.id);
    const check = checks.get(listing.id);
    const item: MapItem = recommendation
      ? { listing, status: "ranked", rank: recommendation.rank, score: recommendation.score }
      : { listing, status: check ? (check.verdict === "reject" ? "filtered" : "checked") : "unchecked" };
    const own = listing.location.value;
    const area = centres.get(listing.locality.value ?? "");
    if (own) {
      result.listings.push({ position: [own.lat, own.lng], item });
    } else if (area?.center) {
      const key = localitySlug(area);
      if (!groups.has(key)) {
        groups.set(key, { locality: area.locality, position: [area.center.lat, area.center.lng], items: [] });
      }
      groups.get(key)!.items.push(item);
    } else {
      result.unplaced.push(item);
    }
  }
  result.listings.sort((a, b) => byStatusThenRank(b.item, a.item)); // ranked drawn last, on top
  result.localities = [...groups.values()];
  result.localities.forEach((group) => group.items.sort(byStatusThenRank));

  const seen = new Set<string>();
  for (const area of areas) {
    for (const amenity of area.amenities ?? []) {
      if (!amenity.location || !AMENITY_CATEGORIES.has(amenity.category)) continue;
      const key = `${amenity.name}|${amenity.location.lat}|${amenity.location.lng}`;
      if (seen.has(key)) continue;
      seen.add(key);
      result.amenities.push({ position: [amenity.location.lat, amenity.location.lng], amenity, locality: area.locality });
    }
  }

  for (const report of competitors) {
    for (const competitor of report.competitors ?? []) {
      if (!competitor.location) continue;
      result.competitors.push({
        position: [competitor.location.lat, competitor.location.lng],
        competitor,
        businessType: report.business_type,
      });
    }
  }

  const candidates = [...result.listings, ...result.localities].map((marker) => marker.position);
  const near = result.competitors.map((marker) => marker.position); // within a 2 km radius
  const amenities = result.amenities.map((marker) => marker.position); // up to 5 km out
  result.bounds = fitAmenities ? [...candidates, ...near, ...amenities]
    : result.listings.length > 0 ? candidates
    : [...candidates, ...(near.length > 0 ? near : amenities)];
  return result;
}

/** "bengaluru/whitefield" → "whitefield", the slug listings carry. */
function localitySlug(area: AreaIntel): string {
  return area.locality_key.split("/").pop() ?? area.locality_key;
}

export const SCORE_COLORS = { high: "#059669", mid: "#d97706", low: "#ea580c" };

export const STATUS_COLORS: Record<Exclude<MapStatus, "ranked">, string> = {
  checked: "#64748b", unchecked: "#94a3b8", filtered: "#dc2626",
};

/** Marker colour: ranked candidates by score band (70+, 50–69, under 50), the rest by status. */
export function markerColor(item: MapItem): string {
  if (item.status === "ranked") {
    const score = item.score ?? 0;
    return score >= 70 ? SCORE_COLORS.high : score >= 50 ? SCORE_COLORS.mid : SCORE_COLORS.low;
  }
  return STATUS_COLORS[item.status];
}

/** Legend entries for the colours actually on the map, ranked bands first. */
export function legendEntries(layout: MapLayout): { color: string; label: string }[] {
  const items = [...layout.listings.map((m) => m.item), ...layout.localities.flatMap((g) => g.items)];
  const entries = [
    { color: SCORE_COLORS.high, label: "Ranked, score 70+" },
    { color: SCORE_COLORS.mid, label: "Ranked, score 50–69" },
    { color: SCORE_COLORS.low, label: "Ranked, score under 50" },
    ...(["checked", "unchecked", "filtered"] as const).map((s) => ({ color: STATUS_COLORS[s], label: STATUS_LABELS[s] })),
  ];
  const present = new Set(items.map(markerColor));
  const categories = new Set(layout.amenities.map((m) => m.amenity.category));
  return [
    ...entries.filter((entry) => present.has(entry.color)),
    ...Object.entries(AMENITY_LABELS)
      .filter(([category]) => categories.has(category as Amenity["category"]))
      .map(([category, label]) => ({ color: AMENITY_COLORS[category], label })),
    ...[...new Set(layout.competitors.map((m) => m.businessType))]
      .map((business) => ({ color: COMPETITOR_COLOR, label: `${business} nearby` })),
  ];
}

const AMENITY_LABELS: Record<string, string> = { metro: "Metro", school: "School", hospital: "Hospital" };

export const STATUS_LABELS: Record<MapStatus, string> = {
  ranked: "Ranked",
  checked: "Checked, not ranked",
  unchecked: "Not AI-checked",
  filtered: "Filtered out",
};

export const COMPETITOR_COLOR = "#92400e";

export const AMENITY_COLORS: Record<string, string> = {
  metro: "#7c3aed", school: "#2563eb", hospital: "#0891b2",
};
