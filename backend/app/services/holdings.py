from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.models import HoldingRow
from app.schemas.holding import Holding, HoldingIn, PortfolioSummary
from app.services.properties import get_property_detail


def _owner(db: Session) -> str:
    return db.info.get("owner_id", "local")


def _view(row: HoldingRow) -> Holding:
    data = HoldingIn.model_validate(row.data)
    cost = data.purchase_price_inr + data.acquisition_costs_inr
    value = data.current_value_inr
    return Holding(
        **data.model_dump(),
        id=row.id,
        updated_at=row.updated_at.replace(tzinfo=row.updated_at.tzinfo or UTC),
        monthly_cash_flow_inr=data.monthly_rent_inr
        - data.monthly_expenses_inr
        - data.monthly_emi_inr,
        equity_inr=None if value is None else value - data.outstanding_loan_inr,
        unrealized_gain_inr=None if value is None else value - cost,
        net_yield_on_cost_pct=round(
            (data.monthly_rent_inr - data.monthly_expenses_inr) * 12 / cost * 100, 2
        ),
    )


def summary(db: Session) -> PortfolioSummary:
    items = [
        _view(row)
        for row in db.scalars(
            select(HoldingRow)
            .where(HoldingRow.owner_id == _owner(db))
            .order_by(HoldingRow.updated_at.desc())
        )
    ]
    valued = [item for item in items if item.current_value_inr is not None]
    complete = bool(items) and len(valued) == len(items)
    return PortfolioSummary(
        holdings=items,
        invested_cost_inr=sum(i.purchase_price_inr + i.acquisition_costs_inr for i in items),
        valued_holdings=len(valued),
        current_value_inr=sum(i.current_value_inr for i in valued) if complete else None,
        equity_inr=sum(i.equity_inr for i in valued) if complete else None,
        monthly_cash_flow_inr=sum(i.monthly_cash_flow_inr for i in items),
    )


def save_holding(db: Session, data: HoldingIn, holding_id: str | None = None) -> Holding:
    if data.listing_id:
        get_property_detail(db, data.listing_id)
    row = _get(db, holding_id) if holding_id else HoldingRow(owner_id=_owner(db))
    row.data = data.model_dump(mode="json")
    db.add(row)
    db.commit()
    return _view(row)


def _get(db: Session, holding_id: str) -> HoldingRow:
    row = db.get(HoldingRow, holding_id)
    if row is None or row.owner_id != _owner(db):
        raise NotFound("Portfolio holding not found")
    return row


def delete_holding(db: Session, holding_id: str) -> None:
    db.delete(_get(db, holding_id))
    db.commit()
