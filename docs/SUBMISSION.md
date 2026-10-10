# Hackathon Submission

Working notes for the SerpApi India Hackathon 2026 submission. Rules and constraints:
[HACKATHON_BRIEF.md](../HACKATHON_BRIEF.md). Progress: the **Submission** section of
[CHECKLIST.md](../CHECKLIST.md).

**Deadline:** Mon Oct 12, 2026, 23:59 IST (extended from Oct 10; the site's banner, checked
2026-10-10) · Submit as soon as the required fields are in: the timestamp locks on first submit
and edits stay open until the deadline.

## Form fields

| Field | Draft |
|---|---|
| Project name | Realty Intel *(confirm)* |
| Track | Commerce & Market Intelligence (see [Track](#track)) |
| Description | See [Description](#description) below |
| SerpApi usage | See [SerpApi usage](#serpapi-usage) below |
| Repo | *public GitHub URL (the repo is private today)* |
| Demo video | *unlisted URL, < 3 min, tested in incognito* |
| Pre-existing project? | No *(confirm)* |
| AI tools used | Claude Code (development), DeepSeek V4 Pro (in-product LLM) *(confirm full list)* |
| Community source | BangPypers *(confirm)* |
| Team | *names + emails; every member must have contributed* |

### Description

Paste the block below as is. The form field is plain text, limited to 4,000 characters, and asks
"What does the project do, who is it for, and why is it useful?". This text is 3,875 characters.
Its facts were checked against the repo on 2026-10-10 (engines, the 15 localities, the 41-search
cost of a fresh run, 514 backend tests, 31 ADRs, and the rent-as-sale catch in
`test_demo_replay.py`). Recheck the numbers if code changes before submitting.

```text
Realty Intel is a research analyst for property investors, built on live search data. You describe the property you want to buy; it returns a ranked shortlist in which every number has a source, a confidence level and an explanation.

THE PROBLEM
India has no open, structured property database. An investor in Bengaluru checks asking prices on 99acres, MagicBricks and NoBroker, commutes and amenities on Google Maps, locality news and rent levels across many more tabs. The work takes weeks, the results are hard to compare, and the figures that matter most (price per sq ft, rent, yield) are the ones most often wrong in a listing.

WHAT IT DOES
The investor fills a three-step profile: residential or commercial, property type, up to five localities, budget, goal (rental income, appreciation or both), risk appetite and a target return. They can also type a sentence such as "flat in Whitefield under 90 lakh for rental income, near metro" and review the fields it recognises. One pipeline then runs, and the app shows each stage live:

1. Discover: site-filtered Google searches of the three portals, reading the prices their search pages quote, plus housing projects from Google Maps.
2. Verify: DeepSeek fills missing fields only from quoted text and checks each candidate against the profile: what matched, what did not, what is unconfirmed. Hard limits such as budget are enforced in code.
3. Enrich each locality: nearest metro stations, schools and hospitals; the local price level and past-year price change; typical rent; the weekday 9 AM drive to Bengaluru's three big job hubs; recent news labelled by topic; and Google Trends interest as a developing-area signal. Commercial searches add nearby same-category businesses (density, ratings) and service gaps drawn from their low-rated reviews.
4. Rank: rental yield, total return and the match score are computed in code. The AI writes the reason for each pick, and every number it quotes is checked against the computed figures.

The investor gets a ranked shortlist on a map and a property page for each candidate. They can compare 2 to 4 saved properties side by side, get alerts for new matches and price drops, and download a PDF report. Owners can also track holdings and model loan, EMI and exit scenarios.

WHO IT IS FOR
Individual and small-firm real estate investors, residential and commercial. Two demo profiles ship with the repo: an apartment under ₹80 L in Whitefield for rental income, and an office under ₹3 Cr in Koramangala for an IT services business. Bengaluru is the demo market (15 verified localities); nothing in the pipeline is specific to one city.

WHY IT IS USEFUL
- Weeks of tab-juggling become one run, with results the investor can compare.
- Every figure shows its confidence, how it was obtained and a link to the search result it came from. Missing data is shown as missing, never guessed.
- It catches bad listings. Prices far below the sourced locality price level are flagged. In the commercial demo it caught a monthly rent (₹3.6 L for a 4,800 sq ft office) advertised as a sale price, and ranked it last.
- The AI only extracts and explains. Scores and money calculations are done in code, so the AI cannot invent a return.

Search data is the product. Every candidate, price benchmark, rent, commute and competitor comes from SerpApi (Google Search, Maps, Directions, Reviews, News and Trends) through the official Python SDK. One gateway adds a database cache, per-run and monthly search budgets, and record/replay fixtures. A fresh three-locality search costs about 41 searches; repeating it costs 0.

TRY IT
"make setup && make demo" runs the full product offline from recorded searches and AI calls: no API keys needed, no searches spent. Built with FastAPI, React and SQLite, with 514 backend tests, CI on every push, and 31 decision records explaining the design.
```

### Track

**Commerce & Market Intelligence.** The form asks for one track, and SerpApi may move a project
to a better fit before judging. The track brief is "Turn product, price, merchant, finance,
trend, and marketplace results into useful tools for shoppers, sellers, analysts, or small
businesses". Realty Intel turns marketplace listings (portal prices), price benchmarks, Google
Trends and competitor data into a decision tool for investors, which is that brief applied to
property. Travel & Local Discovery was ruled out: it is about deciding where to go, and Maps is
only one of our six engines. Open Innovation is for ideas that fit no other track.

### SerpApi usage

Paste the block below as is. The form field is plain text, limited to 4,000 characters, and asks
"List the APIs, SDKs, tools, or search engines used and explain why the data matters." This
text is 3,788 characters, checked against `engines.py` and the pipeline call sites on 2026-10-10.

```text
SerpApi is Realty Intel's only external data source. India has no open property database, so every candidate property, price benchmark, rent level and locality fact is built from search results fetched for that investor's profile. Without SerpApi there is no shortlist.

SEARCH ENGINES (all called through the official serpapi Python SDK, serpapi.Client)

1. Google Search (google): finds the properties. Site-filtered searches of 99acres, MagicBricks and NoBroker return the portals' search pages, and their snippets quote real prices, sizes and BHK. These are parsed into candidates. The same engine gives the locality price level per sq ft (the benchmark for value scores and the "too good to be true" flag), the past-12-month price change, and typical rents, which drive rental yield and total return. Queries use location "Bengaluru,Karnataka,India", gl=in and google_domain.

2. Google Maps (google_maps): housing projects with GPS, rating and reviews, so candidates sit on the map. It also geocodes each locality centre, finds the nearest metro stations, schools and hospitals (distances feed the area-access part of the ranking score), and for commercial profiles finds same-category businesses within 2 km to measure competition density and ratings.

3. Google Maps Directions (google_maps_directions): the weekday 9 AM drive from each locality to Bengaluru's three big job hubs (ORR/Bellandur, Manyata, Electronic City), with Google's typical-traffic range. For example, Whitefield to Manyata takes 1 hr 10 min, typically 55 min to 1 hr 50 min. Rental demand follows the commute.

4. Google Maps Reviews (google_maps_reviews): for commercial profiles, the lowest-rated reviews (sort_by=ratingLow) of top nearby competitors. DeepSeek draws possible service gaps from them, each one citing the exact review quote.

5. Google News (google_news): recent locality news (metro lines, projects, flooding, legal disputes), labelled by topic and sentiment and screened for risk leads.

6. Google Trends (google_trends): five years of weekly search interest in each locality and in "<locality> rent" (geo IN-KA, up to 5 localities per call). These are growth checks for developing areas and short-term interest projections.

OTHER SERPAPI APIs
- Account API (Client.account()): searches left this month, shown in the app header.
- Locations API: confirmed the canonical location string used in every Google query.
- Provenance: every fact keeps its engine, the result's URL and the SerpApi search ID (search_metadata.id), and the app shows the source link next to the value.

WHY THE DATA MATTERS
Search data decides the result. Discovery results become the candidates. The searched price level decides whether a price is good value or suspicious: in the commercial demo it exposed a monthly rent of ₹3.6 L for a 4,800 sq ft office advertised as a sale price. Searched rents decide whether a property meets the investor's ROI target, and Maps distances shape the area score. News, commutes, Trends and competitor data give the context an investor checks before buying. DeepSeek only extracts and explains; scores and money are computed in code from the search data.

HOW WE USE IT RESPONSIBLY
One gateway is the only module that imports serpapi. It adds a SQLite cache with a 72-hour TTL, a ledger with per-run (45) and monthly search budgets, and record/replay fixtures. All parameters are built in one auditable file (engines.py). Area data is cached per locality for 7 days, so localities shared across profiles are searched once. A fresh three-locality apartment search costs about 41 searches; repeating it costs 0. The repo ships recorded responses from all six engines, so "make demo" runs the whole product with no API key and no searches spent. Portals are linked, never scraped.
```

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
