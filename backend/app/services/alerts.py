"""New-match and price-drop alerts (CHECKLIST F-10).

`check_alerts` re-runs discovery for every profile, diffs against `listings`
(new canonical URLs -> new_match; lower `last_price_inr` -> price_drop) and writes `alerts`.
It is called by the scheduler and by `POST /api/alerts/check` for the demo.
"""

from sqlalchemy.orm import Session

from app.core.errors import NotImplementedYet
from app.schemas.views import Alert


def list_alerts(db: Session, *, unread_only: bool = False) -> list[Alert]:
    raise NotImplementedYet("F-10", "Listing alerts")


def check_alerts(db: Session) -> list[Alert]:
    raise NotImplementedYet("F-10", "Checking for alerts")
