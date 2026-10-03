"""Stage 5c, enrich: investment metrics (CHECKLIST F-09).

Pure arithmetic over sourced inputs. No I/O, so it is unit-tested exhaustively. Every output
is `Sourced` with method `computed` and carries its inputs' sources forward.

    price_per_sqft     = price / size
    price_vs_area_pct  = (price_per_sqft / area_avg_price_per_sqft - 1) * 100
    rental_yield_pct   = est_monthly_rent * 12 / price * 100          (before any costs)
    price_growth_pct   = profile.expected_growth_pct if set, else the locality's
                         past-12-month change in price per sq ft (missing if not found)
    total_return_pct   = rental_yield_pct + price_growth_pct
    meets_target_roi   = value of GOAL_MEASURE[profile.goal] >= profile.target_roi_pct

There is no net yield or cap rate: both need cost assumptions (vacancy, maintenance, tax,
operating costs) that we would have to source (docs/decisions/0010-roi-definition.md).
"""

from app.core.errors import NotImplementedYet
from app.schemas.area import AreaIntel
from app.schemas.listing import Listing
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import InvestorProfile


def compute_metrics(
    listing: Listing, area: AreaIntel | None, profile: InvestorProfile
) -> InvestmentMetrics:
    raise NotImplementedYet("F-09", "Investment metrics")
