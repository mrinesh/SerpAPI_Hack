# 0021. Run-scoped property detail, assembled from stored results

- **Status:** Accepted
- **Date:** 2026-10-07
- **Builds on:** [0013](0013-grounded-verification.md), [0020](0020-local-news-and-frozen-run-areas.md)

## Context

F-07 needs one page per property. A listing's id is stable across runs (F-02), but almost
everything an investor reads about it is not: the verification, metrics, score and reason were
judged against one run's profile, and each run keeps its own listing snapshot and area evidence
(ADR 0013, ADR 0020). A detail page keyed by listing id alone would have to choose which run's
judgement to show, or mix runs.

## Decision

- **`GET /properties/{listing_id}?run_id=`** returns the listing as that run saw and judged it:
  snapshot, verification, recommendation (rank, score, breakdown, reason, highlights, risks,
  access), metrics, and the area the run used for the listing's locality (its frozen area, or the
  shared cache for runs older than ADR 0020).
- **Without `run_id`**, the latest run that found the listing is used, so links keyed only by
  listing id (F-08 saved properties, F-10 alerts) still open a page. The UI says so.
- **404** for an unknown listing, an unknown run, or a run that did not find the listing.
- **Stored results only**: no searches, no LLM calls. The page cannot change what the run
  concluded.
- **`price_history`** lists the price quoted in every run that saw the listing, oldest first,
  from `listing_observations`.
- **`sources`** (F-11's "Where this came from") is computed in code: the listing's sources, every
  `Sourced` field's sources on the listing and metrics, and the area figures it uses (price and
  rent level for its type, price growth, amenities), de-duplicated by engine, URL and search id.
  News is display only (ADR 0020) and feeds no figure, so it is not listed.
- The frontend route is `/runs/:runId/properties/:listingId`; `/properties/:listingId` is the
  latest-run form.

## Consequences

- Two runs of different profiles can show different verdicts for one listing; each page is
  consistent with its own run page.
- F-06 competitors and F-19 detail layers attach to this response and page without new routes.
- An unranked or rejected candidate has a page too, with `recommendation` and `metrics` null.
