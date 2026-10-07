# 0022. Map positions only from SerpApi; unplaced candidates grouped at the locality centre

- **Status:** Accepted
- **Date:** 2026-10-07
- **Builds on:** [0004](0004-provenance-on-every-field.md), [0011](0011-discovery-from-search-snippets.md), [0016](0016-area-intelligence-and-score.md)

## Context

F-19 puts a run's candidates on a map. Only some candidates have a position: Google Maps projects
carry GPS, and a priced snippet entry gets one only when matched to a project by name (F-02).
In the recorded demos, 19 of 28 residential candidates have GPS (all of them Maps projects; no
entry was matched) and none of the 6 commercial ones do. Ranked snippet entries, often the top of
the shortlist, have no position at all.

Spreading position-less candidates around the locality centre (jitter), or geocoding each
snippet's text, would draw points that look like addresses but are not.

## Decision

- A candidate is drawn at **its own GPS** when its `location` has one.
- Otherwise it joins **one dashed marker at its locality's geocoded centre** (F-05's
  `AreaIntel.center`), whose popup lists every candidate in it and says no position was quoted.
  It is never drawn at an invented point, and no extra search is spent to place it.
- A candidate whose locality has no centre yet (enrichment not finished, or the centre lookup
  failed) is **counted under the map**, not drawn.
- Ranked candidates are numbered by rank and coloured by score band (70+, 50–69, under 50);
  the rest are coloured by status (checked, not checked, filtered out). Filtered-out candidates
  are an overlay that is off by default on the run page.
- The area's metro stations, schools and hospitals are an overlay. It is on by default when no
  candidate has its own position (the commercial demo), so the map still shows context.
- The map is computed in the browser from existing run endpoints (`listings`, `verifications`,
  `recommendations`, `areas`) and the property detail response; there is no map endpoint.
- Tiles are OpenStreetMap's, with attribution.

## Consequences

- The commercial demo's map is one dashed marker plus amenities until F-06 adds competitor
  places with GPS.
- If F-02 later matches more entries to projects, they move to exact markers with no map change.
- The competitor layer on the detail page belongs to F-06.
