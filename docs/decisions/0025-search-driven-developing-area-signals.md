# 0025. Search-driven developing-area signals, display only (after gscode007's branch)

- **Status:** Accepted
- **Date:** 2026-10-07
- **Builds on:** [0008](0008-code-computes-llm-explains.md), [0016](0016-area-intelligence-and-score.md), [0019](0019-visible-failures-validated-cache-withheld-metrics.md), [0020](0020-local-news-and-frozen-run-areas.md), [0023](0023-competitors-per-locality-read-by-type.md)

## Context

gscode007's branch `feature/search-driven-area-insights` added a new idea on top of their
earlier F-05/F-09 branches: test whether interest in a locality is really growing before calling
it a developing area. Their branch forked 35 commits before main and conflicted in 34 files; it
also carried their own F-05/F-09, which main had replaced (ADRs 0019, 0020), and ADRs 0015-0017
that collide with main's. Its tests passed on its own base (309 backend, 21 frontend) and its
demos replayed. F-05's own Google Trends item had been deferred (P1).

## Decision

- **Port the feature, not the branch**, keeping gscode007's code, tests, recordings and design
  ([SEARCH_DRIVEN_AREA_INSIGHTS.md](../SEARCH_DRIVEN_AREA_INSIGHTS.md)), and their arithmetic
  and thresholds unchanged:
  - public history: two Google Trends TIMESERIES requests per batch of up to five localities
    (`<locality>`, `<locality> rent`), `IN-KA`, five years, the last 104 complete weeks, with the
    newest or partial bucket excluded and every value validated;
  - app history: each run records its localities per profile (`search_intents`); one profile
    counts once per locality per complete UTC week; at least five profiles are needed;
  - last 13 weeks against the previous 13 and against the same 13 weeks a year earlier;
    `rising` needs +15% with 8 sustained weeks; a priority also needs +10% on the year and
    corroboration;
  - DeepSeek reviews and may cite up to three news items as unconfirmed explanations; a quote
    must be a complete title or snippet and match its driver, or the review is withheld.
- **Adapted to main's area intelligence**: observed prices are `AreaIntel.price_growth_pct`
  (one sourced past-12-month change per locality, not per type), and infrastructure
  corroboration counts news DeepSeek labelled positive infrastructure (`classify_news`), dated
  within a year. Reports cover the localities the run enriched.
- **Display only**, like news (ADR 0020) and competitors (ADR 0023): the reports never reach the
  property score, so ranks and recorded explanations do not change. A test feeds a strongly
  rising history and checks the shortlist is identical.
- **Frozen per run** in `run_development`; read with `GET /runs/{id}/development`; deleted with
  the run or the profile, as are the profile's search intents.
- **Recordings**: gscode007's four Trends histories replay unchanged on main (identical request
  parameters, 0 searches); the two DeepSeek reviews were recorded on main.

## Consequences

- A fresh run costs two more searches (Trends, cached like every search).
- Both demos get "no sustained search growth": Whitefield rental interest -17.4% on the quarter,
  Koramangala -28.5%. Neither gets a research priority, which is an honest result.
- App history needs five or more profiles over 26 weeks, so it stays unavailable in a
  single-user local app; it becomes meaningful on the hosted, multi-user site.
- The remaining commits of gscode007's branch (their F-05/F-09) are not merged.
