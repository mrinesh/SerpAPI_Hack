import pytest
from pydantic import ValidationError

from app.schemas.scenario import ScenarioIn
from app.services.scenarios import calculate


def inputs(**patch):
    return ScenarioIn(
        purchase_price_inr=1000000,
        down_payment_pct=20,
        loan_interest_pct=patch.pop("loan_interest_pct", 12),
        loan_years=patch.pop("loan_years", 10),
        hold_years=patch.pop("hold_years", 2),
        monthly_rent_inr=patch.pop("monthly_rent_inr", 10000),
        annual_price_growth_pct=patch.pop("annual_price_growth_pct", 0),
        **patch,
    )


def test_known_emi_and_amortization_conserve_principal_and_payments():
    result = calculate(inputs(hold_years=10))
    assert result.monthly_emi_inr == pytest.approx(11477.68, abs=0.01)
    assert sum(y.principal_inr for y in result.years) == pytest.approx(800000, abs=0.1)
    assert result.exit_loan_balance_inr == 0
    assert all(
        y.loan_payments_inr == pytest.approx(y.principal_inr + y.interest_inr, abs=0.02)
        for y in result.years
    )


def test_zero_interest_full_payoff_and_no_double_counting_exit_debt():
    result = calculate(inputs(loan_interest_pct=0, loan_years=1, hold_years=2, monthly_rent_inr=0))
    assert result.monthly_emi_inr == 66666.67
    assert result.years[1].loan_payments_inr == 0
    assert result.total_profit_inr == 0 and result.equity_return_pct == 0


def test_vacancy_expenses_and_exit_costs_reduce_profit():
    a = calculate(inputs(loan_interest_pct=0, loan_years=1))
    b = calculate(
        inputs(
            loan_interest_pct=0,
            loan_years=1,
            vacancy_pct=50,
            monthly_expenses_inr=1000,
            purchase_cost_pct=5,
            exit_cost_pct=5,
        )
    )
    assert b.total_profit_inr < a.total_profit_inr
    assert b.initial_cash_inr == 250000


def test_invalid_and_nonfinite_assumptions_rejected():
    for patch in ({"loan_interest_pct": float("inf")}, {"hold_years": 0}, {"vacancy_pct": 101}):
        with pytest.raises(ValidationError):
            inputs(**patch)
