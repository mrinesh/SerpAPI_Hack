# 0019. Visible area failures, a validated area cache, and withheld metrics

- **Status:** Accepted
- **Date:** 2026-10-07
- **Amends:** [0016](0016-area-intelligence-and-score.md), [0017](0017-investment-metrics-and-roi-score.md)
- **Credit:** adapted from gscode007's parallel `f-05` / `f-09` branches (their ADRs 0015 and
  0016 on those branches). The ideas were ported onto `main`; the code was not merged.

## Context

A comparison with the teammate's parallel F-05 / F-09 work showed three weaknesses on `main`:

- **Failures were silent.** Provider errors in area enrichment and rent lookups returned `None`,
  so "no metro station nearby" and "the metro search failed" looked identical. A half-empty area
  was then cached for 7 days.
- **The cache was trusted blindly.** A cached area was reused whatever code version or provider
  mode had built it, and an unreadable row could break a run.
- **Metrics used unconfirmed prices.** A starting price or a price range still produced a yield
  and a target verdict, and verdicts read the profile's current target, so editing a profile
  changed old results.

## Decision

- **Each area section** (`centre`, `metro`, `school`, `hospital`, `growth`, `summary`,
  `rent:<type>`) records a status:
  - `ok`: data found;
  - `empty`: the search worked but found nothing (a valid result);
  - `failed`: with an `AreaIssue {section, provider, code, message}` in `warnings` and a log
    warning.
- **A failed section** makes the area expire at its assembly time, so the next run retries. The
  area is still saved, so it can be inspected. A failed rent lookup doesn't expire the area,
  because missing rent is retried on every run anyway.
- **Warnings are shown** in the enrich stage counts and message, and in the area panel. The run
  never fails because of one.
- **A cached area is reused** only if it parses, hasn't expired, and matches the current
  `AREA_SCHEMA_VERSION` and provider modes. Otherwise it is rebuilt, which is free in replay
  and record mode. The read-only `GET /api/areas/{key}` returns a clear `area_cache_read` error
  for a corrupt row and never repairs it silently.
- **Withheld metrics:** for a price flagged too good to be true, or a starting or range price
  (`quality.price_is_bound`, now shared with verification), the price-dependent figures are
  withheld: price vs area, rental yield, total return, and a target verdict that depends on
  them. Each note says why. Growth, and an appreciation verdict, which depends only on growth,
  are kept.
- `InvestmentMetrics` now stores `target_roi_pct`, frozen at computation, and an
  `assessment_note` explaining a missing verdict.

## Consequences

- **The recorded demos are unchanged:** the same ranks, scores, reasons, yields and verdicts,
  checked against a snapshot taken before the change. No re-recording was needed.
- **Live runs never pin a partial area for a week:** they retry it, at the cost of those searches
  being attempted again. The gateway cache makes repeats free within its own TTL.
- **Not yet ported from the teammate's branches:** news with classification, and frozen per-run
  area snapshots.
