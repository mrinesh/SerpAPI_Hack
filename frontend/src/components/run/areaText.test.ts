import { describe, expect, it } from "vitest";
import type { AreaIntel } from "../../api/types";
import { accessLine, areaWarnings, nearestByCategory, newsForPanel } from "./areaText";

describe("area text", () => {
  it("formats access, noting when it is measured from the locality centre", () => {
    expect(accessLine({
      metro_name: "Kadugodi Tree Park", metro_km: 1.8, schools_3km: 4, hospitals_3km: 3,
      measured_from: "locality centre",
    })).toBe("Metro 1.8 km · 4 schools · 3 hospitals found within 3 km (from the locality centre)");
    expect(accessLine({ metro_km: null, schools_3km: 0, hospitals_3km: 1, measured_from: "listing" }))
      .toBe("No metro within 5 km · 0 schools · 1 hospitals found within 3 km");
    expect(accessLine(null)).toBeNull();
  });

  it("keeps the nearest amenities per category and skips empty ones", () => {
    const amenity = (name: string, category: string, distance_km: number) =>
      ({ name, category, distance_km, source: { engine: "google_maps" } });
    const area = { amenities: [
      amenity("Far", "school", 3), amenity("Near", "school", 0.5), amenity("Mid", "school", 1),
      amenity("Very far", "school", 4), amenity("Clinic", "hospital", 2),
    ] } as unknown as AreaIntel;
    expect(nearestByCategory(area).map((g) => [g.label, g.items.map((a) => a.name)])).toEqual([
      ["Schools", ["Near", "Mid", "Far"]],
      ["Hospitals", ["Clinic"]],
    ]);
  });
});

describe("area warnings", () => {
  it("names each failed section in plain words", () => {
    const area = { warnings: [
      { section: "growth", provider: "serpapi+deepseek", code: "replay_miss", message: "No recorded google response." },
      { section: "rent:office", provider: "serpapi+deepseek", code: "upstream_error", message: "SerpApi timed out." },
    ] } as unknown as AreaIntel;
    expect(areaWarnings(area)).toEqual([
      "Price growth: No recorded google response.",
      "Rent (office): SerpApi timed out.",
    ]);
    expect(areaWarnings({} as AreaIntel)).toEqual([]);
  });
});

describe("area news", () => {
  it("puts classified infrastructure stories first, then the newest", () => {
    const item = (title: string, published_on: string, topic = "other", classified = true) =>
      ({ title, published_on, topic, classified, url: "https://x", sentiment: "neutral", source: { engine: "google_news" } });
    const area = { news: [
      item("Old civic", "2026-09-01", "civic"),
      item("Metro extension", "2026-09-10", "infrastructure"),
      item("New cafe", "2026-10-01", "market"),
      item("Unlabelled road story", "2026-10-02", "infrastructure", false),
    ] } as unknown as AreaIntel;
    expect(newsForPanel(area, 3).map((n) => n.title)).toEqual([
      "Metro extension", "Unlabelled road story", "New cafe",
    ]);
  });
});
