"""Monthly amortization; no provider or AI calls, all assumptions retained."""

import math

from app.schemas.scenario import ScenarioIn, ScenarioResult, ScenarioYear


def calculate(data: ScenarioIn) -> ScenarioResult:
    principal = data.purchase_price_inr * (1 - data.down_payment_pct / 100)
    cash = data.purchase_price_inr * (data.down_payment_pct + data.purchase_cost_pct) / 100
    rate = data.loan_interest_pct / 1200
    months = data.loan_years * 12
    emi = (
        principal / months
        if rate == 0
        else principal * rate / -math.expm1(-months * math.log1p(rate))
    )
    balance = principal
    years = []
    cumulative = 0
    for year in range(1, data.hold_years + 1):
        rent = data.monthly_rent_inr * (1 + data.annual_rent_growth_pct / 100) ** (year - 1)
        rent *= 12 * (1 - data.vacancy_pct / 100)
        expenses = data.monthly_expenses_inr * 12
        interest_sum = principal_sum = payments = 0
        for _ in range(12):
            interest = balance * rate
            payment = min(emi, balance + interest) if balance > 1e-7 else 0
            paid_principal = max(0, payment - interest)
            balance = max(0, balance - paid_principal)
            interest_sum += interest
            principal_sum += paid_principal
            payments += payment
        flow = rent - expenses - payments
        cumulative += flow
        years.append(
            ScenarioYear(
                year=year,
                rent_inr=round(rent, 2),
                expenses_inr=round(expenses, 2),
                loan_payments_inr=round(payments, 2),
                interest_inr=round(interest_sum, 2),
                principal_inr=round(principal_sum, 2),
                balance_inr=round(balance, 2),
                cash_flow_inr=round(flow, 2),
            )
        )
    exit_value = (
        data.purchase_price_inr * (1 + data.annual_price_growth_pct / 100) ** data.hold_years
    )
    proceeds = exit_value * (1 - data.exit_cost_pct / 100) - balance
    profit = proceeds + cumulative - cash
    return ScenarioResult(
        assumptions=data,
        initial_cash_inr=round(cash, 2),
        loan_principal_inr=round(principal, 2),
        monthly_emi_inr=round(emi, 2),
        years=years,
        exit_value_inr=round(exit_value, 2),
        exit_loan_balance_inr=round(balance, 2),
        net_exit_proceeds_inr=round(proceeds, 2),
        cumulative_cash_flow_inr=round(cumulative, 2),
        total_profit_inr=round(profit, 2),
        equity_return_pct=round(profit / cash * 100, 2),
    )
