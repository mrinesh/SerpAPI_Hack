import type { Listing, Verification } from "../../api/types";

/** Rejects belong only in the filtered view; pending checks stay in their discovery view. */
export function groupCandidates(listings: Listing[], verifications: Verification[]) {
  const rejected = new Set(
    verifications.filter((check) => check.verdict === "reject").map((check) => check.listing_id),
  );
  return {
    priced: listings.filter((listing) => !rejected.has(listing.id) && listing.kind === "snippet_entry"),
    projects: listings.filter((listing) => !rejected.has(listing.id) && listing.kind === "project"),
    filtered: listings.filter((listing) => rejected.has(listing.id)),
  };
}
