from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    purchase_price_inr: float = Field(gt=0, le=1e12)
    down_payment_pct: float = Field(ge=0, le=100)
    purchase_cost_pct: float = Field(default=0, ge=0, le=50)
    loan_interest_pct: float = Field(ge=0, le=50)
    loan_years: int = Field(ge=1, le=40)
    hold_years: int = Field(ge=1, le=40)
    monthly_rent_inr: float = Field(ge=0, le=1e9)
    vacancy_pct: float = Field(default=0, ge=0, le=100)
    monthly_expenses_inr: float = Field(default=0, ge=0, le=1e9)
    annual_rent_growth_pct: float = Field(default=0, ge=-100, le=100)
    annual_price_growth_pct: float = Field(ge=-100, le=100)
    exit_cost_pct: float = Field(default=0, ge=0, le=50)

    @model_validator(mode="after")
    def _equity(self):
        if self.purchase_price_inr * (self.down_payment_pct + self.purchase_cost_pct) / 100 < 1:
            raise ValueError("initial cash must be at least INR 1: include down payment or costs")
        return self


class ScenarioYear(BaseModel):
    year: int
    rent_inr: float
    expenses_inr: float
    loan_payments_inr: float
    interest_inr: float
    principal_inr: float
    balance_inr: float
    cash_flow_inr: float


class ScenarioResult(BaseModel):
    assumptions: ScenarioIn
    initial_cash_inr: float
    loan_principal_inr: float
    monthly_emi_inr: float
    years: list[ScenarioYear]
    exit_value_inr: float
    exit_loan_balance_inr: float
    net_exit_proceeds_inr: float
    cumulative_cash_flow_inr: float
    total_profit_inr: float
    equity_return_pct: float
    note: str = (
        "Illustrative fixed-rate monthly amortization and user-entered assumptions. "
        "Rent changes annually; expenses stay fixed. Exit proceeds repay remaining debt. "
        "Equity return is for the entire holding period, not annualized or IRR. "
        "Taxes, loan fees, inflation and prepayment penalties are excluded."
    )
