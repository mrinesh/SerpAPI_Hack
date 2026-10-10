BASE = {
    "name": "Owned flat",
    "acquired_on": "2020-01-01",
    "purchase_price_inr": 1000000,
    "acquisition_costs_inr": 100000,
    "monthly_rent_inr": 10000,
    "monthly_expenses_inr": 2000,
    "monthly_emi_inr": 5000,
    "outstanding_loan_inr": 400000,
}


def test_holdings_crud_math_missing_valuations_and_totals(client):
    item = client.post("/api/portfolio", json=BASE)
    assert item.status_code == 201
    row = item.json()
    assert row["monthly_cash_flow_inr"] == 3000
    assert row["equity_inr"] is None
    assert row["net_yield_on_cost_pct"] == 8.73
    updated = client.put(
        "/api/portfolio/" + row["id"],
        json={**BASE, "current_value_inr": 1500000, "valued_on": "2026-01-01"},
    ).json()
    assert updated["equity_inr"] == 1100000 and updated["unrealized_gain_inr"] == 400000
    summary = client.get("/api/portfolio").json()
    assert summary["current_value_inr"] == 1500000
    client.post("/api/portfolio", json=BASE)
    assert client.get("/api/portfolio").json()["current_value_inr"] is None
    assert client.delete("/api/portfolio/" + row["id"]).status_code == 204
    assert client.put("/api/portfolio/" + row["id"], json=BASE).status_code == 404


def test_valuation_and_future_dates_are_validated(client):
    for patch in (
        {"valued_on": "2026-01-01"},
        {"current_value_inr": 2},
        {"acquired_on": "2099-01-01"},
        {"purchase_price_inr": -1},
    ):
        assert client.post("/api/portfolio", json={**BASE, **patch}).status_code == 422
