# 0016. Area intelligence from five searches; the area score measures amenity access only

- **Status:** Accepted
- **Date:** 2026-10-06
- **Amends:** [0015](0015-composite-ranking.md) (fills its `area` component)

## Context

F-04 reserved an `area` component in the composite score. The product owner scoped F-05 to the
locality centre, nearby amenities, past-12-month price growth and an AI summary. News and Google
Trends demand are deferred. The recorded price-level searches contain no year-on-year figure
(Whitefield has none; Koramangala has a bare "1%" with no period), so growth needs its own
search. Price growth is also the measure for F-09's appreciation ROI (ADR 0010).

## Decision

- **Five searches per new locality**, cached in `area_intel` for `AREA_INTEL_TTL_HOURS` (7 days)
  and shared by every listing there (ADR 0006):
  1. a Google Maps geocode, rejected if outside the market's bounding box;
  2. "metro station", "school" and "hospital" near the centre;
  3. a Google search for the locality's price trend year on year.
- **Amenities** are kept by Maps place type, not by name: a Whitefield metro station is named
  "Sri Sathya Sai Hospital". Preschools, language and coaching schools are excluded. Distances
  are computed in code (haversine), keeping the 5 nearest per category within 5 km.
- **Growth:** DeepSeek lite picks one snippet's one-year change. Code checks that the span is in
  the snippet, has the signed number with "%", has a one-year period, has no rent or yield
  wording, and that the sign matches the wording. A missing figure is null, never zero, and it
  is labelled past data.
- **Summary:** DeepSeek lite writes it from figures keyed by category (`metro_station_1`). The
  F-04 number check (`pipeline/grounding.py`) applies, with a summary written by code as the
  fallback.
- **The area score is access only:** metro 100 at 0.5 km or less down to 0 at 4 km (0 when none
  is found within 5 km), plus schools and hospitals found within 3 km, full marks at 3 each.
  Weighted 0.5 / 0.25 / 0.25. It is measured from the listing's own coordinates when it has
  them (Maps projects), otherwise from the locality centre.
- **Growth is not scored here.** It will feed `roi` for appreciation and balanced goals in F-09,
  so scoring it as `area` too would count it twice.
- Any provider error leaves that part of the area empty; enrichment never fails a run.

## Consequences

- **Recorded demo results:**
  - Whitefield: metro 1.8 km (Kadugodi Tree Park), 4 schools and 3 hospitals within 3 km,
    growth +29% ("appreciated by approximately 29% in the last one year").
  - Koramangala: metro 2.7 km (Bommanahalli, BTM Layout), 1 school and 4 hospitals, growth
    +26.9% ("+26.9% in 1 year").
- **Counts are a sample.** Each category is one Maps query of 20 results, ordered by relevance
  rather than distance, so Koramangala's single school is surely an undercount. The UI says so.
- **Listings without coordinates score the same.** Snippet entries in one locality all share
  the centre's access, so `area` only separates Maps projects, or candidates in different
  localities.
- **Labels need context.** The first summary run showed the number check cannot catch a
  mislabelled real figure. It called the metro station a hospital until the inputs were keyed by
  category; a regression is guarded by the demo replay test.
- **Cost:** a new locality costs 5 searches and 2 lite calls per TTL. The SerpApi cost model in
  SERPAPI_USAGE.md is updated.
