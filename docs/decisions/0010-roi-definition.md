# 0010. ROI: one target, measured as rental yield, price growth or total return

- **Status:** Accepted
- **Date:** 2026-10-03
- **Amends:** [0008](0008-code-computes-llm-explains.md) (cap rate is no longer computed)

## Context
The investor profile has an "ROI target". Net rental yield and commercial cap rate both need
cost assumptions (vacancy, maintenance, property tax, operating costs). We would have to source
and defend each figure, and the product owner chose not to ask investors for them either.

## Decision
- The profile has one `target_roi_pct`. The investment goal picks what it is compared against:

  | Goal | Measure | Formula |
  |---|---|---|
  | Rental income | Rental yield | annual rent ÷ price × 100, before costs |
  | Appreciation | Price growth | locality's past-12-month change in price per sq ft |
  | Balanced | Total return | rental yield + price growth |

- Price growth defaults to the locality's past-12-month change found in search results (if spike
  S-01 shows the data exists), and the investor can override it per profile
  (`expected_growth_pct`). Past growth is labelled as past, never as a forecast.
- Net yield and cap rate are not computed anywhere, for residential or commercial.

## Consequences
- Every ROI number comes from listed prices, rents and price trends we can cite; there are no
  invented cost defaults.
- Rental yield overstates what an investor actually earns, because costs are ignored. The UI must
  say "before costs" wherever it shows yield.
- If the locality's growth figure is not found and there is no override, price growth and total
  return show as missing, not zero.
