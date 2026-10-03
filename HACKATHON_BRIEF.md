# SerpApi India Hackathon 2026 — Working Brief

Sources: https://serpapi.com/indiahackathon (= https://serpapi.github.io/serpapi-india-hackathon-2026/),
its `rules.html`, `terms.html`, `submit.html`, and the launch blog post. Rules > marketing copy;
Terms > Rules where they conflict.

## Hard constraints

| Item | Value |
|---|---|
| Window | Sep 1, 2026 00:00 IST → **Oct 10, 2026 23:59 IST** |
| Eligibility | 18+ **resident in India** (blog says "citizens"; Rules say residency — Rules govern) |
| Team | 1–5 people (lead + up to 4). Every member must have actually contributed. |
| Stack | Any language / framework. No restrictions. |
| Existing projects | Allowed, **must be disclosed**, submitted version must show meaningful SerpApi usage |
| AI tools | Allowed, must be listed, **explicitly does not affect judging** |
| Active projects per account | **3** (drafts + submitted combined) |
| Free SerpApi tier | 250 searches/month |

## The five judging criteria (unweighted, considered together)

1. **Idea strength** — is it built on a clear, compelling insight?
2. **Originality** — distinctive, or thoughtfully recombined?
3. **Technical complexity** — meaningful engineering effort, implementation depth, quality?
4. **Usefulness** — real practical value to the intended user?
5. **Meaningful SerpApi usage** — does the project *depend* on search data to function?

No fixed percentage weights. Judges may review "the repository history, code, documentation,
demonstration, submission record, and other publicly available project information," and may
request clarification or a live functionality check. SerpApi's decisions are final, no appeal.

**Gate, not a criterion:** "Meaningful SerpApi usage" is also a validity requirement. An isolated
or cosmetic API call added just to qualify is explicitly called out as insufficient, judged at
SerpApi's sole discretion.

## Judges — all SerpApi staff, mostly developer advocates

- Adarsh Divakaran — Python Developer Advocate (also the hackathon contact, adarsh@serpapi.com)
- Tomas Murua — Developer Advocate
- Josef Strzibny — Ruby Developer Advocate
- Pranav Kafle — Customer Success Engineer

Implication: this panel reads code and READMEs for a living. Repo hygiene, a setup path that
actually works, and idiomatic use of their SDKs are judged in practice even though they aren't
named criteria.

## Six tracks (pick exactly one; SerpApi may reclassify)

1. **AI Agents** — plan/search/compare/act on current info. Recommends `serpapi-search-tools` (Python) or SerpApi MCP.
2. **Open-Source Integrations** — a plugin/provider/connector/SDK adapter bringing SerpApi to a new OSS package, agent framework, MCP client, or dev tool.
3. **Travel & Local Discovery** — flights, hotels, maps, places, reviews, destinations.
4. **Commerce & Market Intelligence** — product, price, merchant, finance, trend, marketplace.
5. **Knowledge & Public Interest** — education, research, jobs, news literacy, accessibility, civic info, patents.
6. **Open Innovation** — wildcard; combine engines/SDKs into something original and useful.

## Prizes — ₹2,10,000 cash + 120,000 credits competitive, ₹3L+ total value

| Award | Cash | Credits |
|---|---|---|
| 1st | ₹1,00,000 | 15,000 |
| 2nd | ₹40,000 | 10,000 |
| 3rd | ₹20,000 | 10,000 |
| Best in Track (×6) | — | 10,000 |
| Best from Community (×5 partners) | ₹10,000 each | 5,000 |
| Every valid submission | — | 1,000 |

**One competitive award per project.** Assignment order: overall 1/2/3 first → then best-in-track
to the next highest-ranked eligible projects → then community awards. Participation credits stack.

Partner communities (each has its own ₹10,000 award): BangPypers (Bengaluru), HydPy (Hyderabad),
TriPy (Thiruvananthapuram), AI Geeks Chennai, PyDelhi.

## Submission checklist

- Sign in with **GitHub** on the submission dashboard. Drafts never auto-submit — must click "Submit project".
- **Public GitHub repo**: code, documentation, setup/usage instructions good enough for a stranger to run it.
- **Demo video < 3 min**: screen recording of the project **running locally**, showing core functionality.
  Public or unlisted. Narration optional. May be sped up. **Production quality does not affect judging.**
  Must open in an incognito window without requesting access.
- **Project description**: what it does, who it helps, why it's useful.
- **SerpApi usage explanation**: name the specific APIs / engines / SDKs / MCP features and their role.
- **Lead details**: name, email, mobile, occupation, years of experience (last two = internal analytics only).
- **Per teammate**: name + email.
- **Disclosures**: did the project pre-exist; which AI tools were used; how you heard about the hackathon
  (the "community source" field — this is what routes you to a partner-community award).
- Accept Rules + Terms; tick the box confirming you tested links in incognito.
- Draft minimum to save: project name, description, community source.
- Submission timestamp is set on first submit and is *not* reset by later edits — so submit early and keep editing.

## IP / legal worth knowing

- You keep ownership of your project. No transfer to SerpApi.
- You grant SerpApi a perpetual, irrevocable, sublicensable license to run, evaluate, display, excerpt
  and promote the submission, including your name/likeness/voice from the demo video.
- Nothing is confidential. **No API keys, secrets, or personal data in the public repo** — exposure is a
  listed disqualification ground.
- SerpApi may independently build similar functionality; submitting creates no exclusivity.

## Landscape — BuiltWithSerpApi gallery (179 public projects, theme counts)

Saturated: shopping/price-compare 30 · maps/local-business 23 · travel/flights/hotels 20 ·
fact-checking 18 · compliance & human-approval agents 17 · lead-gen/CRM 14 · SEO/rank-tracking 12 ·
n8n workflows 12 · research-brief/Scholar 11 · Lens/reverse-image/OSINT 11 · beauty/try-on 11 ·
jobs/resume 10.

Thin: open-source integrations & MCP 4 · accessibility 3 · patents 2 · education/admissions 6 ·
news monitoring 7 · civic/public-interest 9.

## Strategic reads

1. **Three active projects per account.** Best-in-track is awarded per track and community awards per
   community, so 2–3 entries across *different* tracks multiply shots at an award without competing
   with each other.
2. **Open-Source Integrations is the least contested track** (4 of 179 gallery projects) and it is the
   track a devrel panel is most motivated to see filled. Lowest-competition path to a Best-in-Track.
3. **The community-source field is free money.** Five ₹10,000 awards, each contested only within one
   community. Answer it deliberately.
4. **"Technical complexity" is an explicit criterion**, which prices out thin Streamlit wrappers —
   the gallery is full of them. Depth is a differentiator here, not just polish.
5. **The demo must show the project running locally**, so a deployed-URL-only demo fails the standard.
   Budget time for a clean local-run path.
6. **250 searches/month on free tier.** Cache aggressively and ship fixtures/demo mode, both to survive
   development and so judges can run it without burning their own quota.
