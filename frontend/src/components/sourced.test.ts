import { describe, expect, it } from "vitest";
import type { SourceRef } from "../api/types";
import { confidenceLevel, groupSources, sourceLabel } from "./sourced";

describe("sourced values", () => {
  it("maps confidence to a badge level", () => {
    expect(confidenceLevel(0.9)).toBe("high");
    expect(confidenceLevel(0.8)).toBe("high");
    expect(confidenceLevel(0.6)).toBe("medium");
    expect(confidenceLevel(0.5)).toBe("medium");
    expect(confidenceLevel(0.2)).toBe("low");
    expect(confidenceLevel(undefined)).toBe("low");
  });

  it("names a source by title, then host, then search id", () => {
    expect(sourceLabel({ engine: "google", title: "Rates", url: "https://x.com" })).toBe("Rates");
    expect(sourceLabel({ engine: "google", url: "https://www.99acres.com/a/b" })).toBe("99acres.com");
    expect(sourceLabel({ engine: "google_maps", search_id: "abc" })).toBe("Search abc");
  });

  it("groups sources by engine in first-seen order", () => {
    const sources: SourceRef[] = [
      { engine: "google", url: "https://a" },
      { engine: "google_maps", url: "https://m" },
      { engine: "google", url: "https://b" },
    ];
    expect(groupSources(sources).map((g) => [g.label, g.items.length])).toEqual([
      ["Google Search", 2],
      ["Google Maps", 1],
    ]);
  });
});
