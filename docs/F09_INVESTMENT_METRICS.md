# F-09: investment metrics

## What difference this makes

Before F-09, the results answered **does this property match my criteria, and what is nearby?**
They showed sale snippets, relevance checks, amenities, news and area price benchmarks. You still
had to calculate the investment comparison yourself.

Now each candidate has an **Investment comparison** panel. It shows price per sq ft, price
above/below the same-type locality benchmark, sourced asking-rent estimates where available,
estimated gross rental yield, reported past annual growth or your own growth assumption,
illustrative total return, and the selected goal's target comparison. Every figure has expandable
evidence, source links, confidence and missing-data reasons.

This is useful for comparing an asking price with local evidence and finding which candidates
need more financial information. It also prevents misleading comparisons: a rent mistaken for
a cheap sale cannot create an enormous yield, and an unknown component cannot silently become zero.

## Real replay examples

The committed demo searches were recorded on 2026-10-06; values below describe those recordings.

| Demo | Added comparison | Practical difference |
|---|---|---|
| Whitefield apartment | Sowparnika Columns: INR 60 lakh / 733 sq ft = about INR 8,185.54/sq ft, about 32.63% below the INR 12,150 same-type benchmark | Compare the quote with local sale-price evidence; a lower rate alone is not a valuation or purchase recommendation |
| Whitefield annual change | Search evidence says flat rates changed by 10.8% in the last 1 year | A sourced past-growth input is now available; it is not a forecast, and it cannot replace missing rent for a rental-income goal |
| Koramangala office, INR 1.15 crore / 820 sq ft | Local quote INR 1.7 lakh/month for 1,800 sq ft gives an indicative INR 77,444/month for this size; estimated gross yield about 8.08%, above the 4% rental target | You can compare the gross income estimate to your selected target without manual arithmetic; lease/area/fit-out differences still matter |
| Koramangala suspicious INR 3.6 lakh "sale" | Yield and ROI verdict withheld, with an implausibly-cheap-price explanation | F-12's price warning now also protects financial calculations |

Whitefield has 28 saved metric snapshots and reported growth for 12 checked, non-rejected
candidates. Its eligible housing snippets do not provide comparable monthly rent evidence, so
rental yield and the rental target assessment remain unavailable. Koramangala has six snapshots,
two rent/yield/target assessments, and no supported annual office growth. Its total return stays
unavailable without growth. Missing data is part of the result, not an offline-replay error.

## How the implementation works

1. **F-03 finishes first.** Enrichment uses the grounded, extracted listings, not the earlier
   cleaning objects. This matters when DeepSeek added size, BHK or price evidence.
2. **F-05 area snapshots provide sale benchmarks.** F-09 reuses `price_levels` for the candidate's
   property type. No duplicate sale-benchmark search is needed.
3. **`InvestmentInputs` gathers financial inputs.** Rent requests share a locality/type/BHK
   cohort; an unknown-layout candidate with size uses only a per-area rent quote. Commercial
   unit rent with a quoted area can be converted to a rate. Growth shares locality/type keys.
   Searches use the existing SerpApi gateway and DeepSeek lite tier, with cache/replay and budgets.
4. **Code validates evidence.** Rent candidates are screened for currency, monthly units,
   positive amounts, ranges, deposits and BHK/type. DeepSeek selects a complete snippet; code
   requires exact evidence, locality and type. Growth needs an explicit annual change and
   direction. Quarterly trends and invented/partial numbers are rejected.
5. **`compute_metrics` does arithmetic.** It performs no I/O, propagates provenance, caps confidence
   at the weakest input, and compares unrounded values. The investor's growth override wins over
   search evidence, including 0% or negative growth, and is labelled as an assumption.
6. **Save progressively.** Each result is appended to the existing `run_results` JSON and committed.
   Prior results survive a later failure. Profile edits and shared-listing refreshes do not rewrite
   the frozen target, sources or calculations.
7. **The frontend polls metric progress.** The candidate cards show the comparison without waiting
   for future F-04 ranking or F-07 property details.

| Field | Formula or input |
|---|---|
| `price_per_sqft` | sale price / size; direct sourced rate when size is unavailable |
| `area_avg_price_per_sqft` | existing same-locality/type sale benchmark |
| `price_vs_area_pct` | (candidate rate / benchmark - 1) * 100 |
| `est_monthly_rent_inr` | comparable BHK monthly quote, or sourced rent rate * unit size |
| `rental_yield_pct` | monthly asking-rent estimate * 12 / sale price * 100, **before costs** |
| `price_growth_pct` | profile growth assumption if supplied; otherwise sourced past annual change |
| `total_return_pct` | gross rental yield + growth; **illustrative**, not a forecast or realised return |
| `meets_target_roi` | rental income -> yield, appreciation -> growth, balanced -> total; compare >= target |

No net yield or cap rate is calculated because vacancy, maintenance, taxes and other operating
costs are not sourced. Same-type locality rates are benchmarks, not property-specific valuations.

## API and storage

`GET /api/runs/{run_id}/metrics` returns:

```json
[
  {
    "listing_id": "candidate-id",
    "metrics": {
      "rental_yield_pct": {
        "value": 8.081113043478261,
        "confidence": 0.6,
        "method": "computed",
        "sources": [],
        "note": "Illustrative shape only; real responses include input evidence and source links"
      },
      "roi_measure": "rental_yield",
      "target_roi_pct": 4,
      "meets_target_roi": true
    }
  }
]
```

The JSON above is a shortened shape example, not a complete payload or fixture. Real responses
include all seven sourced figures and `assessment_note`. A known run before enrichment returns
`[]`; an active/failed run returns whatever is committed; an unknown/deleted run returns 404.
GET never spends credits. `enrich` counts add `metrics`, `roi_assessed`, `investment_warnings`.
No database reset or migration is needed. Older snapshots without metrics remain readable.

## Run and test it

From the repository root:

```bash
make demo
```

Open <http://localhost:5173>, choose a recorded demo profile, start a **new** run, and expand
Investment comparison evidence on a candidate. Old completed runs are deliberately not backfilled.
The Koramangala office demo shows two gross-yield comparisons; Whitefield shows benchmark/growth
comparisons and truthful rent gaps. Ranking still reports pending because it belongs to F-04.

From `backend`:

```bash
uv run pytest tests/unit/test_metrics.py tests/unit/test_investment_inputs.py tests/integration/test_metrics_api.py
uv run python scripts/record_investment_metrics.py --profile both
```

The recording command sets both provider modes to `record` in its own process, uses a disposable
SQLite database, reuses existing discovery/verification/area/search fixtures, and only writes new
fixtures. It needs the provider keys already configured in `.env` when a live call is necessary.
The four F-09 demo searches and three current DeepSeek selections are committed for offline use.

## Diagnose unavailable figures

| Symptom | Meaning / action |
|---|---|
| Unknown target assessment | Selected goal's figure is missing, or candidate price/relevance is unsafe. Expand evidence and the assessment reason |
| No rent for known housing price | A whole-unit quote needs the exact BHK; unknown BHK needs size and an explicit monthly per-area quote. Do not infer layout from size |
| Commercial total unavailable | Annual office price growth was not sourced. Gross yield can still be shown independently |
| Growth is 0% | A real zero override is supported; it is not treated as missing |
| `replay_miss` in an evidence note | A search or exact task/model/prompt/schema has no recording. Run the recording script; replay will never silently call a live API |
| `search_budget_exceeded` / provider failure | Already saved data remains readable. Financial input notes preserve the error and enrichment counts track provider warnings |
| Implausibly cheap / range quote | Confirm the final sale price before an ROI assessment can be made |
| Existing run has no comparison panel | Create a new run; old snapshots are intentionally unchanged |

The F-03 statement that ROI was unverified **at the verification stage** still describes that stage.
The later F-09 panel provides the financial assessment separately; it does not rewrite relevance
scores or decide F-04 ranking.

See [ADR 0016](decisions/0016-grounded-investment-metrics.md) for tradeoffs and
[ADR 0010](decisions/0010-roi-definition.md) for the goal mapping.
