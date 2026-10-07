# 0024. Locality evidence from the result's own words; flag text that places it elsewhere

- **Status:** Accepted
- **Date:** 2026-10-07
- **Builds on:** [0004](0004-provenance-on-every-field.md), [0011](0011-discovery-from-search-snippets.md), [0013](0013-grounded-verification.md), [0014](0014-area-relative-price-flags.md)

## Context

Until now every candidate's locality was "the locality that was searched for" (method `query`,
confidence 0.5). A portal search page for Whitefield can quote flats in nearby areas, so the
verification prompt treated the locality as search context only and every candidate carried
an "unconfirmed locality" caveat. Yet most results say where they are: in the recorded demos, 18
of 19 Google Maps projects name Whitefield in their address, and several snippet entries name
their locality in their own text. `QualityFlagKind.LOCATION_MISMATCH` existed but nothing
raised it.

Names in results are not always the listing's locality: "Sarjapur Road", "Whitefield Main
Road", "Marathahalli Metro" and "KR Puram Railway" appear as landmarks, and Sarjapur Road
runs through several localities. Spellings vary ("Indira Nagar", "Indiranagara", "K R Puram").

## Decision

- **Matcher** (`app/reference/localities.py`): whole-word matching of the market's names and
  aliases after normalising case and punctuation; spaced initials are joined ("K R" = "KR");
  one-word names of 8 or more letters also match a word with a fuzzy ratio of 90 or more (short
  names would give false hits); a name followed by a landmark word (road, main, metro,
  station, railway, bus, flyover, junction, signal, circle, ...) does not count.
- **Aliases only from observed data**: "Indira Nagar", "Jaya Nagar" and "Sarjapur" were seen in
  the recorded results and are added to `bengaluru.json`.
- **Evidence levels.** The slug is always the searched locality; only the evidence changes:

  | The result's words | Method | Confidence |
  |---|---|---|
  | Its own text (snippet entry) names it | `regex` | 0.8 |
  | Its Maps address names it (projects; entries matched to a project) | `serpapi_field` | 0.9 |
  | Only the page title names it | `regex` | 0.7 |
  | Nothing names it | `query` | 0.5 |
  | Its own text names other localities only | `query` | 0.3 |

  The page title is page-level (a filter), so it is weaker than the entry's own text. The full
  page snippet is not used: it lists many areas.
- **`Listing.named_localities`** keeps the slugs the listing's own text names, so the evidence
  and the flag are decided once, in cleaning.
- **`location_mismatch` flag**, raised in verification when the listing's own text names other
  localities and not the searched one:
  - **high** when none of them is in the profile. It contradicts a hard constraint but is not
    proven, so, like an implausibly cheap price (ADR 0014), the verdict is capped at weak, the
    reason is listed as a mismatch, and the flag penalty applies;
  - **medium** when one of them is in the profile (mislabelled, not out of area). No penalty.
- **Re-recording.** The listing (with its locality evidence) is part of the extraction and
  verification prompts, so both demos' DeepSeek calls were re-recorded with
  `scripts/record_verification.py` (0 SerpApi searches), and the superseded recordings were
  pruned with `make fixtures`.

## Consequences

- Most demo candidates now show a confirmed locality; the AI's "query-derived locality" caveat
  remains only where nothing in the result names it.
- Neither demo has a listing whose text places it elsewhere, so the flag is covered by unit
  tests; it matters for live searches across several localities.
- Area news matching (`mentions_locality`, ADR 0020) is unchanged; moving it onto this
  matcher would change recorded news results and is left for later.
