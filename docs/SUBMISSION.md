# Hackathon Submission

Working notes for the SerpApi India Hackathon 2026 submission. Rules and constraints:
[HACKATHON_BRIEF.md](../HACKATHON_BRIEF.md). Progress: the **Submission** section of
[CHECKLIST.md](../CHECKLIST.md).

**Deadline:** Sat Oct 10, 2026, 23:59 IST · **Plan:** first submit by Thu Oct 8 (the timestamp
locks on first submit; edits stay open).

## Form fields

| Field | Draft |
|---|---|
| Project name | *TBD (working name: Realty Intel)* |
| Track | Commerce & Market Intelligence |
| Description: what, who, why | *Draft from docs/PRODUCT.md once the demo works* |
| SerpApi usage | *Condense docs/SERPAPI_USAGE.md: engines, roles, SDK* |
| Repo | *public GitHub URL* |
| Demo video | *unlisted URL, < 3 min, tested in incognito* |
| Pre-existing project? | No *(confirm)* |
| AI tools used | Claude Code (development), Gemini (in-product LLM) *(confirm full list)* |
| Community source | BangPypers *(confirm)* |
| Team | *names + emails; every member must have contributed* |

## Demo video plan (< 3 min, running locally)

| Time | Show |
|---|---|
| 0:00–0:15 | Problem: an investor juggling portals, maps and news tabs |
| 0:15–0:40 | Create a residential profile (Bengaluru, ₹80 L, 2 BHK, yield target) |
| 0:40–1:10 | Live pipeline progress: searches, cache hits, verify, enrich |
| 1:10–1:50 | Ranked results on the map; open one: reason, yield vs area, amenities, news, source links |
| 1:50–2:30 | Commercial profile (cafe): competitor density, ratings, gaps |
| 2:30–2:50 | Compare 3 properties; alert for a price drop |
| 2:50–3:00 | SerpApi engines used + "runs offline in replay mode" |

## Pre-submit checks
- [ ] Fresh clone on another machine or directory: `make setup && make demo` works
- [ ] No secrets in the repo or its history (`git log -p | grep -i "api_key"` returns nothing real)
- [ ] README quickstart matches reality
- [ ] Video and repo links open in an incognito window
