# 0002. SerpApi is the only listing source; no portal scraping

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
Indian listing portals (99acres, MagicBricks, Housing.com, NoBroker) have terms that restrict
automated access, and they render listings with heavy client-side code. SerpApi returns Google's
view of those pages (title, snippet, rich snippets, links) through a supported API.

## Decision
Listings are discovered and described only from SerpApi results. The app links to the portal page
for detail and never fetches portal pages itself. Missing fields are shown as missing.

## Consequences
- Coverage is limited to what search results expose; spike S-01 measures it before the design
  is locked.
- Search results include aggregate pages ("312 flats in Whitefield"), so cleaning must classify
  result kinds; aggregate pages become locality price signals instead of properties.
- The SerpApi dependence is real, not cosmetic, which is also the hackathon's validity gate.
