"""Stage 5c, enrich: investment metrics (CHECKLIST F-09).

Pure arithmetic over sourced inputs. No I/O, so it is unit-tested exhaustively. Every output
is `Sourced` with method `computed` and carries its inputs' sources forward.

    price_per_sqft     = price / size
    price_vs_area_pct  = (price_per_sqft / area_avg_price_per_sqft - 1) * 100
    gross_yield_pct    = est_monthly_rent * 12 / price * 100
    net_yield_pct      = (rent * 12 * (1 - vacancy) - maintenance - property_tax) / price * 100
    cap_rate_pct       = net operating income / price * 100    (commercial)

Default assumptions (vacancy, maintenance, tax) are listed in `DEFAULT_ASSUMPTIONS` and
returned in `InvestmentMetrics.assumptions` so the UI can show them.
"""

from app.core.errors import NotImplementedYet
from app.schemas.area import AreaIntel
from app.schemas.listing import Listing
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import InvestorProfile

DEFAULT_ASSUMPTIONS: dict[str, float] = {}  # filled in F-09 with cited sources in docs/PIPELINE.md


def compute_metrics(
    listing: Listing, area: AreaIntel | None, profile: InvestorProfile
) -> InvestmentMetrics:
    raise NotImplementedYet("F-09", "Investment metrics")
