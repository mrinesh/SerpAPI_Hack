# Product

## One-liner

A research and recommendation platform that finds investable properties, uses AI to check that
each one matches the investor's criteria, and adds area intelligence to every property (plus
competitor data for commercial ones).

## Problem

Investors research across many tabs: listing portals, maps, news, review sites and local market
data. It is slow and inconsistent, and the results are hard to compare.

## Solution

One pipeline: **criteria → shortlist → verified relevance → context → decision.**

## Users

Individual and small-firm real estate investors, residential and commercial. The demo market is
**Bengaluru**; nothing in the pipeline is specific to that city.

| Persona | Wants | Key screens |
|---|---|---|
| Residential yield investor | 2–3 BHK under a budget with good rental yield near transit | Results, detail (yield, amenities, news) |
| Commercial investor | Retail or office space where a given business would do well | Results, detail (competitors, density, gaps) |

## Core value

Faster, better-informed buy decisions with less manual research, and every claim traceable to a
source.

## Features

Numbering matches [CHECKLIST.md](../CHECKLIST.md), which tracks status.

| ID | Feature | What it does | Priority |
|---|---|---|---|
| F-01 | Investor profile | Budget, locations, property type, ROI target, risk appetite, residential or commercial | P0 |
| F-02 | Property discovery | Turns criteria into SerpApi searches across listing portals and Maps | P0 |
| F-03 | AI relevance verification | Gemini extracts structured fields, scores each listing against the profile, flags mismatches and missing data | P0 |
| F-04 | Recommendations | Ranked shortlist with a match score and a plain-language reason for each pick | P0 |
| F-05 | Area intelligence | Per locality: news, infrastructure, amenities, price level, rental demand | P0 |
| F-06 | Competitor analysis | Commercial: same-category businesses nearby, ratings, review volume, density, market gaps | P0 |
| F-07 | Property detail page | Everything above for one property in one view | P0 |
| F-08 | Saved and compare | Side-by-side comparison of 2–4 shortlisted properties | P1 |
| F-09 | Investment metrics | Rental yield, cap rate, price per sq ft vs area average | P0 |
| F-10 | Alerts | New matching listings and price drops | P1 |
| F-11 | Source citations and confidence | Source link and confidence on every data point | P0 |
| F-12 | Listing quality flags | Stale, duplicate and too-good-to-be-true listings | P1 |
| F-19 | Map view | Results and amenities on a map | P0 |
| F-20 | Live pipeline progress | Watch the search → verify → enrich stages run | P0 |
| F-13–F-18, F-21 | Later | Risk scoring, forecasting, PDF report, portfolio tracker, scenario calculator, natural-language search, auth | P2 |

## End-to-end flow

1. **Onboard:** the investor sets criteria.
2. **Query generation:** criteria become search queries.
3. **Fetch:** SerpApi returns listings and local data.
4. **Clean:** deduplicate, normalise, extract fields.
5. **Verify:** AI scores relevance and flags weak or suspicious listings.
6. **Enrich:** area and competitor data are attached to each property.
7. **Present:** ranked recommendations with explanations.
8. **Act:** save, compare, get alerts.

## Risks and how the design answers them

| Risk | Answer |
|---|---|
| **Data coverage:** SerpApi returns search results, not a property database; portals limit what is visible | Spike S-01 measures real coverage before the design is locked. Result-kind classification separates single listings from aggregate pages. Missing fields are shown as missing, never guessed. |
| **Terms of service and cost** | SerpApi is the only data source; portals are linked, not scraped ([ADR 0002](decisions/0002-serpapi-as-the-only-listing-source.md)). Aggressive caching, locality-keyed enrichment and a search budget ([SERPAPI_USAGE.md](SERPAPI_USAGE.md)). |
| **AI accuracy** | Regex first, LLM only for gaps; every field keeps its source text and confidence ([ADR 0004](decisions/0004-provenance-on-every-field.md)); scores and money maths are computed in code ([ADR 0008](decisions/0008-code-computes-llm-explains.md)). |

## Hackathon framing

- **Track:** Commerce & Market Intelligence: property is a marketplace, and the platform turns
  search data into price, demand and competition intelligence.
- **Why search data is load-bearing:** see [SERPAPI_USAGE.md](SERPAPI_USAGE.md#why-the-product-needs-search-data).
