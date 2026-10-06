import { describe, expect, it } from "vitest";
import type { Listing, Verification } from "../../api/types";
import { groupCandidates } from "./groupCandidates";

describe("candidate views", () => {
  it("keeps rejects in the filtered view and pending checks in discovery views", () => {
    const listings = [
      { id: "accepted", kind: "snippet_entry" },
      { id: "rejected", kind: "snippet_entry" },
      { id: "project", kind: "project" },
      { id: "pending", kind: "snippet_entry" },
      { id: "rejected-project", kind: "project" },
    ] as Listing[];
    const verifications = [
      { listing_id: "accepted", verdict: "partial" },
      { listing_id: "rejected", verdict: "reject" },
      { listing_id: "rejected-project", verdict: "reject" },
    ] as Verification[];
    const views = groupCandidates(listings, verifications);
    expect(views.priced.map((item) => item.id)).toEqual(["accepted", "pending"]);
    expect(views.projects.map((item) => item.id)).toEqual(["project"]);
    expect(views.filtered.map((item) => item.id)).toEqual(["rejected", "rejected-project"]);
    expect(Object.values(views).flat()).toHaveLength(listings.length);
  });
});
