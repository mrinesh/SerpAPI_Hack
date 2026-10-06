# Realty Intel *(working name)*

**Real estate investor intelligence, built on live search data.** Tell it what you want to buy,
and it finds listings through SerpApi, has DeepSeek check each one against your criteria, adds area
intelligence (and competitor data for commercial property), and returns a ranked shortlist with
a reason and a source link for every number.

> **Status: framework stage.** The architecture, schemas, API surface and UI shell are in place;
> features are being built now. Progress lives in **[CHECKLIST.md](CHECKLIST.md)**.
> Discovery, DeepSeek verification and area intelligence are implemented and recorded for both
> offline demos. Investment metrics, ranking and property details remain pending. See
> [the F-05 implementation/debugging guide](docs/F05_AREA_INTELLIGENCE.md).
>
> Built for the SerpApi India Hackathon 2026 · Track: **Commerce & Market Intelligence** ·
> Demo market: **Bengaluru**

## Why

Investors research across many tabs: listing portals, maps, news, review sites and market data.
It is slow and inconsistent, and the results are hard to compare. Realty Intel runs one pipeline:

**criteria → search → clean → AI verification → area and competitor enrichment → ranked shortlist**

## What it does

| | |
|---|---|
| **Discovery** | Site-filtered Google searches of 99acres, MagicBricks and NoBroker, reading the prices their search pages quote, plus housing projects from Google Maps |
| **AI verification** | DeepSeek V4 Pro extracts structured fields, scores each listing against your profile, and flags mismatches and missing data |
| **Area intelligence** | Amenities (Maps), news and infrastructure (News), price level (Search), rental demand (Trends), cached per locality |
| **Competitor analysis** | For commercial property: same-category businesses nearby, ratings, review volume, density, market gaps |
| **Investment metrics** | Price per sq ft vs area average, rental yield, price growth and total return, checked against your ROI target |
| **Trust** | Every data point shows its source and the model's confidence |

## SerpApi usage

Discovery runs on `google` (site-filtered portal searches) and `google_maps` (housing projects)
through the official `serpapi` Python SDK; `google_news`, `google_trends` and
`google_maps_reviews` come with area intelligence and competitor analysis. The free Account,
Locations and Search Archive APIs are used too. Without search data there is no product. Details,
what we measured, and the cost model: **[docs/SERPAPI_USAGE.md](docs/SERPAPI_USAGE.md)**.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/), Node.js 22 or 24 LTS (20.19+ works) and make.

```bash
git clone <repo-url> && cd SerpAPI_Hack
make setup    # installs backend + frontend, creates .env
make demo     # replay mode: no API keys needed, no searches spent
```

- App: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>

To run against live data, put `SERPAPI_API_KEY` and `DEEPSEEK_API_KEY` in `.env`, set
`SERPAPI_MODE=live` and `LLM_MODE=live`, then `make dev`. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#provider-modes).

## Architecture

```
React (Vite · TS · Tailwind · Leaflet)  ──/api──▶  FastAPI
                                                    ├─ services
                                                    ├─ pipeline: plan → fetch → clean → verify → enrich → rank
                                                    ├─ SerpApi gateway (cache · budget · record/replay) ──▶ SerpApi
                                                    ├─ LLM provider (record/replay) ──▶ DeepSeek
                                                    └─ SQLite
```

Full picture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · stage detail:
[docs/PIPELINE.md](docs/PIPELINE.md) · decisions: [docs/decisions/](docs/decisions/).

## Repository layout

```
backend/      FastAPI app, pipeline, SerpApi/DeepSeek integrations, tests, recorded fixtures
frontend/     React app5
docs/         product, architecture, pipeline, SerpApi usage, API, data model, ADRs
CHECKLIST.md  feature tracker: what's done, what's pending
CHANGELOG.md  dated log of changes
```

## Documentation

Start at **[docs/README.md](docs/README.md)**.

## AI disclosure

Developed with the help of Claude Code. DeepSeek is used inside the product for extraction,
verification and explanations.
