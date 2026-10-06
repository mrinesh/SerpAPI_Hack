"""F-05 API and run snapshots, using existing fixtures and no network."""

import pytest

from app.db.models import AreaIntelRow
from app.db.session import SessionLocal
from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_area_demo_api_preserves_sources_and_reuses_existing_benchmarks(client, name):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "succeeded", run["error"]
    response = client.get(f"/api/runs/{run_id}/areas")
    assert response.status_code == 200
    areas = response.json()
    assert len(areas) == 1
    area = areas[0]
    assert not area["warnings"], area["warnings"]
    assert area["amenities"] and area["news"] and area["infrastructure"]
    assert area["center"] and area["center_source"]["search_id"]
    assert area["price_levels"] and area["price_trend"] is None  # no invented YoY
    assert all(a["source"]["search_id"] for a in area["amenities"])
    assert all(n["source"]["url"] == n["url"] for n in area["news"])
    assert all(f["evidence"]["sources"] for f in area["infrastructure"])
    assert run["searches_used"] == 0
    event = next(e for e in run["events"] if e["stage"] == "enrich")
    assert event["status"] == "succeeded" and event["counts"]["warnings"] == 0
    cached = client.get(f"/api/areas/{area['locality_key']}").json()
    assert cached["cache_hit"] and cached["price_levels"] == {}
    # Later locality-cache modifications cannot rewrite this run's snapshot.
    with SessionLocal() as db:
        row = db.get(AreaIntelRow, area["locality_key"])
        row.data = dict(row.data, summary="A later cache value")
        db.commit()
    assert client.get(f"/api/runs/{run_id}/areas").json()[0]["summary"] == area["summary"]
    second_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    second = client.get(f"/api/runs/{second_id}/areas").json()[0]
    assert second["cache_hit"] and second["price_levels"] == area["price_levels"]
    assert client.delete(f"/api/profiles/{profile_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}/areas").status_code == 404
    # Shared area cache survives profile deletion.
    assert client.get(f"/api/areas/{area['locality_key']}").status_code == 200


def test_unenriched_area_is_404_unknown_geography_is_422_and_missing_run_is_404(client):
    assert client.get("/api/areas/bengaluru/whitefield").status_code == 404
    assert client.get("/api/areas/bengaluru/unknown").status_code == 422
    assert client.get("/api/areas/bad-key").status_code == 422
    assert client.get("/api/runs/missing/areas").status_code == 404


def test_openapi_exposes_typed_area_results(client):
    schema = client.get("/openapi.json").json()
    assert "/api/runs/{run_id}/areas" in schema["paths"]
    assert "InfrastructureFact" in schema["components"]["schemas"]
