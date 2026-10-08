# Hackathon Submission

Working notes for the SerpApi India Hackathon 2026 submission. Rules and constraints:
[HACKATHON_BRIEF.md](../HACKATHON_BRIEF.md). Progress: the **Submission** section of
[CHECKLIST.md](../CHECKLIST.md).

**Deadline:** Sat Oct 10, 2026, 23:59 IST · **Plan:** first submit by Thu Oct 8 (the timestamp
locks on first submit; edits stay open).

## Form fields

| Field | Draft |
|---|---|
| Project name | Realty Intel *(confirm)* |
| Track | Commerce & Market Intelligence |
| Description | See [Description](#description) below |
| SerpApi usage | See [SerpApi usage](#serpapi-usage) below |
| Repo | *public GitHub URL (the repo is private today)* |
| Demo video | *unlisted URL, < 3 min, tested in incognito* |
| Pre-existing project? | No *(confirm)* |
| AI tools used | Claude Code (development), DeepSeek V4 Pro (in-product LLM) *(confirm full list)* |
| Community source | BangPypers *(confirm)* |
| Team | *names + emails; every member must have contributed* |

### Description

Realty Intel helps property investors in Bengaluru go from "what I want to buy" to a short,
explained list of candidates, without juggling portals, maps and news tabs. The investor
describes a purchase: residential or commercial, property type, up to five localities, budget,
goal (rental income, appreciation or both), risk appetite and a target return. One pipeline
then searches 99acres, MagicBricks and NoBroker through Google and housing projects through
Google Maps, reads the prices those pages quote, and has DeepSeek check each candidate against
the profile, filling gaps only from quoted text. For every locality it adds nearby metro
stations, schools and hospitals, the local price level, past-year price change, typical rent and
recent news; for commercial searches, the same-category businesses nearby. Yield, total return
and the ranking score are computed in code; the AI writes the reasons and every number it
quotes is checked. Every figure carries its confidence and a link to the search result it came
from, and implausible listings are flagged (it caught a monthly rent advertised as a sale
price). It runs fully offline from recorded searches, so anyone can try it with no API keys.

### SerpApi usage

SerpApi is the only data source, used through the official `serpapi` Python SDK behind one
gateway with a database cache, a per-run and monthly search budget, and record/replay fixtures.

- **Google Search (`google`)**: site-filtered searches of 99acres, MagicBricks and NoBroker,
  whose search-page snippets quote prices; the locality price level per sq ft, used to flag
  implausible prices; the past 12-month price change; and rent levels for yield.
- **Google Maps (`google_maps`)**: housing projects with GPS, ratings and reviews; geocoding
  each locality; the nearest metro stations, schools and hospitals; and, for commercial
  profiles, same-category businesses within 2 km for density and ratings.
- **Google Maps Directions (`google_maps_directions`)**: the weekday 9 AM drive from each
  locality to Bengaluru's three big job hubs (ORR/Bellandur, Manyata, Electronic City), with
  Google's typical-traffic range, e.g. Whitefield → Manyata 1 hr 10 min (typically 55 min to
  1 hr 50 min). Rental demand follows the commute.
- **Google News (`google_news`)**: recent locality news, labelled by topic and sentiment.
- **Google Trends (`google_trends`)**: weekly search interest in each locality and its rentals,
  for developing-area signals.
- **Account API** for searches left (shown in the app) and **Locations API** for the `location`
  parameter.

A fresh search of one locality costs about 15 searches; repeats within the cache window cost 0.

## Demo video plan (< 3 min, running locally)

Built features only; `make demo` seeds both profiles, so no keys are needed while recording.

| Time | Show |
|---|---|
| 0:00–0:15 | Problem: an investor juggling portals, maps and news tabs |
| 0:15–0:40 | The profile wizard on "Whitefield demo": what, where, money, and the suggested target ROI |
| 0:40–1:05 | Find properties: live pipeline stages with searches, cache hits, AI checks, enrichment |
| 1:05–1:40 | Map and ranked shortlist: score, reason, yield vs target; the "Filtered out" tab with reasons |
| 1:40–2:15 | Open the top property: facts with confidence and sources, relevance check, metrics, map, "Where this came from" |
| 2:15–2:45 | "Koramangala office demo": the flagged rent-as-sale price, IT services cluster card and map layer |
| 2:45–3:00 | SerpApi engines used, and that it runs offline from recordings |

## Pre-submit checks
- [x] Fresh clone in another directory: `make setup && make demo` works with no `.env`; both demo
      profiles are seeded and run with 0 searches (2026-10-07, branch `submission`)
- [x] No secrets in the repo or its history: neither configured key appears in any commit on any
      branch, `.env` was never committed, the 64-hex strings are cache keys (2026-10-07)
- [x] README quickstart matches reality, with screenshots
- [ ] Video and repo links open in an incognito window
