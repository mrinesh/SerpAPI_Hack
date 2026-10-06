"""Real demo replay, frozen metric snapshots, read-only API and unsafe price suppression."""

import pytest

from app.db.models import ListingRow
from app.db.session import SessionLocal
from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_metrics_replay_snapshot_sources_and_read_only_endpoint(client, name):
    profile = DEMO_PROFILES[name]
    profile_id = client.post("/api/profiles", json=profile).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "succeeded", run["error"]
    response = client.get(f"/api/runs/{run_id}/metrics")
    assert response.status_code == 200
    items = response.json()
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    assert {m["listing_id"] for m in items} == {item["id"] for item in listings}
    event = next(e for e in run["events"] if e["stage"] == "enrich")
    assert event["counts"]["metrics"] == len(items)
    assert event["counts"]["investment_warnings"] == 0
    assert run["searches_used"] == 0
    if name == "commercial":
        assessed = [
            item["metrics"] for item in items if item["metrics"]["meets_target_roi"] is not None
        ]
        assert len(assessed) == 2
        assert all(item["rental_yield_pct"]["value"] > 4 for item in assessed)
        assert all(item["est_monthly_rent_inr"]["sources"][0]["search_id"] for item in assessed)
    else:
        growths = [
            item["metrics"]["price_growth_pct"]
            for item in items
            if item["metrics"]["price_growth_pct"]["value"] is not None
        ]
        assert growths and all(item["value"] == 10.8 for item in growths)
        assert all(item["meets_target_roi"] is None for item in (m["metrics"] for m in items))
    for item in items:
        metrics = item["metrics"]
        assert metrics["target_roi_pct"] == 4
        assert metrics["roi_measure"] == "rental_yield"
        for field in ("rental_yield_pct", "price_growth_pct", "price_vs_area_pct"):
            value = metrics[field]
            if value["value"] is not None:
                assert value["sources"] and value["note"]
        if metrics["rental_yield_pct"]["value"] is None:
            assert metrics["meets_target_roi"] is None
    # A profile edit or shared listing refresh cannot rewrite an old financial comparison.
    assert (
        client.put(f"/api/profiles/{profile_id}", json=dict(profile, target_roi_pct=9)).status_code
        == 200
    )
    with SessionLocal() as db:
        listing = db.get(ListingRow, items[0]["listing_id"])
        listing.data = dict(listing.data, price_inr=dict(listing.data["price_inr"], value=1))
        db.commit()
    assert client.get(f"/api/runs/{run_id}/metrics").json() == items
    after = client.get(f"/api/runs/{run_id}").json()
    assert (after["searches_used"], after["cache_hits"]) == (
        run["searches_used"],
        run["cache_hits"],
    )
    assert client.delete(f"/api/profiles/{profile_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}/metrics").status_code == 404


def test_flagged_commercial_price_cannot_generate_huge_yield(client):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES["commercial"]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    suspect = next(item["id"] for item in listings if item["price_inr"]["value"] == 360000)
    metrics = next(
        m["metrics"]
        for m in client.get(f"/api/runs/{run_id}/metrics").json()
        if m["listing_id"] == suspect
    )
    assert metrics["rental_yield_pct"]["value"] is None
    assert metrics["meets_target_roi"] is None
    assert "Implausibly cheap" in metrics["assessment_note"]


def test_unknown_or_pre_enrichment_run_and_openapi(client, monkeypatch):
    assert client.get("/api/runs/missing/metrics").status_code == 404
    monkeypatch.setattr(orchestrator, "_launch", lambda _: None)
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    assert client.get(f"/api/runs/{run_id}/metrics").json() == []
    assert "/api/runs/{run_id}/metrics" in client.get("/openapi.json").json()["paths"]


def test_saved_metrics_survive_a_later_enrichment_failure(client, monkeypatch):
    compute = orchestrator.compute_metrics
    calls = 0

    def fail_later(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("Simulated calculation failure")
        return compute(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "compute_metrics", fail_later)
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES["commercial"]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "failed"
    assert len(client.get(f"/api/runs/{run_id}/metrics").json()) == 2
    assert len(client.get(f"/api/runs/{run_id}/verifications").json()) == 6
