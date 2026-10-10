"""Investor-entered portfolio records; asking prices are never automatic valuations."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HoldingIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=160)
    listing_id: str | None = Field(default=None, min_length=1, max_length=32)
    acquired_on: date
    purchase_price_inr: float = Field(gt=0, le=1e12)
    acquisition_costs_inr: float = Field(default=0, ge=0, le=1e12)
    current_value_inr: float | None = Field(default=None, gt=0, le=1e12)
    valued_on: date | None = None
    outstanding_loan_inr: float = Field(default=0, ge=0, le=1e12)
    monthly_rent_inr: float = Field(default=0, ge=0, le=1e9)
    monthly_expenses_inr: float = Field(default=0, ge=0, le=1e9)
    monthly_emi_inr: float = Field(default=0, ge=0, le=1e9)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _dates(self):
        if self.acquired_on > date.today():
            raise ValueError("acquisition must not be in the future")
        if (self.current_value_inr is None) != (self.valued_on is None):
            raise ValueError("valuation amount and date must be supplied together")
        if self.valued_on and not self.acquired_on <= self.valued_on <= date.today():
            raise ValueError("valuation date must be between acquisition and today")
        return self


class Holding(HoldingIn):
    id: str
    updated_at: datetime
    monthly_cash_flow_inr: float
    equity_inr: float | None
    unrealized_gain_inr: float | None
    net_yield_on_cost_pct: float


class PortfolioSummary(BaseModel):
    holdings: list[Holding]
    invested_cost_inr: float
    valued_holdings: int
    current_value_inr: float | None
    equity_inr: float | None
    monthly_cash_flow_inr: float
    note: str = (
        "Manual amounts and dated valuations. Totals for value/equity are withheld "
        "unless every holding has a valuation. Unrealized gains exclude sale costs and taxes."
    )
