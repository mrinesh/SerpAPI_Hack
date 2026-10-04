# 0011. Discovery reads portal search-page snippets and Google Maps projects

- **Status:** Accepted
- **Date:** 2026-10-04
- **Evidence:** [S-01 data coverage spike](../spikes/S-01-data-coverage.md)

## Context
The design assumed Google would return single-listing pages. In S-01, 0 of 87 portal results
were single listings: Google returns 99acres, MagicBricks and NoBroker search pages. Their
snippets still quote real entries (project, price, price per sq ft, size, BHK, status), about
4–10 prices per query, and there is no `rich_snippet`. For flats, Google Maps returns named
apartment projects with GPS; for commercial it returns agencies and co-working spaces.

## Decision
- A discovered candidate is either a **snippet entry** (one priced entry parsed from a portal
  search page's snippet, linked to that page) or a **project** (a Google Maps housing place,
  merged with snippet entries whose name matches).
- One Google search per locality × property type with the tested template, page 1 only; a query
  with no portal results is retried once without the budget phrase.
- One Google Maps search per locality, only for Apartment / Flat profiles.
- Parsing is deterministic (regex over NFKC-normalised text). The LLM (F-03) only fills gaps later.

## Consequences
- Candidates link to the portal's search page, not to a single unit; the UI must say so.
- Many candidates lack size, BHK or status. Missing values are shown as missing.
- No posted dates exist in this data, so a "stale listing" flag cannot be computed (F-12).
- The cost is predictable: L × T Google searches plus up to L Maps searches per fresh run.
