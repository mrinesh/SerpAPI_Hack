import { describe, expect, it } from "vitest";
import type { AreaIntel, CompetitorReport, Listing, Recommendation, Verification } from "../../api/types";
import { layoutMap, legendEntries, markerColor } from "./mapLayout";

const listing = (id: string, locality: string, gps?: [number, number]) =>
  ({
    id,
    locality: { value: locality },
    location: { value: gps ? { lat: gps[0], lng: gps[1] } : null },
  }) as Listing;

const area = (slug: string, center: [number, number] | null, amenities: [string, string, [number, number] | null][] = []) =>
  ({
    locality_key: `bengaluru/${slug}`,
    locality: slug[0].toUpperCase() + slug.slice(1),
    center: center && { lat: center[0], lng: center[1] },
    amenities: amenities.map(([name, category, at]) => ({
      name, category, location: at && { lat: at[0], lng: at[1] }, source: { engine: "google_maps" },
    })),
  }) as AreaIntel;

const ranked = (id: string, rank: number, score: number) =>
  ({ listing: { id }, rank, score }) as Recommendation;

const check = (id: string, verdict: Verification["verdict"]) =>
  ({ listing_id: id, verdict }) as Verification;

describe("results map layout", () => {
  it("uses a listing's own GPS, else groups it at its locality centre, else counts it", () => {
    const layout = layoutMap({
      listings: [
        listing("project", "whitefield", [12.98, 77.76]),
        listing("entry", "whitefield"),
        listing("elsewhere", "hebbal"),
      ],
      verifications: [],
      recommendations: [],
      areas: [area("whitefield", [12.97, 77.75])],
    });
    expect(layout.listings.map((m) => [m.item.listing.id, m.position])).toEqual([["project", [12.98, 77.76]]]);
    expect(layout.localities).toHaveLength(1);
    expect(layout.localities[0]).toMatchObject({ locality: "Whitefield", position: [12.97, 77.75] });
    expect(layout.localities[0].items.map((i) => i.listing.id)).toEqual(["entry"]);
    expect(layout.unplaced.map((i) => i.listing.id)).toEqual(["elsewhere"]);
    expect(layout.bounds).toEqual([[12.98, 77.76], [12.97, 77.75]]);
  });

  it("never places a listing at a centre the area could not geocode", () => {
    const layout = layoutMap({
      listings: [listing("entry", "koramangala")],
      verifications: [], recommendations: [],
      areas: [area("koramangala", null)],
    });
    expect(layout.localities).toEqual([]);
    expect(layout.unplaced).toHaveLength(1);
  });

  it("labels each candidate with its run status and orders groups ranked first", () => {
    const layout = layoutMap({
      listings: ["filtered", "unchecked", "second", "checked", "first"].map((id) => listing(id, "whitefield")),
      verifications: [check("filtered", "reject"), check("checked", "weak"), check("first", "strong"), check("second", "partial")],
      recommendations: [ranked("second", 2, 55), ranked("first", 1, 81)],
      areas: [area("whitefield", [12.97, 77.75])],
    });
    expect(layout.localities[0].items.map((i) => [i.listing.id, i.status])).toEqual([
      ["first", "ranked"], ["second", "ranked"], ["checked", "checked"],
      ["unchecked", "unchecked"], ["filtered", "filtered"],
    ]);
    expect(layout.localities[0].items[0]).toMatchObject({ rank: 1, score: 81 });
  });

  it("draws ranked GPS markers last so the best sit on top", () => {
    const layout = layoutMap({
      listings: [listing("top", "w", [1, 1]), listing("other", "w", [2, 2]), listing("next", "w", [3, 3])],
      verifications: [check("other", "partial")],
      recommendations: [ranked("top", 1, 90), ranked("next", 2, 60)],
      areas: [],
    });
    expect(layout.listings.map((m) => m.item.listing.id)).toEqual(["other", "next", "top"]);
  });

  it("keeps metro, school and hospital amenities with positions, once each", () => {
    const shared: [string, string, [number, number]] = ["Metro A", "metro", [1, 2]];
    const layout = layoutMap({
      listings: [listing("p", "whitefield", [5, 5])],
      verifications: [], recommendations: [],
      areas: [
        area("whitefield", [0, 0], [shared, ["School B", "school", null], ["Mall C", "mall", [3, 3]]]),
        area("hebbal", [0, 0], [shared, ["Hospital D", "hospital", [4, 4]]]),
      ],
    });
    expect(layout.amenities.map((m) => m.amenity.name)).toEqual(["Metro A", "Hospital D"]);
    expect(layout.bounds).toEqual([[5, 5]]); // amenities stay out of the opening view by default
    expect(layoutMap({
      listings: [listing("p", "whitefield", [5, 5])], verifications: [], recommendations: [],
      areas: [area("whitefield", [0, 0], [shared])], fitAmenities: true,
    }).bounds).toEqual([[5, 5], [1, 2]]);
  });

  it("takes in the amenities when no candidate has its own position", () => {
    const amenities: [string, string, [number, number]][] = [["Metro A", "metro", [1, 2]]];
    expect(layoutMap({
      listings: [], verifications: [], recommendations: [],
      areas: [area("whitefield", null, amenities)],
    }).bounds).toEqual([[1, 2]]);
    expect(layoutMap({
      listings: [listing("entry", "whitefield")], verifications: [], recommendations: [],
      areas: [area("whitefield", [0, 0], amenities)],
    }).bounds).toEqual([[0, 0], [1, 2]]);
  });

  it("colours ranked markers by score band and the rest by status", () => {
    const item = (status: "ranked" | "filtered", score?: number) => ({ listing: listing("x", "w"), status, score });
    expect(markerColor(item("ranked", 75))).toBe("#059669");
    expect(markerColor(item("ranked", 50))).toBe("#d97706");
    expect(markerColor(item("ranked", 49))).toBe("#ea580c");
    expect(markerColor(item("filtered"))).toBe("#dc2626");
  });

  it("lists only the colours on the map in its legend", () => {
    const layout = layoutMap({
      listings: [listing("top", "whitefield", [1, 1]), listing("entry", "whitefield")],
      verifications: [check("entry", "reject")],
      recommendations: [ranked("top", 1, 62)],
      areas: [area("whitefield", [0, 0], [["Metro A", "metro", [1, 2]]])],
    });
    expect(legendEntries(layout).map((e) => e.label)).toEqual(["Ranked, score 50–69", "Filtered out", "Metro"]);
  });

  it("places competitors with a position and takes them in when no candidate has its own", () => {
    const report = {
      business_type: "IT services",
      competitors: [
        { name: "Near Co", location: { lat: 1, lng: 1 } },
        { name: "No point", location: null },
      ],
    } as CompetitorReport;
    const layout = layoutMap({
      listings: [listing("entry", "koramangala")], verifications: [], recommendations: [],
      areas: [area("koramangala", [0, 0], [["Metro A", "metro", [9, 9]]])], competitors: [report],
    });
    expect(layout.competitors.map((m) => [m.competitor.name, m.position])).toEqual([["Near Co", [1, 1]]]);
    expect(layout.bounds).toEqual([[0, 0], [1, 1]]); // the nearby competitors, not far amenities
    expect(legendEntries(layout).map((e) => e.label)).toEqual(["Not AI-checked", "Metro", "IT services nearby"]);
  });
});
