# Search-driven area insights

Locality research now uses public search history and actual searches inside the app. Code
measures growth and assigns research priorities; DeepSeek reviews the evidence and selects
news-backed possible explanations. This adds observed demand to the existing listing
verification, area news and F-09 financial calculations.

## What difference it makes

Previously, the app showed news and financial inputs without testing whether search interest
was growing. A positive metro announcement could sound attractive without any increase in
property research. Now sustained property-related interest must pass growth checks and have
price/news corroboration before a locality gets a research-priority rank. Missing history,
short spikes, repeated seasonal peaks and broad curiosity cannot establish that conclusion.

The run page shows the weekly histories, percentage changes, source links, data coverage,
and separately labelled causal hypotheses. Investors can inspect the evidence behind the
result. AI cannot change the arithmetic, evidence score, conclusion or rank.

This ranks only the profile's selected localities as priorities for further research.
It does not establish actual development, predict returns or implement F-04 property ranking.

## Both histories

**Public history:** two Google Trends `TIMESERIES` requests batch up to five localities each:
`Whitefield,Koramangala,...` and `Whitefield rent,Koramangala rent,...`. They use the market's
`IN-KA` geography and `today 5-y` window to obtain weekly observations, retaining the last
104 complete weeks. Broad locality interest includes unrelated curiosity; the rental query
is property-related research, without claiming a particular residential/commercial segment.
The newest bucket and explicitly partial buckets are excluded. Query identity, finite values
in 0–100, and contiguous weekly dates are validated. Source search IDs and original provider
retrieval dates survive into the snapshot.

Google describes Trends as sampled, normalized relative interest, rather than absolute counts;
low-volume terms can show zero. Separate requests can have different normalization scales,
so the app compares each query's percentage change, not raw indexes between localities.
See [Google's methodology](https://support.google.com/trends/answer/4365533?hl=en),
[SerpApi parameters](https://serpapi.com/google-trends-api) and
[timeline fields](https://serpapi.com/google-trends-interest-over-time).

**App history:** each started run records its requested canonical locality and profile ID.
Reruns by the same profile count once per locality per complete UTC week. Historical locality
choices survive profile edits. Weekly zeros exist only after collection starts; the first
collection week and current week are excluded. There is no browser-history scraping or
invented backfill. The sample is distinct profiles, not verified individuals, and is shared
across the app's profiles. AI receives aggregated weekly statistics, never profile IDs/names.

New installations need time to build this source: 26 complete weeks and at least five distinct
profiles in those weeks for the quarter comparison, and 65 complete weeks for the annual
comparison used in priority eligibility. Public history can support a result while the app
baseline is still unavailable. Profile deletion cascades to its intents and development
snapshots; other profiles' old frozen reports retain their historical aggregate statistics.

## Growth checks and ranking

Let `recent` be the mean of the latest 13 complete weekly values and `previous` the mean of
the preceding 13. Quarter change is `(recent / previous - 1) * 100`. The annual comparison
uses the same 13-week period 52 weeks earlier (`history[-65:-52]`). A zero baseline produces
an unavailable percentage. Public signals need at least 20 nonzero values in the last 26
weeks to avoid interpreting sparse/low-volume samples as growth.

`rising` requires quarter change at least 15% and at least eight recent weeks above the
previous mean. `falling` requires change at most −15% and at least eight below that mean.
Other usable histories are `steady`. A priority also requires at least 10% annual growth.
This checks recurring seasonal rises; it is not a statistical seasonal-adjustment model.

| Conclusion | Condition | Rank |
|---|---|---|
| `corroborated_growth` | Eligible rental/app search growth plus positive observed annual price change or recent positive infrastructure news | Research priority |
| `interest_only` | Eligible search growth without corroboration, or broad locality growth alone | None |
| `no_sustained_growth` | Usable search history without eligible growth | None |
| `insufficient_data` | No usable history | None |

Infrastructure corroboration counts distinct cited news URLs classified as positive
infrastructure, with publication dates in the last 365 days. Undated, old, future or negative
reports do not count. News can describe proposals and contracts; it does not prove completion.
Investor-entered expected growth is never used as observed price corroboration.

The transparent evidence score uses rental interest 35%, broad interest 15%, app interest
15%, observed prices 15%, infrastructure 20%. Qualified search components are quarter change
clamped to 0–100; other usable search signals contribute zero. Prices use median observed
annual change ×5 clamped to 0–100. Infrastructure uses 50 points per eligible report, capped
at 100. Missing components are omitted and remaining weights renormalized; coverage reports
their total weight. Eligible localities sort by score; exact ties share a rank. These are
research heuristics, not probabilities or a validated forecast.

## AI's role

DeepSeek sees measured histories, code statistics/conclusion, observed price evidence, and
dated news. It returns `consistent`, `mixed` or `inconclusive` and up to three possible drivers.
Each driver needs a complete exact title/snippet, a valid news index and matching driver terms.
Code preserves the quote and link, uses cautious explanation templates, and caps hypothesis
confidence at 0.5. Unsupported output is withheld with a warning; the measured conclusion
remains available. AI checks consistency and contextual plausibility, not independent truth
or proven causation. Provider failures never silently switch to fabricated data.

## Recorded results, 7 October 2026

Four real SerpApi histories and two real DeepSeek reviews cover the existing demo profiles.
Both have 104 complete public weeks and no usable app-history baseline yet.

| Locality | Broad quarter change | Rental quarter change | Rental annual change | Priority |
|---|---:|---:|---:|---|
| Whitefield | +3.1% | −17.4% | −6.2% | None |
| Koramangala | +2.8% | −28.5% | −23.6% | None |

Whitefield's positive reported price growth and metro news do not override falling rental
interest. Neither demo receives a developing-area priority. That is a useful result, rather
than evidence that either locality is definitely failing to develop. Replay is recorded
history, with its original retrieval date; start a live/record run for current observations.

## Try it and record it

Run `make demo`, open <http://localhost:5173>, start either demo profile, and inspect
**Search history and developing-area signals** on its run page. Expand **Weekly observations**
or **Method, scores and limitations** to inspect the inputs. Existing old runs have no report;
start a new run. The existing database gains two tables at startup without a reset.

To record the demo histories/reviews with configured keys:

```bash
cd backend
uv run python scripts/record_search_growth.py --profile both
```

This uses a temporary database, real provider record modes and existing fixtures where
available. It inserts no historical app searches. Different locality batches and usable
app histories need their own exact recordings. To refresh an already recorded Trends query,
run the app in live mode after its gateway cache expires; record mode deliberately reuses
committed responses when available.

`GET /api/runs/{run_id}/development` is read-only and returns frozen `AreaDevelopment[]`.
Known pending/older runs return `[]`; partial/failed runs expose saved reports; unknown/deleted
runs return 404. No GET makes provider calls. Progress includes `development` and
`development_warnings`. A replay miss or exhausted budget is explicit in report warnings.

Main implementation: `enrichment/search_history.py` (collection/parser/arithmetic),
`enrichment/development.py` (assessment/ranking/review), `DevelopmentPanel.tsx` (charts/evidence).
Tests cover spikes, seasonal recurrence, sparse/malformed data, sample deduplication, partial
weeks, rank gates, unsupported AI evidence, profile edits/deletion, API snapshots and rendering.
